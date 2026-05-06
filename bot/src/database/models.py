from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.types import String, DateTime, Integer, BigInteger
from sqlalchemy import func

class Base(AsyncAttrs, DeclarativeBase):
    created_time: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
    updated_time: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

class Rating(Base):
    __tablename__ = 'ratings'
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True) # Индекс для быстрого поиска по юзеру
    username: Mapped[str] = mapped_column(String, nullable=True) 
    rating_value: Mapped[int] = mapped_column(Integer, nullable=False) 
    context: Mapped[str] = mapped_column(String, nullable=True) 
    product_id: Mapped[str] = mapped_column(String, nullable=True) 