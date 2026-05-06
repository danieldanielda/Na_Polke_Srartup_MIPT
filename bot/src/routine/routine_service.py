import httpx
import logging
from config import BotSettings

logger = logging.getLogger(__name__)
settings = BotSettings()

AGENTS_API_URL = f"{settings.agents_api_base}/api/v1/crew/build_routine"

async def get_skincare_routine(user_query: str) -> str:
    payload = {
        "query": user_query,
        "collection_id": "global_collection"
    }

    try:
        logger.info(f"Requesting routine for: {user_query}")
        timeout = httpx.Timeout(
            connect=10.0,   # таймаут подключения
            read=300.0,     # таймаут чтения
            write=60.0,     # таймаут записи (можно меньше)
            pool=60.0       # таймаут ожидания соединения из пула
        )
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(AGENTS_API_URL, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("routine", "Не удалось составить рутину.")
            else:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return "❌ Произошла ошибка на стороне сервиса рекомендаций."
                
    except httpx.ReadTimeout:
        logger.error("Routine API Read Timeout")
        return "⏳ Превышено время ожидания. Попробуйте упростить запрос или повторите позже."
    except httpx.ConnectError:
        return "❌ Не удалось подключиться к сервису анализа."
    except Exception as e:
        logger.error(f"Routine service error: {e}", exc_info=True)
        return "❌ Произошла непредвиденная ошибка."