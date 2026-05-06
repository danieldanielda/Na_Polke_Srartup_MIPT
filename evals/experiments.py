import json
import os
import requests
import numpy as np
import re
from typing import List, Dict, Any, Tuple
import time
import logging
from config import EvalSettings

# --- КОНФИГУРАЦИЯ ---
API_BASE_URL = "http://195.209.219.147:8000" 
DATASET_H1_PATH = "eval/eval_dataset_nl_queries.jsonl"
DATASET_H2_PATH = "eval/eval_dataset_inci.jsonl"
GOLDAPPLE_DB_PATH = "data/goldapple_dataset.json"
REQUEST_TIMEOUT = 120 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = EvalSettings()

# ==============================================================================
# 1. Утилиты парсинга (из твоего кода)
# ==============================================================================

def extract_skus_from_text(text: str) -> List[str]:
    skus = []
    pattern_marked = r'(?:sku_|article[:\s]*)(\d+)'
    found_marked = re.findall(pattern_marked, text, re.IGNORECASE)
    if found_marked:
        skus.extend(found_marked)
        
    if not skus:
        pattern_digits = r'\b(\d{10,14})\b'
        skus = re.findall(pattern_digits, text)
        
    return list(set(skus))

def parse_recommendation_response(response_data: dict) -> List[str]:
    raw_content = response_data.get("recommendations", "")
    
    if isinstance(raw_content, str):
        try:
            clean_json = raw_content.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(clean_json)
            
            if isinstance(parsed, list):
                result_skus = []
                for item in parsed:
                    if isinstance(item, dict):
                        val = item.get('sku') or item.get('article') or item.get('id')
                        if val: result_skus.append(str(val))
                    elif isinstance(item, str):
                        result_skus.append(item)
                if result_skus: return result_skus
        except json.JSONDecodeError:
            pass 

    return extract_skus_from_text(str(raw_content))

def parse_analysis_response(response_data: dict) -> Dict[str, str]:
    if isinstance(response_data, dict):
        for key in ['ingredients', 'result', 'analysis', 'classified_ingredients']:
            if key in response_data and isinstance(response_data[key], dict):
                return response_data[key]
        
        exclude_keys = {'status', 'message', 'error', 'summary', 'raw'}
        filtered = {k: v for k, v in response_data.items() if k not in exclude_keys}
        if filtered: return filtered
            
    return {}

# ==============================================================================
# 2. LLM-as-Judge Logic (НОВОЕ)
# ==============================================================================

def decompose_answer_into_claims(answer: str) -> List[str]:
    """Разбивает текст ответа на атомарные утверждения (предложения)."""
    if not answer: return []
    # Простая эвристика: разделение по точкам, фильтрация коротких фрагментов
    sentences = [s.strip() for s in answer.split('.') if len(s.strip()) > 15 and not s.strip().startswith(('http', 'www'))]
    return sentences

