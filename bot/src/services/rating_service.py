# src/services/rating_service.py
import logging
from src.database.models import Rating
from src.database.engine import session_maker

logger = logging.getLogger(__name__)

async def save_rating(user_id: int, username: str | None, rating: int, context: str, product_id: str):
    """
    Асинхронно сохраняет оценку в PostgreSQL через SQLAlchemy ORM.
    """
    try:
        async with session_maker() as session:
            new_rating = Rating(
                user_id=user_id,
                username=username,
                rating_value=rating,
                context=context,
                product_id=product_id
            )
            
            session.add(new_rating)
            
            await session.commit()
            
            logger.info(f"Rating saved: User={user_id}, Value={rating}, Context={context}")
            
    except Exception as e:
        if 'session' in locals():
            await session.rollback()
        logger.error(f"Error saving rating to DB: {e}", exc_info=True)
        raise