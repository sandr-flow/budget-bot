"""
Telegram Bot для учета семейных финансов
Aiogram 3.x + Google Sheets + FSM
"""
import asyncio
import os
import re
from datetime import datetime
from typing import Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

# Загрузка переменных окружения
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
ALLOWED_USERS = [int(x.strip()) for x in os.getenv("ALLOWED_USERS", "").split(",") if x.strip()]

# Конфигурация таблицы
SHEET_TRANSACTIONS = "Транзакции"
SHEET_SETTINGS = "Settings"
START_ROW = 4
EXPENSE_COLS = {"date": 2, "amount": 3, "desc": 4, "category": 5}  # B-E
INCOME_COLS = {"date": 7, "amount": 8, "desc": 9, "category": 10}  # G-J
TIMEZONE_OFFSET = 4

# Кэш категорий
categories_cache = []


# ============================================
# FSM States
# ============================================

class TransactionStates(StatesGroup):
    waiting_amount = State()
    waiting_type = State()  # Ожидание выбора типа (расход/доход)
    waiting_category = State()
    waiting_description = State()  # Описание теперь в конце


# ============================================
# Google Sheets
# ============================================

def get_sheets_client():
    """Подключение к Google Sheets"""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file("analog-woodland-477311-j7-4045d01ab666.json", scopes=scopes)
    return gspread.authorize(creds)


def load_categories() -> list[dict]:
    """Загрузить категории"""
    global categories_cache
    try:
        client = get_sheets_client()
        sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_SETTINGS)
        data = sheet.get_all_values()
        
        categories_cache = []
        for row in data[1:]:
            if len(row) >= 2 and row[0] and row[1]:
                categories_cache.append({
                    "name": row[0].strip(),
                    "type": row[1].strip().lower()
                })
        print(f"Loaded {len(categories_cache)} categories")
        return categories_cache
    except Exception as e:
        print(f"Error getting categories: {e}")
        return []


def write_transaction(trans_type: str, amount: float, description: str, category: str):
    """Записать транзакцию"""
    try:
        client = get_sheets_client()
        sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_TRANSACTIONS)
        
        is_expense = "expense" in trans_type or "expence" in trans_type
        cols = EXPENSE_COLS if is_expense else INCOME_COLS
        
        date_values = sheet.col_values(cols["date"])
        next_row = max(len(date_values) + 1, START_ROW)
        
        from datetime import timezone, timedelta
        tz = timezone(timedelta(hours=TIMEZONE_OFFSET))
        date_str = datetime.now(tz).strftime("%d.%m.%Y")
        
        sheet.update_cell(next_row, cols["date"], date_str)
        sheet.update_cell(next_row, cols["amount"], amount)
        sheet.update_cell(next_row, cols["desc"], description)
        sheet.update_cell(next_row, cols["category"], category)
        
        print(f"Transaction saved: {trans_type} | {amount} | {description} | {category}")
        return True
    except Exception as e:
        print(f"Error writing transaction: {e}")
        return False


# ============================================
# Telegram Bot
# ============================================

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()


def main_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура: Расход / Доход"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💸 Расход", callback_data="type:expense"),
            InlineKeyboardButton(text="💰 Доход", callback_data="type:income")
        ]
    ])


def skip_keyboard() -> InlineKeyboardMarkup:
    """Кнопка пропустить описание"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_desc")]
    ])


def category_keyboard(trans_type: str) -> InlineKeyboardMarkup:
    """Клавиатура категорий (только релевантные)"""
    buttons = []
    row = []
    
    for i, cat in enumerate(categories_cache):
        # Фильтруем по типу
        cat_type = cat["type"]
        if trans_type == "expense" and ("expense" in cat_type or "expence" in cat_type):
            row.append(InlineKeyboardButton(text=cat["name"], callback_data=f"cat:{i}"))
        elif trans_type == "income" and "income" in cat_type:
            row.append(InlineKeyboardButton(text=cat["name"], callback_data=f"cat:{i}"))
        
        if len(row) == 2:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    
    # Кнопка отмены
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================
# Handlers
# ============================================

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Команда /start"""
    if message.from_user.id not in ALLOWED_USERS:
        return
    
    await state.clear()
    await message.answer(
        "👋 Привет! Выбери тип операции:",
        reply_markup=main_keyboard()
    )


@router.message(F.text, StateFilter(None))
async def any_message(message: Message, state: FSMContext):
    """Любое сообщение без состояния -> проверяем на число или показываем меню"""
    if message.from_user.id not in ALLOWED_USERS:
        return
    
    text = message.text.strip().replace(",", ".").replace(" ", "")
    
    # Проверяем, является ли ввод числом (суммой)
    try:
        amount = float(text)
        if amount > 0:
            # Сохраняем сумму и спрашиваем тип операции
            await state.update_data(amount=amount)
            await state.set_state(TransactionStates.waiting_type)
            await message.answer(
                f"💵 Сумма: <b>{amount}</b>\n\n"
                "Это расход или доход?",
                reply_markup=main_keyboard()
            )
            return
    except ValueError:
        pass
    
    # Если не число - показываем главное меню
    await message.answer(
        "Выбери тип операции:",
        reply_markup=main_keyboard()
    )


