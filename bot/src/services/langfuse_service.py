import uuid

from langfuse import Langfuse
from config import BotSettings
import logging

settings = BotSettings()
logger = logging.getLogger(__name__)

langfuse_client = Langfuse(
    public_key=settings.langfuse_public_key,
    secret_key=settings.langfuse_secret_key,
    host=settings.langfuse_host
)
def start_analysis_trace(user_id: str, product_identifier: str, analysis_type: str) -> str | None:
    """
    Создает новый трейс в Langfuse и возвращает его ID.
    Вызывать в начале процесса анализа.
    """
    if not langfuse_client:
        return None

    try:
        trace_id = f"analysis_{uuid.uuid4()}"
        
        langfuse_client.api.trace.create(
            id=trace_id,
            name="product_analysis",
            user_id=str(user_id),
            input={
                "product_identifier": product_identifier,
                "analysis_type": analysis_type
            }
        )
        
        logger.debug(f"Created Langfuse trace: {trace_id}")
        return trace_id
        
    except Exception as e:
        logger.error(f"Failed to create Langfuse trace: {e}", exc_info=True)
        return None


async def log_feedback(user_id: str, username: str, rating: int, context: str, trace_id: str | None = None):
    """
    Логирует оценку в Langfuse.
    Если trace_id передан, оценка привязывается к существующему трейсу.
    Если нет, создается отдельный трейс только для оценки.
    """
    if not langfuse_client:
        logger.debug("Langfuse client not initialized, skipping feedback log.")
        return

    try:
        # Если trace_id не передан, генерируем новый, чтобы оценка не потерялась
        target_trace_id = trace_id or f"feedback_only_{uuid.uuid4()}"

        # Если трейса с таким ID еще не существует (случай feedback_only),
        # Langfuse создаст его автоматически при добавлении скора, 
        # но лучше явно создать его для чистоты данных, если это новый трейс.
        if not trace_id:
            try:
                langfuse_client.api.trace.create(
                    id=target_trace_id,
                    name="user_feedback_standalone",
                    user_id=str(user_id),
                    input={"context": context}
                )
            except:
                pass # Игнорируем ошибки создания дублей, если вдруг

        # Отправляем оценку
        langfuse_client.score(
            name="user_feedback_rating",
            value=float(rating),
            trace_id=target_trace_id,
            comment=f"User: @{username}",
            data_type="NUMERIC"
        )
        
        # Принудительная отправка данных
        langfuse_client.flush()
        
        logger.info(f"Score {rating} logged for user {user_id} in trace {target_trace_id}")
        
    except Exception as e:
        logger.error(f"Failed to send score to Langfuse: {e}", exc_info=True)