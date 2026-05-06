# main.py
import logging
import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from src.start_router import router as start_router
from src.parse_barcode.router import router as barcode_router
from src.translator.router import router as translate_router
from src.recommendation.router import router as rec_router
from src.routine.router import router as routine_router

from config import BotSettings
from src.database.engine import create_db

logger = logging.getLogger(__name__)
settings = BotSettings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    stream=sys.stdout,
)

bot = Bot(token=settings.tg_api_key)
dp = Dispatcher()

async def setup_bot_commands():
    bot_commands = [
        BotCommand(command="/start", description="Запуск/Перезапуск бота"),
        BotCommand(command="/barcode", description="Как снимать штрихкод")
    ]
    await bot.set_my_commands(bot_commands)
            
async def on_startup():
    logger.info("Bot is starting up...")
    await create_db()
    logger.info("Database tables checked/created.")
    await setup_bot_commands()

async def main():
    
    dp.include_router(start_router)
    dp.include_router(barcode_router)
    dp.include_router(translate_router)
    dp.include_router(rec_router)
    dp.include_router(routine_router)
    
    dp.startup.register(on_startup)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit from Bot')