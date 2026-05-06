import os
import re
import tempfile
import logging
import asyncio
from aiogram import F, Router
from aiogram.types import Message, ContentType, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import StateFilter

from src.services.langfuse_service import log_feedback, start_analysis_trace
from src.services.rating_service import save_rating
from src.states import UserState
from src.utils import decode_barcode_with_cv2, get_product_analysis_by_barcode, get_product_analysis_by_name, format_analysis_for_telegram
from src.keyboards.keyboard import CustomKeyboard

logger = logging.getLogger(__name__)
router = Router()


def escape_md_v2(text: str) -> str:
    escape_chars = r"_*[]()~`>#+-=|{}.!?"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)


async def send_analysis_result(message: Message, product_identifier: str, analysis_result: str | None):
    """
    Просто отправляет форматированный результат анализа.
    """
    if not analysis_result:
        await message.reply(
            f"🔍 Штрихкод/Продукт: <code>{product_identifier}</code>\n\n"
            "Нам не удалось надежно определить полный INCI-состав средства.\n\n"
            "Анализ может быть неполным или неточным. Для более корректного результата загрузите фото состава с упаковки или введите состав вручную.\n\n",
            parse_mode=ParseMode.HTML
        )
        return

    formatted_analysis = await format_analysis_for_telegram(analysis_result)

    text = f"<b>Штрихкод/Продукт:</b> <code>{product_identifier}</code>\n\n{formatted_analysis}"

    keyboard = await CustomKeyboard().translate_to_ru()

    await message.reply(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


async def initiate_rating_flow(message: Message, state: FSMContext, product_id: str, analysis_type: str):
    """
    Универсальная функция: сохраняет контекст, переключает стейт на оценку и показывает кнопки 1-5.
    """
    await state.update_data(
        last_product_id=product_id,
        last_analysis_type=analysis_type,
    )
    
    await state.set_state(UserState.waiting_for_rating)
    
    await message.answer(
        "Насколько результат анализа помог вам понять, стоит ли рассматривать это средство к покупке?",
        reply_markup=await CustomKeyboard().get_rating_keyboard()
    )


@router.message(F.text == "ℹ️ Как снимать штрихкод")
async def how_to_scan(message: Message):
    await message.answer(
        "📌 Советы:\n"
        "• Убедитесь, что штрихкод чёткий и не размыт\n"
        "• Хорошее освещение — обязательно\n"
        "• Держите камеру параллельно штрихкоду\n"
        "• Избегайте бликов и теней"
    )


@router.message(F.text & F.text.regexp(r"^\d+$"))
async def handle_barcode_text(message: Message, state: FSMContext):
    barcode = message.text.strip()
    await state.update_data(barcode=barcode, product_name=None)
    await state.set_state(UserState.waiting_for_analysis_type)
    
    keyboard = await CustomKeyboard().main_keyboard()
    await message.reply(
        f"Штрихкод: `{barcode}`\n\nВыберите тип анализа:",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=keyboard
    )


@router.callback_query(F.data.in_(["description", "summary"]))
async def handle_analysis_selection(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()

    data = await state.get_data()
    barcode = data.get("barcode")
    product_name = data.get("product_name")
    analysis_type = callback_query.data
    
    user_id = callback_query.from_user.id
    product_identifier = barcode if barcode else product_name

    wait_msg = await callback_query.message.reply(
        "🔍 Собираю информацию и анализирую состав.\n\n"
        "Анализ может занять до одной минуты, пожалуйста, ожидайте.\n\n"
        "Обязательно пришлю уведомление, когда анализ будет готов.\n\n"
    )

    try:
        if barcode:
            analysis_result = await get_product_analysis_by_barcode(barcode, analysis_type)
        elif product_name:
            analysis_result = await get_product_analysis_by_name(product_name, analysis_type)
        else:
            await callback_query.message.reply("❌ Не удалось определить продукт для анализа.")
            return

        # 1. Отправляем сам результат анализа
        await send_analysis_result(
            callback_query.message,
            product_identifier,
            analysis_result
        )
        
        await state.update_data(original_analysis=analysis_result)

        await initiate_rating_flow(
            message=callback_query.message,
            state=state,
            product_id=product_identifier,
            analysis_type=analysis_type
        )

    except Exception as e:
        logger.error(f"Error during product lookup: {e}", exc_info=True)
        await callback_query.message.reply("❌ Произошла ошибка при обработке запроса.")
    finally:
        try:
            await callback_query.bot.delete_message(
                chat_id=callback_query.message.chat.id,
                message_id=wait_msg.message_id
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("rate_"), UserState.waiting_for_rating)
async def handle_rating(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    rating = int(callback_query.data.split("_")[1])
    
    user_data = await state.get_data()
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username
    context_type = user_data.get("last_analysis_type", "unknown")
    product_id = user_data.get("last_product_id", "Unknown")
    
    try:
        await save_rating(
            user_id=user_id,
            username=username,
            rating=rating,
            context=context_type,
            product_id=product_id
        )
    except Exception as e:
        logger.error(f"Failed to save rating: {e}")

    # Визуальное подтверждение оценки
    try:
        await callback_query.message.edit_text(
            text=f"Насколько результат анализа помог вам понять, стоит ли рассматривать это средство к покупке?\n\n✅ Спасибо за оценку: {rating}/5",
            reply_markup=None
        )
    except:
        pass

    await show_post_analysis_menu(callback_query.message, state)

async def show_post_analysis_menu(message: Message, state: FSMContext):
    """Показывает кнопки 'Новое фото', 'Повторить' и т.д."""
    keyboard = await CustomKeyboard().after_analysis_keyboard()

    await message.answer(
        "Что хотите сделать дальше?",
        reply_markup=keyboard
    )

    await state.set_state(UserState.analysis_finished)


@router.callback_query(F.data == "repeat_analysis", UserState.analysis_finished)
async def repeat_analysis(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    keyboard = await CustomKeyboard().main_keyboard()
    await callback.message.answer(
        "Выберите тип анализа:",
        reply_markup=keyboard
    )
    await state.set_state(UserState.waiting_for_analysis_type)


@router.callback_query(F.data == "new_photo", UserState.analysis_finished)
async def new_photo(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    # Сбрасываем данные предыдущего продукта
    await state.update_data(barcode=None, product_name=None, langfuse_trace_id=None)
    
    await callback.message.answer(
        "📸 Пришлите фото штрихкода косметики или ее название — я постараюсь найти полезную информацию о ней!\n\n"
        "⚠️ <b>Перед проверкой важно знать:</b>\n"
        "Анализ основан на INCI-составе и справочных данных об ингредиентах. Мы не знаем точные концентрации, технологию производства и результаты испытаний готовой формулы, если они не предоставлены производителем. Поэтому вывод является вероятностным и не гарантирует эффективность, безопасность или индивидуальную переносимость средства.\n\n"
        "⚠️ Названия брендов и продуктов используются только для идентификации анализируемых средств. Все товарные знаки принадлежат их правообладателям. Сервис не аффилирован с производителями, если прямо не указано иное.",
        parse_mode="HTML"
    )
    await state.set_state(UserState.waiting_for_photo)


@router.message(
    F.text, 
    ~F.text.regexp(r"^\d+$"), 
    StateFilter(UserState.waiting_for_photo, UserState.waiting_for_analysis_type)
)
async def handle_product_name_text(message: Message, state: FSMContext):
    product_name = message.text.strip()
    await state.update_data(product_name=product_name, barcode=None)
    await state.set_state(UserState.waiting_for_analysis_type)
    
    keyboard = await CustomKeyboard().main_keyboard()
    await message.reply(
        f"Название продукта: `{product_name}`\n\nВыберите тип анализа:",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=keyboard
    )


@router.message(UserState.waiting_for_photo, F.content_type == ContentType.PHOTO)
async def handle_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        await message.bot.download(photo, destination=tmp_path)
        barcode = await asyncio.to_thread(decode_barcode_with_cv2, tmp_path)

        if not barcode:
            await message.reply(
                "❌ Не удалось распознать штрихкод.\n\n"
                "Попробуйте сделать фото чётче или в другом ракурсе."
            )
            return

        keyboard = await CustomKeyboard().main_keyboard()
        await message.reply(
            f"Штрихкод: `{barcode}`\n\nВыберите тип анализа:",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard
        )

        await state.update_data(barcode=barcode, product_name=None)
        await state.set_state(UserState.waiting_for_analysis_type)

    except Exception as e:
        logger.error(f"Error processing photo: {e}", exc_info=True)
        await message.reply("❌ Ошибка при обработке изображения.")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            
            
@router.callback_query(F.data == "to_main_menu_from_analysis", UserState.analysis_finished)
async def to_main_menu_from_analysis(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    
    kb = await CustomKeyboard().main_start_keyboard()
    await callback.message.answer(
        "Вы вернулись в главное меню. Выберите действие:",
        reply_markup=kb
    )