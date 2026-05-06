import logging
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from src.states import UserState
from src.utils import get_product_recommendations
from src.keyboards.keyboard import CustomKeyboard

logger = logging.getLogger(__name__)
router = Router()

# 1. Старт режима рекомендаций (может вызываться по кнопке из главного меню)
@router.message(F.text == "🧴 Подобрать средство по запросу")
async def start_recommendation_mode(message: Message, state: FSMContext):
    await state.set_state(UserState.waiting_for_recommendation_query)
    await message.answer(
        "🧴 <b>Режим подбора средств</b>\n\n"
        "Опишите, что вы ищете. Например:\n"
        "• <i>'Подбери увлажняющий крем для сухой кожи'</i>\n"
        "• <i>'Сыворотка с витамином С'</i>\n"
        "• <i>'Гель для умывания для жирной кожи'</i>\n\n"
        "Напишите ваш запрос:",
        parse_mode=ParseMode.HTML
    )

# 2. Обработка текстового запроса
@router.message(UserState.waiting_for_recommendation_query, F.text)
async def process_recommendation_query(message: Message, state: FSMContext):
    user_query = message.text.strip()
    
    if len(user_query) < 3:
        await message.answer("Пожалуйста, опишите запрос чуть подробнее.")
        return

    # Показываем индикатор загрузки
    wait_msg = await message.answer("🔍 Ищу подходящие средства в базе...")

    try:
        # Дергаем наш новый сервис, который стучится в API
        result_text = await get_product_recommendations(user_query)
        
        await wait_msg.delete()
        
        final_response = f"✨ <b>Результаты поиска:</b>\n<i>По запросу: \"{user_query}\"</i>\n\n{result_text}"
        
        # Клавиатура для дальнейших действий
        keyboard = await CustomKeyboard().recommendation_result_keyboard()
        
        await message.answer(
            final_response,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
        # Переводим в состояние ожидания следующего действия
        await state.set_state(UserState.analysis_finished)

    except Exception as e:
        logger.error(f"Error processing recommendation: {e}", exc_info=True)
        await wait_msg.delete()
        await message.answer("❌ Произошла ошибка при получении рекомендаций.")

# 3. Кнопка "Новый подбор"
@router.callback_query(F.data == "new_recommendation", UserState.analysis_finished)
async def new_recommendation(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(UserState.waiting_for_recommendation_query)
    await callback.message.answer("Напишите новый запрос для подбора средств:")

# 4. Кнопка "В главное меню"
@router.callback_query(F.data == "to_main_menu", UserState.analysis_finished)
async def to_main_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    # Возвращаем главную клавиатуру
    from src.keyboards.keyboard import CustomKeyboard
    kb = await CustomKeyboard().main_start_keyboard()
    await callback.message.answer("Вы в главном меню. Выберите действие:", reply_markup=kb)