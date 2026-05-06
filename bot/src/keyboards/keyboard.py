from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

class CustomKeyboard:
    
    def __init__(self):
        pass
    
    async def main_keyboard(self) -> InlineKeyboardMarkup:
        balance_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text='☘️ Безопасность состава', callback_data='description')],
                [InlineKeyboardButton(text='🔍 Полный анализ средства', callback_data='summary')],
            ]
        )
        return balance_keyboard
    
    async def after_analysis_keyboard(self) -> InlineKeyboardMarkup:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Повторить анализ средства", callback_data="repeat_analysis")],
                [InlineKeyboardButton(text="📷 Загрузить новое фото или название", callback_data="new_photo")],
            ]
        )
        return keyboard
    
    async def translate_to_ru(self):
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🌍 Перевести на русский",
                        callback_data="translate_ru"
                    )
                ]
            ]
        )

    async def translate_to_en(self):
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🌍 Translate to English",
                        callback_data="translate_en"
                    )
                ]
            ]
        )
        
    async def main_start_keyboard(self) -> ReplyKeyboardMarkup:
        """Главное меню с выбором режима"""
        keyboard = [
            [KeyboardButton(text="🔍 Анализ состава (Штрихкод/Название)")],
            [KeyboardButton(text="🧴 Подобрать средство по запросу")]
        ]
        return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

    async def recommendation_result_keyboard(self) -> InlineKeyboardMarkup:
        """Клавиатура после выдачи рекомендаций"""
        inline_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Подобрать еще", callback_data="new_recommendation")],
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_main_menu")]
        ])
        return inline_kb
    
    async def main_start_keyboard(self) -> ReplyKeyboardMarkup:
        """Главное меню с выбором режима"""
        keyboard = [
            [KeyboardButton(text="🔍 Анализ состава (Штрихкод/Название)")],
            [KeyboardButton(text="🧴 Подобрать средство по запросу")],
            [KeyboardButton(text="📅 Составить полную рутину")]
        ]
        return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    
    async def after_analysis_keyboard(self) -> InlineKeyboardMarkup:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Повторить анализ", callback_data="repeat_analysis")],
                [InlineKeyboardButton(text="📷 Новое фото/название", callback_data="new_photo")],
                [InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_main_menu_from_analysis")] # <--- ДОБАВИТЬ ЭТО
            ]
        )
        return keyboard
    
    async def start_agreement_keyboard(self) -> InlineKeyboardMarkup:
        """Клавиатура для согласия с условиями"""
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Принять и начать", callback_data="accept_agreement")]
        ])
        return kb
    
    async def get_rating_keyboard(self):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="1", callback_data="rate_1"),
                InlineKeyboardButton(text="2", callback_data="rate_2"),
                InlineKeyboardButton(text="3", callback_data="rate_3"),
                InlineKeyboardButton(text="4", callback_data="rate_4"),
                InlineKeyboardButton(text="5", callback_data="rate_5"),
            ]
        ])
        return keyboard