@router.callback_query(F.data.startswith("type:"), StateFilter(None))
async def select_type_no_amount(callback: CallbackQuery, state: FSMContext):
    """Выбор типа без предварительной суммы: сначала запрашиваем сумму"""
    if callback.from_user.id not in ALLOWED_USERS:
        return
    
    trans_type = callback.data.split(":")[1]
    emoji = "💸" if trans_type == "expense" else "💰"
    type_name = "расход" if trans_type == "expense" else "доход"
    
    await state.update_data(trans_type=trans_type)
    await state.set_state(TransactionStates.waiting_amount)
    
    await callback.message.edit_text(
        f"{emoji} <b>Добавляем {type_name}</b>\n\n"
        "Введи сумму:"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("type:"), TransactionStates.waiting_type)
async def select_type_with_amount(callback: CallbackQuery, state: FSMContext):
    """Выбор типа после ввода суммы: сразу показываем категории"""
    if callback.from_user.id not in ALLOWED_USERS:
        return
    
    trans_type = callback.data.split(":")[1]
    emoji = "💸" if trans_type == "expense" else "💰"
    type_name = "расход" if trans_type == "expense" else "доход"
    
    await state.update_data(trans_type=trans_type)
    data = await state.get_data()
    
    await state.set_state(TransactionStates.waiting_category)
    
    await callback.message.edit_text(
        f"{emoji} <b>{type_name.capitalize()}</b>\n"
        f"💵 Сумма: <b>{data['amount']}</b>\n\n"
        "🏷 Выбери категорию:",
        reply_markup=category_keyboard(trans_type)
    )
    await callback.answer()


@router.message(TransactionStates.waiting_amount)
async def enter_amount(message: Message, state: FSMContext):
    """Ввод суммы (после выбора типа)"""
    if message.from_user.id not in ALLOWED_USERS:
        return
    
    text = message.text.strip().replace(",", ".").replace(" ", "")
    
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError()
    except:
        await message.answer("❌ Введи корректную сумму (число больше 0):")
        return
    
    await state.update_data(amount=amount)
    data = await state.get_data()
    
    await state.set_state(TransactionStates.waiting_category)
    
    await message.answer(
        f"💵 Сумма: <b>{amount}</b>\n\n"
        "🏷 Выбери категорию:",
        reply_markup=category_keyboard(data["trans_type"])
    )


@router.callback_query(F.data.startswith("cat:"), TransactionStates.waiting_category)
async def select_category(callback: CallbackQuery, state: FSMContext):
    """Выбор категории -> переход к описанию"""
    if callback.from_user.id not in ALLOWED_USERS:
        return
    
    cat_index = int(callback.data.split(":")[1])
    category = categories_cache[cat_index]
    
    await state.update_data(category=category["name"])
    data = await state.get_data()
    
    await state.set_state(TransactionStates.waiting_description)
    
    is_expense = data["trans_type"] == "expense"
    emoji = "💸" if is_expense else "💰"
    type_name = "Расход" if is_expense else "Доход"
    
    await callback.message.edit_text(
        f"{emoji} <b>{type_name}</b>\n"
        f"💵 Сумма: <b>{data['amount']}</b>\n"
        f"🏷 Категория: <b>{category['name']}</b>\n\n"
        "📝 Введи описание или нажми «Пропустить»:",
        reply_markup=skip_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "skip_desc", TransactionStates.waiting_description)
async def skip_description(callback: CallbackQuery, state: FSMContext):
    """Пропуск описания -> сохранение транзакции"""
    if callback.from_user.id not in ALLOWED_USERS:
        return
    
    data = await state.get_data()
    
    # Записываем транзакцию
    success = write_transaction(
        data["trans_type"],
        data["amount"],
        "-",
        data["category"]
    )
    
    if success:
        is_expense = data["trans_type"] == "expense"
        emoji = "💸" if is_expense else "💰"
        type_text = "Расход" if is_expense else "Доход"
        
        await callback.message.edit_text(
            f"✅ <b>{type_text} записан!</b>\n\n"
            f"💵 Сумма: {data['amount']}\n"
            f"📝 Описание: -\n"
            f"🏷 Категория: {data['category']}"
        )
        await callback.answer("✅ Записано!")
    else:
        await callback.answer("❌ Ошибка записи", show_alert=True)
    
    await state.clear()


@router.message(TransactionStates.waiting_description)
async def enter_description(message: Message, state: FSMContext):
    """Ввод описания -> сохранение транзакции"""
    if message.from_user.id not in ALLOWED_USERS:
        return
    
    description = message.text.strip()[:100]  # Ограничиваем длину
    data = await state.get_data()
    
    # Записываем транзакцию
    success = write_transaction(
        data["trans_type"],
        data["amount"],
        description,
        data["category"]
    )
    
    if success:
        is_expense = data["trans_type"] == "expense"
        emoji = "💸" if is_expense else "💰"
        type_text = "Расход" if is_expense else "Доход"
        
        await message.answer(
            f"✅ <b>{type_text} записан!</b>\n\n"
            f"💵 Сумма: {data['amount']}\n"
            f"📝 Описание: {description}\n"
            f"🏷 Категория: {data['category']}"
        )
    else:
        await message.answer("❌ Ошибка записи")
    
    await state.clear()


# Старый обработчик select_category удалён - логика перенесена выше


@router.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена"""
    await state.clear()
    await callback.message.edit_text("❌ Отменено")
    await callback.answer()


# ============================================
# Main
# ============================================

dp.include_router(router)


async def main():
    """Запуск бота"""
    print("Bot starting...")
    print(f"Allowed users: {ALLOWED_USERS}")
    
    load_categories()
    
    await bot.delete_webhook(drop_pending_updates=True)
    print("Webhook deleted, starting polling...")
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
