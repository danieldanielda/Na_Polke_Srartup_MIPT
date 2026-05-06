import json
import requests
from typing import List, Dict
from config import EvalSettings

settings = EvalSettings()

def decompose_answer_into_claims(answer: str) -> List[str]:
    """
    Простая эвристика для разбиения ответа на атомарные утверждения.
    В идеале это тоже должна делать LLM, но для скорости можно разбить по предложениям.
    """
    # Разбиваем по точкам, убираем пустые
    sentences = [s.strip() for s in answer.split('.') if len(s.strip()) > 10 and not s.strip().startswith(('http', 'www'))]
    return sentences

def call_llm_judge(claim: str, reference_text: str) -> str:
    """
    Отправляет утверждение и референс Судье (LLM) и получает вердикт.
    """
    prompt = f"""
    Ты — строгий эксперт-аудитор фактов.
    Твоя задача: проверить утверждение на соответствие предоставленным данным (Reference).
    
    Утверждение (Claim): "{claim}"
    Reference (Факты): "{reference_text}"
    
    Инструкции:
    1. Если утверждение полностью подтверждается Reference, верни: SUPPORTED
    2. Если утверждение противоречит Reference, верни: CONTRADICTED
    3. Если в Reference нет информации для проверки, верни: UNVERIFIED
    
    Верни ТОЛЬКО одно слово: SUPPORTED, CONTRADICTED или UNVERIFIED.
    """
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.model_api_key}"
    }
    
    payload = {
        "model": settings.model_name,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0 # Судья должен быть детерминированным
    }
    
    try:
        response = requests.post(settings.model_api, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Парсинг ответа (формат зависит от API, здесь OpenAI-like)
        verdict = data['choices'][0]['message']['content'].strip().upper()
        
        # Очистка от лишних слов, если модель многословна
        if "SUPPORTED" in verdict: return "SUPPORTED"
        if "CONTRADICTED" in verdict: return "CONTRADICTED"
        if "UNVERIFIED" in verdict: return "UNVERIFIED"
        
        return "UNVERIFIED" # По умолчанию
        
    except Exception as e:
        print(f"  [Judge Error]: {e}")
        return "ERROR"

def calculate_factual_accuracy(claims: List[str], reference_text: str) -> Dict[str, float]:
    """
    Прогоняет все claims через судью и считает метрики.
    """
    if not claims:
        return {"accuracy": 0.0, "hallucination_rate": 0.0}
        
    results = []
    for claim in claims:
        verdict = call_llm_judge(claim, reference_text)
        results.append(verdict)
        print(f"    Claim: '{claim[:50]}...' -> {verdict}")
        
    total = len(results)
    supported = results.count("SUPPORTED")
    contradicted = results.count("CONTRADICTED")
    
    # Factual Accuracy = Supported / (Supported + Contradicted)
    # Исключаем Unverified из знаменателя, так как мы не можем их проверить
    checkable = supported + contradicted
    accuracy = supported / checkable if checkable > 0 else 0.0
    hallucination_rate = contradicted / checkable if checkable > 0 else 0.0
    
    return {
        "factual_accuracy": accuracy,
        "hallucination_rate": hallucination_rate,
        "total_claims": total,
        "supported": supported,
        "contradicted": contradicted
    }

# --- Интеграция в основной цикл ---

def run_experiment_b_with_judge(limit_queries: int = 3):
    print("\n=== EXPERIMENT B: LLM-as-Judge Evaluation ===")
    
    # ... (загрузка датасета и db_index как раньше) ...
    queries = [json.loads(l) for l in open(DATASET_H1_PATH)]
    db_index = load_goldapple_db()
    test_queries = queries[:limit_queries]
    
    for i, q in enumerate(test_queries):
        query_text = q['query']
        gt_ids = q['ground_truth_product_ids']
        
        print(f"\n[{i+1}/{len(test_queries)}] Query: '{query_text}'")
        rag_answer, _ = call_rag_system(query_text)
        
        # 2. Формируем Reference (описание продукта из GT)
        ref_text = ""
        if gt_ids and db_index:
            product = db_index.get(str(gt_ids[0]))
            if product:
                ref_text = product.get('description', '') + " " + product.get('ingredients', '')
        
        if not ref_text:
            continue
            
        # 3. Декомпозиция ответа на утверждения
        claims = decompose_answer_into_claims(rag_answer)
        print(f"  Decomposed into {len(claims)} claims.")
        
        # 4. Оценка судьей
        if claims:
            metrics = calculate_factual_accuracy(claims, ref_text)
            print(f"  Factual Accuracy: {metrics['factual_accuracy']:.2f}")
            print(f"  Hallucination Rate: {metrics['hallucination_rate']:.2f}")

if __name__ == "__main__":
    run_experiment_b_with_judge()