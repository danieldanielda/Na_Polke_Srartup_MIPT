from aiogram.filters.command import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from src.states import UserState
from src.keyboards.keyboard import CustomKeyboard

router = Router()

AGREEMENT_TEXT = (
    "⚠️ <b>Перед началом работы ознакомьтесь с документами:</b>\n\n"
    "📄 <a href='https://www.notion.so/35041e61f65680acbd2df9c0bd705af5?source=copy_link'>Пользовательское соглашение</a>\n\n"
    "🛡 <a href='https://notion.so/35041e61f6568004bcb3e585743a7232?source=copy_link'>Политика обработки персональных данных</a>\n\n"
    "Нажимая «Принять и начать», вы подтверждаете, что ознакомились с документами и принимаете их условия.\n\n"
    "⚠️ <i>Важно: анализ основан на INCI-составе и справочных данных. Мы не знаем точные концентрации и технологию производства. Вывод является вероятностным и не гарантирует эффективность или безопасность. Brand names are trademarks of their respective owners.</i>"
)

@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    # 1. Устанавливаем состояние ожидания согласия
    await state.set_state(UserState.waiting_for_agreement)
    
    # 2. Показываем клавиатуру ТОЛЬКО с кнопкой "Принять"
    kb = await CustomKeyboard().start_agreement_keyboard()
    
    # 3. Отправляем сообщение с соглашением. Главного меню здесь НЕТ.
    await message.answer(
        AGREEMENT_TEXT,
        parse_mode=ParseMode.HTML,             
        disable_web_page_preview=True,          
        reply_markup=kb
    )

@router.callback_query(F.data == "accept_agreement", UserState.waiting_for_agreement)
async def accept_agreement(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    await state.update_data(agreement_accepted=True)
    
    try:
        await callback.message.delete()
    except Exception:
        pass

    kb = await CustomKeyboard().main_start_keyboard()
    
    await callback.message.answer(
        "👋 Привет! Я помогу тебе разобраться в косметике.\n\n"
        "Выбери, что хочешь сделать:",
        reply_markup=kb
    )
    
    await state.set_state(None) 


@router.message(F.text == "🔍 Анализ состава (Штрихкод/Название)")
async def start_analysis_mode(message: Message, state: FSMContext):
    await state.set_state(UserState.waiting_for_photo)
    await message.answer(
        "📸 <b>Режим анализа</b>\n\n"
        "Пришлите фото штрихкода косметики или ее название — я постараюсь найти полезную информацию о ней!\n\n"
        "⚠️ <b>Перед проверкой важно знать:</b>\n"
        "Анализ основан на INCI-составе и справочных данных об ингредиентах. Мы не знаем точные концентрации, технологию производства и результаты испытаний готовой формулы, если они не предоставлены производителем. Поэтому вывод является вероятностным и не гарантирует эффективность, безопасность или индивидуальную переносимость средства.\n\n"
        "⚠️ Названия брендов и продуктов используются только для идентификации анализируемых средств. Все товарные знаки принадлежат их правообладателям. Сервис не аффилирован с производителями, если прямо не указано иное.",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(Command("barcode"))
async def info(message: Message, state: FSMContext):

    await message.answer(
        "📌 <b>Советы по сканированию:</b>\n\n"
        "• Убедитесь, что штрихкод чёткий и не размыт\n"
        "• Хорошее освещение — обязательно\n"
        "• Держите камеру параллельно штрихкоду\n"
        "• Избегайте бликов и теней",
        parse_mode="HTML"
    )
    await state.set_state(UserState.waiting_for_photo)
    await message.answer(
        "📸 Пришлите фото штрихкода косметики или ее название — я постараюсь найти полезную информацию о ней!\n\n"
        "⚠️ <b>Перед проверкой важно знать:</b>\n"
        "Анализ основан на INCI-составе и справочных данных об ингредиентах. Мы не знаем точные концентрации, технологию производства и результаты испытаний готовой формулы, если они не предоставлены производителем. Поэтому вывод является вероятностным и не гарантирует эффективность, безопасность или индивидуальную переносимость средства.\n\n"
        "⚠️ Названия брендов и продуктов используются только для идентификации анализируемых средств. Все товарные знаки принадлежат их правообладателям. Сервис не аффилирован с производителями, если прямо не указано иное.",
        parse_mode="HTML"
    )

@router.message(F.text == "🧴 Подобрать средство по запросу")
async def start_recommendation_mode(message: Message, state: FSMContext):
    await state.set_state(UserState.waiting_for_recommendation_query)
    await message.answer(
        "🧴 <b>Режим подбора</b>\n\n"
        "Опишите, что вы ищете. Например:\n"
        "• <i>'Увлажняющий крем для сухой кожи'</i>\n"
        "• <i>'Сыворотка с витамином С'</i>\n"
        "• <i>'Гель для умывания для жирной кожи'</i>\n\n"
        "Напишите ваш запрос:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )
    
@router.message(F.text == "📅 Составить рутину")
async def start_routine_mode(message: Message, state: FSMContext):
    await state.set_state(UserState.waiting_for_routine_query)
    await message.answer(
        "Опишите вашу кожу и цели. Например: 'Жирная кожа, есть прыщи, хочу увлажнение'", 
        reply_markup=ReplyKeyboardRemove()
    )