def call_llm_judge(claim: str, reference_text: str) -> str:
    """Отправляет утверждение и эталон модели-судье."""
    prompt = f"""
    Ты — строгий эксперт-аудитор. Проверь утверждение на соответствие Reference.
    
    Claim: "{claim}"
    Reference: "{reference_text}"
    
    Верни ТОЛЬКО одно слово:
    SUPPORTED (если подтверждается Reference)
    CONTRADICTED (если противоречит)
    UNVERIFIED (если в Reference нет информации)
    """
    
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {settings.model_api_key}"}
    payload = {
        "model": settings.model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0
    }
    
    try:
        response = requests.post(settings.model_api, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        verdict = data['choices'][0]['message']['content'].strip().upper()
        
        if "SUPPORTED" in verdict: return "SUPPORTED"
        if "CONTRADICTED" in verdict: return "CONTRADICTED"
        return "UNVERIFIED"
    except Exception as e:
        logger.error(f"Judge Error: {e}")
        return "ERROR"

def load_goldapple_db_for_reference():
    """Загружает базу продуктов для получения Reference Text (описания)."""
    if not os.path.exists(GOLDAPPLE_DB_PATH):
        logger.warning(f"{GOLDAPPLE_DB_PATH} not found. Judge metrics will be skipped.")
        return {}
    
    with open(GOLDAPPLE_DB_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    db_index = {}
    for item in data:
        key = item.get('article') or item.get('sku')
        if key:
            # Сохраняем описание и ингредиенты как источник истины
            db_index[str(key)] = {
                "desc": item.get('description', ''),
                "ingr": item.get('ingredients', ''),
                "title": item.get('title', '')
            }
    return db_index

def run_judge_evaluation(query: str, rag_answer: str, gt_ids: List[str], db_index: Dict) -> Dict[str, float]:
    """
    Проводит оценку одного ответа через Judge.
    1. Берет первый продукт из Ground Truth.
    2. Формирует Reference из его описания.
    3. Разбивает ответ RAG на claims.
    4. Проверяет каждый claim.
    """
    if not gt_ids or not db_index:
        return {"factual_accuracy": 0.0, "hallucination_rate": 0.0}
    
    # Берем первый ID из ground truth как основной референс
    ref_product = db_index.get(str(gt_ids[0]))
    if not ref_product:
        return {"factual_accuracy": 0.0, "hallucination_rate": 0.0}
        
    # Формируем Reference Text
    reference_text = f"{ref_product['title']}. {ref_product['desc']} Состав: {ref_product['ingr']}"
    
    # Декомпозиция
    claims = decompose_answer_into_claims(rag_answer)
    if not claims:
        return {"factual_accuracy": 0.0, "hallucination_rate": 0.0}
        
    # Проверка судьей
    supported = 0
    contradicted = 0
    
    print(f"    [Judge] Checking {len(claims)} claims...")
    for claim in claims:
        verdict = call_llm_judge(claim, reference_text)
        if verdict == "SUPPORTED":
            supported += 1
        elif verdict == "CONTRADICTED":
            contradicted += 1
        # print(f"      Claim: '{claim[:50]}...' -> {verdict}")
        
    checkable = supported + contradicted
    accuracy = supported / checkable if checkable > 0 else 0.0
    hallucination_rate = contradicted / checkable if checkable > 0 else 0.0
    
    return {
        "factual_accuracy": accuracy,
        "hallucination_rate": hallucination_rate,
        "total_claims": len(claims)
    }

# ==============================================================================
# 3. Вызовы API (из твоего кода)
# ==============================================================================

def call_recommendation_api(query: str) -> Tuple[str, List[str]]:
    """Возвращает (Raw Answer Text, Parsed SKUs)"""
    url = f"{API_BASE_URL}/recommend_products"
    payload = {"query": query, "collection_id": "global_collection", "system_prompt": "system_common_prompt"}
    
    try:
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        raw_text = data.get("recommendations", "")
        skus = parse_recommendation_response(data)
        return raw_text, skus
    except Exception as e:
        logger.error(f"Rec API Error: {e}")
        return "", []

def call_analysis_api(product_info: str) -> Dict[str, str]:
    url = f"{API_BASE_URL}/analyze_product"
    payload = {"product_info": product_info, "collection_id": "global_collection", "analysis_type": "full", "system_prompt": "system_common_prompt"}
    
    try:
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return parse_analysis_response(data)
    except Exception as e:
        logger.error(f"Anal API Error: {e}")
        return {}

# ==============================================================================
# 4. Метрики (из твоего кода)
# ==============================================================================

def calculate_recall_at_k(retrieved_ids: List[str], ground_truth_ids: List[str], k: int = 5) -> float:
    if not ground_truth_ids: return 0.0
    top_k = retrieved_ids[:k]
    top_k_str = [str(x) for x in top_k]
    gt_str = [str(x) for x in ground_truth_ids]
    relevant = set(top_k_str).intersection(set(gt_str))
    return len(relevant) / len(gt_str)

def calculate_accuracy(predictions: Dict[str, str], ground_truth: Dict[str, str]) -> float:
    if not ground_truth: return 0.0
    correct = 0
    total = len(ground_truth)
    for ing, true_cat in ground_truth.items():
        pred_cat = predictions.get(ing)
        if pred_cat and str(pred_cat).lower().strip() == str(true_cat).lower().strip():
            correct += 1
    return correct / total

# ==============================================================================
# 5. Запуск экспериментов
# ==============================================================================

def run_h1_with_judge(limit_judge_queries: int = 5):
    """
    Запускает H1 (Recall) и дополнительно оценивает качество текста через Judge.
    """
    print("\n=== EXP H1: RECOMMENDATIONS + LLM JUDGE ===")
    if not os.path.exists(DATASET_H1_PATH): return
    
    queries = [json.loads(l) for l in open(DATASET_H1_PATH)]
    db_index = load_goldapple_db_for_reference()
    
    recalls = []
    judge_accuracies = []
    hallucination_rates = []
    
    # Ограничим количество запросов для Judge, так как это долго
    total_queries = len(queries)
    
    for i, q in enumerate(queries):
        query_text = q['query']
        gt_ids = q['ground_truth_product_ids']
        
        print(f"[{i+1}/{total_queries}] Query: '{query_text[:40]}...'")
        
        # 1. Получаем ответ и SKU
        raw_answer, retrieved_skus = call_recommendation_api(query_text)
        
        # 2. Считаем Recall@5
        rec = calculate_recall_at_k(retrieved_skus, gt_ids)
        recalls.append(rec)
        print(f"  Recall@5: {rec:.2f}")
        
        # 3. Запускаем Judge (только для первых N запросов, чтобы не ждать часами)
        if i < limit_judge_queries and raw_answer:
            metrics = run_judge_evaluation(query_text, raw_answer, gt_ids, db_index)
            judge_accuracies.append(metrics['factual_accuracy'])
            hallucination_rates.append(metrics['hallucination_rate'])
            print(f"  Judge Acc: {metrics['factual_accuracy']:.2f}, Hallucinations: {metrics['hallucination_rate']:.2f}")
        
        time.sleep(2) 
        
    mean_rec = np.mean(recalls)
    print(f"\nRESULT H1: Mean Recall@5 = {mean_rec:.4f} (Target >= 0.9)")
    
    if judge_accuracies:
        mean_judge_acc = np.mean(judge_accuracies)
        mean_halluc = np.mean(hallucination_rates)
        print(f"RESULT JUDGE (on first {limit_judge_queries}): Factual Acc = {mean_judge_acc:.4f}, Hallucination Rate = {mean_halluc:.4f}")

def run_h2():
    print("\n=== EXP H2: INGREDIENTS ===")
    if not os.path.exists(DATASET_H2_PATH): return
    
    products = [json.loads(l) for l in open(DATASET_H2_PATH)]
    total_correct = 0
    total_count = 0
    
    for i, p in enumerate(products):
        preds = call_analysis_api(", ".join(p['inci_list']))
        
        for ing, true_cat in p['ground_truth_categories'].items():
            total_count += 1
            pred_cat = preds.get(ing)
            if pred_cat and str(pred_cat).lower().strip() == str(true_cat).lower().strip():
                total_correct += 1
                
        if i % 5 == 0:
            print(f"  [{i+1}/{len(products)}] Current Acc: {total_correct/max(1,total_count):.2f}")
        time.sleep(2)

    acc = total_correct / max(1, total_count)
    print(f"RESULT H2: Accuracy = {acc:.4f} (Target >= 0.9)")
    return acc

if __name__ == "__main__":
    # Запуск H1 с интеграцией Judge (проверит первые 5 запросов на галлюцинации)
    run_h1_with_judge(limit_judge_queries=5)
    
    # Запуск H2 (там Judge не нужен, так как есть строгий Accuracy по категориям)
    run_h2()