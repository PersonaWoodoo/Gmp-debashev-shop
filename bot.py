import sqlite3
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    Message, CallbackQuery, FSInputFile
)

# ========== КОНФИГ ==========
BOT_TOKEN = "8675588098:AAG4lZtET6JxWLjgP5Octf6Woy9vvUE2uXo"
ADMIN_ID = 0  # ← ЗАМЕНИ НА СВОЙ ID

SUPPORT_USERNAME = "@debashev"
REVIEWS_USERNAME = "@ot3blBbl_debashev"
CHANNEL_USERNAME = "@DEBASHEV_CHANELL"
BOT_USERNAME = "@pdslnhshop_bot"

DEFAULT_GMP_RATE = 0.3
DEFAULT_STAR_RATE = 2.0
MIN_GMP_ORDER = 50
MIN_STAR_ORDER = 15
BONUS_PERCENT = 3

# ========== БАЗА ДАННЫХ ==========
DB_NAME = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
        registered_at TEXT, banned INTEGER DEFAULT 0,
        total_gmp_received REAL DEFAULT 0, bonus_tickets INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        gmp_amount REAL, price_rub REAL, price_stars REAL,
        payment_method TEXT, status TEXT DEFAULT 'pending',
        screenshot_id TEXT, admin_comment TEXT,
        created_at TEXT, updated_at TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS promo_codes (
        code TEXT PRIMARY KEY, bonus_percent INTEGER,
        max_uses INTEGER, used_count INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1, created_at TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT)''')
    # Настройки по умолчанию
    defaults = [
        ('gmp_rate', str(DEFAULT_GMP_RATE)),
        ('star_rate', str(DEFAULT_STAR_RATE)),
        ('requisites', 'Реквизиты не заданы'),
        ('lottery_active', '0')
    ]
    for key, value in defaults:
        cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

def get_setting(key):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def set_setting(key, value):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

def register_user(user_id, username, first_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username, first_name, registered_at) VALUES (?, ?, ?, ?)',
                   (user_id, username, first_name, datetime.now().strftime('%Y-%m-%d %H:%M')))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def get_orders(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders WHERE user_id = ? ORDER BY order_id DESC LIMIT 10', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def create_order(user_id, gmp_amount, price_rub, price_stars, payment_method):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    cursor.execute('''INSERT INTO orders (user_id, gmp_amount, price_rub, price_stars, payment_method, created_at, updated_at)
                      VALUES (?, ?, ?, ?, ?, ?, ?)''',
                   (user_id, gmp_amount, price_rub, price_stars, payment_method, now, now))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id

def update_order_status(order_id, status, admin_comment=''):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    cursor.execute('UPDATE orders SET status = ?, admin_comment = ?, updated_at = ? WHERE order_id = ?',
                   (status, admin_comment, now, order_id))
    if status == 'completed':
        cursor.execute('SELECT user_id, gmp_amount FROM orders WHERE order_id = ?', (order_id,))
        order = cursor.fetchone()
        if order:
            cursor.execute('UPDATE users SET total_gmp_received = total_gmp_received + ? WHERE user_id = ?',
                           (order[1], order[0]))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    stats = {}
    cursor.execute('SELECT COUNT(*) FROM users'); stats['users'] = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM users WHERE banned = 1'); stats['banned'] = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "pending"'); stats['pending'] = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "completed"'); stats['completed'] = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "cancelled"'); stats['cancelled'] = cursor.fetchone()[0]
    cursor.execute('SELECT COALESCE(SUM(gmp_amount), 0) FROM orders WHERE status = "completed"'); stats['gmp_given'] = cursor.fetchone()[0]
    cursor.execute('SELECT COALESCE(SUM(bonus_tickets), 0) FROM users'); stats['bonuses'] = cursor.fetchone()[0]
    cursor.execute('SELECT COALESCE(SUM(price_rub), 0) FROM orders WHERE status = "completed"'); stats['rub_flow'] = cursor.fetchone()[0]
    cursor.execute('SELECT COALESCE(SUM(price_stars), 0) FROM orders WHERE status = "completed"'); stats['stars_flow'] = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM orders'); stats['total_orders'] = cursor.fetchone()[0]
    conn.close()
    return stats

# ========== СОСТОЯНИЯ ==========
class OrderStates(StatesGroup):
    choosing_payment = State()
    entering_gmp = State()
    entering_rub = State()
    entering_stars = State()
    waiting_screenshot = State()

class AdminStates(StatesGroup):
    waiting_rate_gmp = State()
    waiting_rate_star = State()
    waiting_requisites = State()
    waiting_promo_code = State()
    waiting_promo_percent = State()
    waiting_promo_uses = State()
    waiting_confirm_order = State()
    waiting_search = State()

# ========== КЛАВИАТУРЫ ==========
def main_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🟢 Купить GMP")],
        [KeyboardButton(text="📢 Канал"), KeyboardButton(text="👤 Поддержка")],
        [KeyboardButton(text="⭐ Отзывы"), KeyboardButton(text="👤 Мой профиль")],
        [KeyboardButton(text="💬 Бонусы"), KeyboardButton(text="📋 Лотерея")]
    ], resize_keyboard=True)

def payment_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="💳 Рубли"), KeyboardButton(text="⭐ Звёзды")],
        [KeyboardButton(text="🔙 Назад")]
    ], resize_keyboard=True)

def cancel_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="❌ Отменить заказ")]
    ], resize_keyboard=True)

def admin_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📋 Заказы")],
        [KeyboardButton(text="💱 Изменить курс"), KeyboardButton(text="💳 Реквизиты")],
        [KeyboardButton(text="🎟 Промокод"), KeyboardButton(text="📥 База данных")],
        [KeyboardButton(text="🔍 Поиск"), KeyboardButton(text="⬅️ Выйти из админки")]
    ], resize_keyboard=True)

def back_admin_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🔙 Назад в админку")]
    ], resize_keyboard=True)

# ========== БОТ ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ========== ХЕНДЛЕРЫ ==========

# /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    register_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(
        f"⭐ Здравствуй, #{message.from_user.username or message.from_user.first_name}! ⭐\n\n"
        "🎉 Ты попал в бота-продавца GMP.\n"
        "📈 Здесь ты можешь быстро приобрести GMP по самому выгодному курсу!\n\n"
        "🔵 Наши преимущества:\n"
        "• Мгновенная выдача\n"
        "• Бонусы за профиль\n"
        "• Удобные способы оплаты\n"
        "• Лотерея с призами\n\n"
        "👤 Выбери что тебя интересует:",
        reply_markup=main_keyboard()
    )

# Админ-панель
@dp.message(F.text == "👑 Админ")
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("🚫 Нет доступа")
        return
    await message.answer("👑 Админ-панель:", reply_markup=admin_keyboard())

@dp.message(F.text == "⬅️ Выйти из админки")
async def exit_admin(message: Message):
    await message.answer("👤 Главное меню:", reply_markup=main_keyboard())

@dp.message(F.text == "📊 Статистика")
async def admin_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    s = get_stats()
    text = (
        "📊 СТАТИСТИКА\n\n"
        f"👥 Пользователей: {s['users']}\n"
        f"🚫 Забанено: {s['banned']}\n"
        f"⏳ Заказов ожидает: {s['pending']}\n"
        f"✅ Выполнено: {s['completed']}\n"
        f"❌ Отменено: {s['cancelled']}\n"
        f"💰 GMP выдано: {s['gmp_given']}\n"
        f"🎁 Бонусов выдано: {s['bonuses']}\n"
        f"💵 Оборот ₽: {s['rub_flow']:.2f}\n"
        f"⭐ Оборот ⭐: {s['stars_flow']:.0f}\n"
        f"📦 Заказов всего: {s['total_orders']}"
    )
    await message.answer(text)

@dp.message(F.text == "📋 Заказы")
async def admin_orders(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders ORDER BY order_id DESC LIMIT 10')
    orders = cursor.fetchall()
    conn.close()
    if not orders:
        await message.answer("📋 Нет заказов")
        return
    for o in orders:
        status_emoji = {"pending": "⏳", "completed": "✅", "cancelled": "❌"}
        text = (
            f"📦 Заказ #{o[0]}\n"
            f"👤 ID: {o[1]}\n"
            f"💎 GMP: {o[2]}\n"
            f"💵 ₽: {o[3]} | ⭐: {o[4]}\n"
            f"💳 Метод: {o[5]}\n"
            f"📌 Статус: {status_emoji.get(o[6], '❓')} {o[6]}\n"
            f"📅 {o[9]}"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_{o[0]}"),
             InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_{o[0]}")]
        ])
        await message.answer(text, reply_markup=kb)

@dp.callback_query(F.data.startswith("approve_"))
async def approve_order(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    order_id = int(callback.data.split("_")[1])
    update_order_status(order_id, "completed")
    await callback.message.edit_text(callback.message.text.replace("⏳ pending", "✅ completed"))
    await callback.answer("✅ Заказ подтверждён")
    # Уведомить пользователя
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, gmp_amount FROM orders WHERE order_id = ?', (order_id,))
    order = cursor.fetchone()
    conn.close()
    if order:
        try:
            await bot.send_message(order[0],
                f"✅ Ваш заказ #{order_id} выполнен!\n💎 Получено: {order[1]} GMP\nСпасибо за покупку!")
        except:
            pass

@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_order(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    order_id = int(callback.data.split("_")[1])
    update_order_status(order_id, "cancelled", "Отменено админом")
    await callback.message.edit_text(callback.message.text.replace("⏳ pending", "❌ cancelled"))
    await callback.answer("❌ Заказ отменён")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM orders WHERE order_id = ?', (order_id,))
    order = cursor.fetchone()
    conn.close()
    if order:
        try:
            await bot.send_message(order[0], f"❌ Ваш заказ #{order_id} отменён администратором.")
        except:
            pass

@dp.message(F.text == "💱 Изменить курс")
async def change_rate_menu(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    gmp = get_setting('gmp_rate')
    star = get_setting('star_rate')
    text = f"💱 Текущие курсы:\n1 GMP = {gmp} ₽\n1 ⭐ = {star} ₽\n\nВведи новый курс для GMP (в рублях):"
    await message.answer(text, reply_markup=back_admin_keyboard())
    await state.set_state(AdminStates.waiting_rate_gmp)

@dp.message(AdminStates.waiting_rate_gmp)
async def set_gmp_rate(message: Message, state: FSMContext):
    try:
        rate = float(message.text.replace(",", "."))
        set_setting('gmp_rate', str(rate))
        await message.answer(f"✅ Курс GMP обновлён: 1 GMP = {rate} ₽\nТеперь введи курс звёзд (1 ⭐ = X ₽):")
        await state.set_state(AdminStates.waiting_rate_star)
    except ValueError:
        await message.answer("❌ Введи число!")

@dp.message(AdminStates.waiting_rate_star)
async def set_star_rate(message: Message, state: FSMContext):
    try:
        rate = float(message.text.replace(",", "."))
        set_setting('star_rate', str(rate))
        await message.answer(f"✅ Курс звёзд обновлён: 1 ⭐ = {rate} ₽", reply_markup=admin_keyboard())
        await state.clear()
    except ValueError:
        await message.answer("❌ Введи число!")

@dp.message(F.text == "💳 Реквизиты")
async def show_requisites(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    req = get_setting('requisites')
    await message.answer(f"💳 Текущие реквизиты:\n{req}\n\nВведи новые реквизиты:", reply_markup=back_admin_keyboard())
    await state.set_state(AdminStates.waiting_requisites)

@dp.message(AdminStates.waiting_requisites)
async def set_requisites(message: Message, state: FSMContext):
    set_setting('requisites', message.text)
    await message.answer("✅ Реквизиты обновлены!", reply_markup=admin_keyboard())
    await state.clear()

@dp.message(F.text == "📥 База данных")
async def download_db(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer_document(FSInputFile(DB_NAME), caption="📥 База данных")

@dp.message(F.text == "🔍 Поиск")
async def search_start(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("🔍 Введи ID пользователя или номер заказа:", reply_markup=back_admin_keyboard())
    await state.set_state(AdminStates.waiting_search)

@dp.message(AdminStates.waiting_search)
async def search_result(message: Message, state: FSMContext):
    query = message.text.strip()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Пробуем как ID заказа
    cursor.execute('SELECT * FROM orders WHERE order_id = ?', (query,))
    order = cursor.fetchone()
    if order:
        await message.answer(f"📦 Заказ #{order[0]}\n👤 ID: {order[1]}\n💎 GMP: {order[2]}\n💵 ₽: {order[3]}\n📌 Статус: {order[6]}")
        conn.close()
        await state.clear()
        return
    # Пробуем как ID пользователя
    cursor.execute('SELECT * FROM orders WHERE user_id = ? ORDER BY order_id DESC LIMIT 5', (query,))
    orders = cursor.fetchall()
    if orders:
        text = f"👤 Заказы пользователя {query}:\n\n"
        for o in orders:
            text += f"📦 #{o[0]} | 💎 {o[2]} GMP | 📌 {o[6]}\n"
        await message.answer(text)
    else:
        await message.answer("❌ Ничего не найдено")
    conn.close()
    await state.clear()

# ========== ПОЛЬЗОВАТЕЛЬСКИЕ ХЕНДЛЕРЫ ==========

@dp.message(F.text == "🟢 Купить GMP")
async def buy_gmp(message: Message):
    gmp_rate = float(get_setting('gmp_rate'))
    star_rate = float(get_setting('star_rate'))
    await message.answer(
        f"💱 КАЛЬКУЛЯТОР GMP\n\n"
        f"📌 Курс: 1 GMP = {gmp_rate} ₽\n"
        f"📌 Звёзды: 1 ⭐ = {star_rate} ₽\n\n"
        f"🔢 Минимальный заказ: {MIN_GMP_ORDER} GMP\n"
        f"⭐ Минимально звёздами: {MIN_STAR_ORDER} ⭐\n\n"
        f"Введи сколько GMP хочешь купить:",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(OrderStates.entering_gmp)

@dp.message(OrderStates.entering_gmp)
async def calc_gmp(message: Message, state: FSMContext):
    if message.text == "❌ Отменить заказ":
        await state.clear()
        await message.answer("❌ Заказ отменён", reply_markup=main_keyboard())
        return
    try:
        gmp = float(message.text.replace(",", "."))
        if gmp < MIN_GMP_ORDER:
            await message.answer(f"❌ Минимальный заказ: {MIN_GMP_ORDER} GMP")
            return
        gmp_rate = float(get_setting('gmp_rate'))
        star_rate = float(get_setting('star_rate'))
        rub = round(gmp * gmp_rate, 2)
        stars = round(rub / star_rate, 0)
        await state.update_data(gmp_amount=gmp, price_rub=rub, price_stars=stars)
        await message.answer(
            f"📊 РАСЧЁТ:\n\n"
            f"💎 GMP: {gmp}\n"
            f"💵 Рубли: {rub} ₽\n"
            f"⭐ Звёзды: {int(stars)} ⭐\n\n"
            f"Выбери способ оплаты:",
            reply_markup=payment_keyboard()
        )
        await state.set_state(OrderStates.choosing_payment)
    except ValueError:
        await message.answer("❌ Введи число!")

@dp.message(OrderStates.choosing_payment, F.text == "💳 Рубли")
async def pay_rub(message: Message, state: FSMContext):
    data = await state.get_data()
    req = get_setting('requisites')
    order_id = create_order(data['gmp_amount'], data['price_rub'], data['price_stars'], 'rub')
    await state.update_data(order_id=order_id)
    await message.answer(
        f"💳 ЗАКАЗ #{order_id}\n\n"
        f"📌 Сумма: {data['price_rub']} ₽\n"
        f"💎 Получите: {data['gmp_amount']} GMP\n\n"
        f"💰 Реквизиты:\n{req}\n\n"
        f"📸 После оплаты отправь скриншот сюда:",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(OrderStates.waiting_screenshot)

@dp.message(OrderStates.choosing_payment, F.text == "⭐ Звёзды")
async def pay_stars(message: Message, state: FSMContext):
    data = await state.get_data()
    stars = int(data['price_stars'])
    if stars < MIN_STAR_ORDER:
        stars = MIN_STAR_ORDER
    order_id = create_order(data['gmp_amount'], data['price_rub'], stars, 'stars')
    await state.update_data(order_id=order_id)
    await message.answer(
        f"⭐ ЗАКАЗ #{order_id}\n\n"
        f"📌 Отправь {stars} ⭐ подарком на {SUPPORT_USERNAME}\n"
        f"💎 Получите: {data['gmp_amount']} GMP\n\n"
        f"📸 После отправки пришли скриншот:",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(OrderStates.waiting_screenshot)

@dp.message(OrderStates.waiting_screenshot, F.photo)
async def receive_screenshot(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data['order_id']
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE orders SET screenshot_id = ? WHERE order_id = ?',
                   (message.photo[-1].file_id, order_id))
    conn.commit()
    conn.close()
    await message.answer("✅ Скриншот получен! Ожидайте подтверждения администратора.", reply_markup=main_keyboard())
    # Уведомить админа
    try:
        await bot.send_message(ADMIN_ID,
            f"📸 Новый скрин по заказу #{order_id} от @{message.from_user.username or message.from_user.id}")
    except:
        pass
    await state.clear()

@dp.message(OrderStates.waiting_screenshot, F.text == "❌ Отменить заказ")
async def cancel_screenshot(message: Message, state: FSMContext):
    data = await state.get_data()
    if 'order_id' in data:
        update_order_status(data['order_id'], 'cancelled', 'Отменено пользователем')
    await message.answer("❌ Заказ отменён", reply_markup=main_keyboard())
    await state.clear()

# Калькулятор: ввод рублей
@dp.message(F.text == "💵 Посчитать в рублях")
async def calc_rub_start(message: Message):
    await message.answer("Введи сумму в рублях:", reply_markup=cancel_keyboard())
    await state.set_state(OrderStates.entering_rub)

@dp.message(OrderStates.entering_rub)
async def calc_rub_result(message: Message, state: FSMContext):
    if message.text == "❌ Отменить заказ":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_keyboard())
        return
    try:
        rub = float(message.text.replace(",", "."))
        gmp_rate = float(get_setting('gmp_rate'))
        star_rate = float(get_setting('star_rate'))
        gmp = round(rub / gmp_rate, 2)
        stars = round(rub / star_rate, 0)
        await message.answer(
            f"📊 РАСЧЁТ:\n💵 {rub} ₽ = 💎 {gmp} GMP = ⭐ {int(stars)} звёзд\n\n"
            f"Минимальный заказ: {MIN_GMP_ORDER} GMP",
            reply_markup=main_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Введи число!")

# Калькулятор: ввод звёзд
@dp.message(F.text == "⭐ Посчитать в звёздах")
async def calc_stars_start(message: Message):
    await message.answer("Введи количество звёзд:", reply_markup=cancel_keyboard())
    await state.set_state(OrderStates.entering_stars)

@dp.message(OrderStates.entering_stars)
async def calc_stars_result(message: Message, state: FSMContext):
    if message.text == "❌ Отменить заказ":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_keyboard())
        return
    try:
        stars = int(message.text)
        star_rate = float(get_setting('star_rate'))
        gmp_rate = float(get_setting('gmp_rate'))
        rub = stars * star_rate
        gmp = round(rub / gmp_rate, 2)
        await message.answer(
            f"📊 РАСЧЁТ:\n⭐ {stars} звёзд = 💵 {rub} ₽ = 💎 {gmp} GMP\n\n"
            f"Минимальный заказ: {MIN_STAR_ORDER} ⭐",
            reply_markup=main_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Введи целое число!")

# Остальные кнопки меню
@dp.message(F.text == "📢 Канал")
async def channel(message: Message):
    await message.answer(f"📢 Наш канал: https://t.me/{CHANNEL_USERNAME.replace('@', '')}")

@dp.message(F.text == "👤 Поддержка")
async def support(message: Message):
    await message.answer(f"👤 Поддержка: {SUPPORT_USERNAME}")

@dp.message(F.text == "⭐ Отзывы")
async def reviews(message: Message):
    await message.answer(f"⭐ Отзывы: https://t.me/{REVIEWS_USERNAME.replace('@', '')}")

@dp.message(F.text == "👤 Мой профиль")
async def my_profile(message: Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Профиль не найден, нажми /start")
        return
    orders = get_orders(message.from_user.id)
    total_orders = len(orders)
    text = (
        f"👤 МОЙ ПРОФИЛЬ\n\n"
        f"ID: {user[0]}\n"
        f"Имя: #{user[2] or user[1]}\n"
        f"Юзернейм: @{user[1] if user[1] else 'нет'}\n"
        f"Регистрация: {user[3]}\n\n"
        f"СТАТИСТИКА ПОКУПОК\n"
        f"Всего заказов: {total_orders}\n"
        f"Получено GMP: {user[5]}\n"
        f"Лотерейных билетов: {user[6]}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎟 Активировать промокод", callback_data="activate_promo")],
        [InlineKeyboardButton(text="📋 Все мои заказы", callback_data="my_orders")]
    ])
    await message.answer(text, reply_markup=kb)

@dp.callback_query(F.data == "activate_promo")
async def activate_promo_prompt(callback: CallbackQuery):
    await callback.message.answer("🎟 Введи промокод:")
    await callback.answer()

@dp.callback_query(F.data == "my_orders")
async def my_orders_list(callback: CallbackQuery):
    orders = get_orders(callback.from_user.id)
    if not orders:
        await callback.answer("Нет заказов")
        return
    for o in orders:
        await callback.message.answer(
            f"📦 Заказ #{o[0]}\n💎 {o[2]} GMP | 💵 {o[3]} ₽\n📌 {o[6]} | 📅 {o[9]}"
        )
    await callback.answer()

@dp.message(F.text == "💬 Бонусы")
async def bonuses(message: Message):
    text = (
        "🎁 БОНУСНАЯ ПРОГРАММА\n\n"
        "Хочешь получить дополнительный бонус к заказу?\n\n"
        "✨ Как получить бонус:\n"
        "1. Зайди в настройки своего профиля Telegram\n"
        "2. В разделе «О себе» (Bio) напиши эту фразу (нажми чтобы скопировать):\n"
        f"💎 {BOT_USERNAME} — Лучший выбор для депа! 💎\n"
        "3. Сделай заказ через бота\n"
        "4. Мы автоматически проверим твой профиль и начислим бонус!\n\n"
        f"💰 Размер бонуса: {BONUS_PERCENT}% от GMP\n\n"
        "✅ Бонус начисляется автоматически при проверке заказа!\n\n"
        "⚡️ Акция действует постоянно"
    )
    await message.answer(text)

@dp.message(F.text == "📋 Лотерея")
async def lottery(message: Message):
    await message.answer("🎰 Лотерея скоро появится! Следите за обновлениями.")

@dp.message(F.text == "🔙 Назад")
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("👤 Главное меню:", reply_markup=main_keyboard())

@dp.message(F.text == "🔙 Назад в админку")
async def back_to_admin(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 Админ-панель:", reply_markup=admin_keyboard())

# Скрытая команда для админа
@dp.message(F.text == "👑 Админ")
async def secret_admin(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 Админ-панель:", reply_markup=admin_keyboard())

# ========== ЗАПУСК ==========
async def main():
    init_db()
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
