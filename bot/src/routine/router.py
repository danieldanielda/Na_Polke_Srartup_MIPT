import logging
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove

from src.states import UserState
from src.routine.routine_service import get_skincare_routine
from src.keyboards.keyboard import CustomKeyboard
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "📅 Составить полную рутину")
async def start_routine_mode(message: Message, state: FSMContext):
    await state.set_state(UserState.waiting_for_routine_query)
    await message.answer(
        "👩‍⚕️ <b>Архитектор косметической рутины</b>\n\n"
        "Опишите ваш тип кожи и проблемы, чтобы я подобрал полный уход.\n\n"
        "<i>Примеры:</i>\n"
        "• 'Жирная кожа, акне, нужен бюджетный уход'\n"
        "• 'Сухая чувствительная кожа, есть купероз'\n"
        "• 'Возрастная кожа, нужны анти-эйдж средства'",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(UserState.waiting_for_routine_query, F.text)
async def process_routine_query(message: Message, state: FSMContext):
    user_query = message.text.strip()
    
    if len(user_query) < 5:
        await message.answer("Пожалуйста, опишите проблему чуть подробнее.")
        return

    wait_msg = await message.answer("🧪 Анализирую составы... Это займет 2-4 минуты.")

    try:
        result_text = await get_skincare_routine(user_query)
        
        # Безопасное удаление сообщения о загрузке
        try:
            await wait_msg.delete()
        except Exception:
            pass 
        
        kb = await CustomKeyboard().recommendation_result_keyboard()
        
        response = f"✨ <b>Ваша персональная рутина:</b>\n\n{result_text}"
        
        await message.answer(
            response,
            parse_mode=ParseMode.HTML,
            reply_markup=kb
        )
        
        await state.set_state(UserState.analysis_finished)

    except Exception as e:
        logger.error(f"Routine error: {e}", exc_info=True)
        # Безопасное удаление в случае ошибки
        try:
            await wait_msg.delete()
        except Exception:
            pass
        await message.answer("❌ Что-то пошло не так при составлении рутины.")


async def get_routine_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Составить еще", callback_data="new_routine")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="to_main_menu")]
    ])

@router.callback_query(F.data == "new_routine", UserState.analysis_finished)
async def new_routine(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(UserState.waiting_for_routine_query)
    await callback.message.answer("Опишите новый запрос:")

@router.callback_query(F.data == "to_main_menu", UserState.analysis_finished)
async def to_main_menu_from_routine(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    kb = await CustomKeyboard().main_start_keyboard()
    await callback.message.answer("Главное меню:", reply_markup=kb)