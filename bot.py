import sqlite3
import asyncio
import logging
from datetime import datetime, timedelta
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
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from contextlib import suppress

# ========== ЛОГИРОВАНИЕ ==========
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========== КОНФИГ ==========
BOT_TOKEN = "8675588098:AAG4lZtET6JxWLjgP5Octf6Woy9vvUE2uXo"
ADMIN_ID = 8478884644
BOT_USERNAME = "@debashev_GMP_SHOPbot"
SUPPORT_USERNAME = "@debashev"
REVIEWS_USERNAME = "@ot3blBbl_debashev"
CHANNEL_USERNAME = "DEBASHEV_CHANELL"
TINKOFF_URL = "https://www.tinkoff.ru/rm/r_khTqQgynqD.KQfbjzvqGn/M54Ps5735"

DEFAULT_GMP_RATE = 0.3
DEFAULT_STAR_RATE = 2.0
MIN_GMP_ORDER = 50
MIN_STAR_ORDER = 15
BONUS_PERCENT = 3
REF_BONUS_GMP = 1

# ========== ПРЕМИУМ-ЭМОДЗИ (34 шт) ==========
E = {
    'money':    '<tg-emoji emoji-id="5409048419211682843">💰</tg-emoji>',
    'stats':    '<tg-emoji emoji-id="5231200819986047254">📊</tg-emoji>',
    'diamond':  '<tg-emoji emoji-id="6037083366438737901">💎</tg-emoji>',
    'back':     '<tg-emoji emoji-id="5960671702059848143">🔙</tg-emoji>',
    'sparkle':  '<tg-emoji emoji-id="5424972470023104089">✨</tg-emoji>',
    'ref':      '<tg-emoji emoji-id="5454068128969417666">🔗</tg-emoji>',
    'card':     '<tg-emoji emoji-id="5454134258580877567">💳</tg-emoji>',
    'bell':     '<tg-emoji emoji-id="5458603043203327669">🔔</tg-emoji>',
    'gallery':  '<tg-emoji emoji-id="6030466823290360017">🖼</tg-emoji>',
    'loading':  '<tg-emoji emoji-id="5296562641613897196">⏳</tg-emoji>',
    'cancel':   '<tg-emoji emoji-id="5298742255912235479">❌</tg-emoji>',
    'bank':     '<tg-emoji emoji-id="5303310305818855597">🏦</tg-emoji>',
    'free':     '<tg-emoji emoji-id="5406756500108501710">🆓</tg-emoji>',
    'star':     '<tg-emoji emoji-id="5310224206732996002">⭐</tg-emoji>',
    'profile':  '<tg-emoji emoji-id="5298545073963679624">👤</tg-emoji>',
    'chat':     '<tg-emoji emoji-id="5253742260054409879">💬</tg-emoji>',
    'ban':      '<tg-emoji emoji-id="5240241223632954241">🚫</tg-emoji>',
    'box':      '<tg-emoji emoji-id="5208610193952248503">📦</tg-emoji>',
    'approve':  '<tg-emoji emoji-id="5465542769755826716">✅</tg-emoji>',
    'rocket':   '<tg-emoji emoji-id="5312548789062483252">🚀</tg-emoji>',
    'jackpot':  '<tg-emoji emoji-id="5915833712368424979">🎰</tg-emoji>',
    'ticket':   '<tg-emoji emoji-id="5211209302001355411">🎫</tg-emoji>',
    'write':    '<tg-emoji emoji-id="5458382591121964689">✍️</tg-emoji>',
    'pin':      '<tg-emoji emoji-id="5397782960512444700">📌</tg-emoji>',
    'calendar': '<tg-emoji emoji-id="5413879192267805083">📅</tg-emoji>',
    'numbers':  '<tg-emoji emoji-id="5467459132623691529">🔢</tg-emoji>',
    'lightning':'<tg-emoji emoji-id="5219943216781995020">⚡</tg-emoji>',
    'warning':  '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji>',
    'home':     '<tg-emoji emoji-id="6042137469204303531">🏠</tg-emoji>',
    'download': '<tg-emoji emoji-id="6032745346390560408">📥</tg-emoji>',
    'gift':     '<tg-emoji emoji-id="5235511932064129087">🎁</tg-emoji>',
    'cart':     '<tg-emoji emoji-id="5902206159095339799">🛒</tg-emoji>',
    'megaphone':'<tg-emoji emoji-id="5424818078833715060">📢</tg-emoji>',
    'admin':    '<tg-emoji emoji-id="5341715473882955310">👑</tg-emoji>',
}

# ========== БАЗА ДАННЫХ ==========
DB_NAME = "bot_database.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
        registered_at TEXT, last_active TEXT, banned INTEGER DEFAULT 0,
        total_gmp_received REAL DEFAULT 0, total_orders INTEGER DEFAULT 0,
        total_spent_rub REAL DEFAULT 0, total_spent_stars INTEGER DEFAULT 0,
        bonus_tickets INTEGER DEFAULT 0, ref_gmp REAL DEFAULT 0,
        ref_count INTEGER DEFAULT 0, referred_by INTEGER)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        username TEXT, gmp_amount REAL, price_rub REAL,
        price_stars INTEGER, payment_method TEXT,
        status TEXT DEFAULT 'pending', screenshot_id TEXT,
        admin_comment TEXT, bonus_applied REAL DEFAULT 0,
        created_at TEXT, updated_at TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS promo_codes (
        code TEXT PRIMARY KEY, bonus_percent INTEGER,
        max_uses INTEGER, used_count INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1, created_at TEXT, expires_at TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS promo_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        code TEXT, used_at TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS support_tickets (
        ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        username TEXT, message TEXT, admin_reply TEXT,
        status TEXT DEFAULT 'open', created_at TEXT, replied_at TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT)''')

    defaults = [
        ('gmp_rate', str(DEFAULT_GMP_RATE)),
        ('star_rate', str(DEFAULT_STAR_RATE)),
        ('requisites', f'Оплата по ссылке:\n{TINKOFF_URL}'),
        ('maintenance_mode', '0'),
    ]
    for key, value in defaults:
        cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, value))

    conn.commit()
    conn.close()
    logger.info("✅ База данных инициализирована")

# ========== ФУНКЦИИ БД ==========
def get_setting(key):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT value FROM settings WHERE key=?', (key,))
    row = c.fetchone()
    conn.close()
    return row['value'] if row else None

def set_setting(key, value):
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, value))
    conn.commit()
    conn.close()

def register_user(user_id, username, first_name, ref=None):
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('''INSERT OR IGNORE INTO users (user_id, username, first_name, registered_at, last_active, referred_by)
                 VALUES (?,?,?,?,?,?)''', (user_id, username, first_name, now, now, ref))
    c.execute('UPDATE users SET last_active=?, username=?, first_name=? WHERE user_id=?',
              (now, username, first_name, user_id))
    if ref and ref != user_id:
        c.execute('SELECT ref_count FROM users WHERE user_id=?', (ref,))
        row = c.fetchone()
        if row:
            c.execute('''UPDATE users SET ref_count=ref_count+1, ref_gmp=ref_gmp+?,
                         bonus_tickets=bonus_tickets+? WHERE user_id=?''',
                      (REF_BONUS_GMP, REF_BONUS_GMP, ref))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def is_banned(user_id):
    u = get_user(user_id)
    return u and u['banned'] == 1

def create_order(user_id, username, gmp, rub, stars, method):
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('''INSERT INTO orders (user_id, username, gmp_amount, price_rub, price_stars, payment_method, created_at, updated_at)
                 VALUES (?,?,?,?,?,?,?,?)''', (user_id, username, gmp, rub, stars, method, now, now))
    oid = c.lastrowid
    conn.commit()
    conn.close()
    return oid

def update_order(order_id, status, comment='', bonus=0):
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('UPDATE orders SET status=?, admin_comment=?, updated_at=?, bonus_applied=? WHERE order_id=?',
              (status, comment, now, bonus, order_id))
    if status == 'completed':
        c.execute('SELECT user_id, gmp_amount, price_rub, price_stars FROM orders WHERE order_id=?', (order_id,))
        o = c.fetchone()
        if o:
            c.execute('''UPDATE users SET total_gmp_received=total_gmp_received+?, total_orders=total_orders+1,
                         total_spent_rub=total_spent_rub+?, total_spent_stars=total_spent_stars+?
                         WHERE user_id=?''',
                      (o['gmp_amount'], o['price_rub'] or 0, o['price_stars'] or 0, o['user_id']))
    conn.commit()
    conn.close()

def get_stats():
    conn = get_db()
    c = conn.cursor()
    s = {}
    c.execute('SELECT COUNT(*) as c FROM users')
    s['users'] = c.fetchone()['c']
    c.execute('SELECT COUNT(*) as c FROM users WHERE banned=1')
    s['banned'] = c.fetchone()['c']
    c.execute("SELECT COUNT(*) as c FROM orders WHERE status='pending'")
    s['pending'] = c.fetchone()['c']
    c.execute("SELECT COUNT(*) as c FROM orders WHERE status='completed'")
    s['completed'] = c.fetchone()['c']
    c.execute("SELECT COUNT(*) as c FROM orders WHERE status='cancelled'")
    s['cancelled'] = c.fetchone()['c']
    c.execute("SELECT COALESCE(SUM(gmp_amount),0) as s FROM orders WHERE status='completed'")
    s['gmp'] = c.fetchone()['s']
    c.execute('SELECT COALESCE(SUM(bonus_tickets),0) as s FROM users')
    s['bonuses'] = c.fetchone()['s']
    c.execute("SELECT COALESCE(SUM(price_rub),0) as s FROM orders WHERE status='completed'")
    s['rub'] = c.fetchone()['s']
    c.execute("SELECT COALESCE(SUM(price_stars),0) as s FROM orders WHERE status='completed'")
    s['stars'] = c.fetchone()['s'] or 0
    c.execute('SELECT COUNT(*) as c FROM orders')
    s['total_orders'] = c.fetchone()['c']
    c.execute("SELECT COUNT(*) as c FROM support_tickets WHERE status='open'")
    s['tickets'] = c.fetchone()['c']
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute("SELECT COUNT(*) as c FROM users WHERE date(registered_at)=?", (today,))
    s['today'] = c.fetchone()['c']
    conn.close()
    return s

def create_ticket(user_id, username, message):
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('INSERT INTO support_tickets (user_id, username, message, created_at) VALUES (?,?,?,?)',
              (user_id, username, message, now))
    tid = c.lastrowid
    conn.commit()
    conn.close()
    return tid

def get_open_tickets():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM support_tickets WHERE status='open' ORDER BY ticket_id DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def reply_ticket(ticket_id, reply):
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("UPDATE support_tickets SET admin_reply=?, status='closed', replied_at=? WHERE ticket_id=?",
              (reply, now, ticket_id))
    conn.commit()
    conn.close()

def create_promo(code, bonus_percent, max_uses):
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    exp = (datetime.now() + timedelta(hours=72)).strftime('%Y-%m-%d %H:%M:%S')
    c.execute('INSERT OR IGNORE INTO promo_codes (code, bonus_percent, max_uses, created_at, expires_at) VALUES (?,?,?,?,?)',
              (code.upper(), bonus_percent, max_uses, now, exp))
    conn.commit()
    conn.close()

def check_promo(code, user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM promo_codes WHERE code=? AND is_active=1', (code.upper(),))
    promo = c.fetchone()
    if not promo:
        conn.close()
        return None, "Промокод не найден"
    promo = dict(promo)
    if promo['used_count'] >= promo['max_uses']:
        conn.close()
        return None, "Промокод исчерпан"
    if promo['expires_at'] and datetime.strptime(promo['expires_at'], '%Y-%m-%d %H:%M:%S') < datetime.now():
        conn.close()
        return None, "Промокод истёк"
    c.execute('SELECT * FROM promo_usage WHERE user_id=? AND code=?', (user_id, code.upper()))
    if c.fetchone():
        conn.close()
        return None, "Вы уже использовали этот промокод"
    c.execute('UPDATE promo_codes SET used_count=used_count+1 WHERE code=?', (code.upper(),))
    c.execute('INSERT INTO promo_usage (user_id, code, used_at) VALUES (?,?,?)',
              (user_id, code.upper(), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    return promo, None

def ban_user_db(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET banned=1 WHERE user_id=?', (user_id,))
    conn.commit()
    conn.close()

def unban_user_db(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET banned=0 WHERE user_id=?', (user_id,))
    conn.commit()
    conn.close()

# ========== СОСТОЯНИЯ FSM ==========
class OrderStates(StatesGroup):
    entering_gmp = State()
    entering_rub = State()
    entering_stars = State()
    choosing_payment = State()
    waiting_screenshot = State()
    entering_promo = State()

class SupportStates(StatesGroup):
    waiting_message = State()

class AdminStates(StatesGroup):
    waiting_rate_gmp = State()
    waiting_rate_star = State()
    waiting_requisites = State()
    waiting_promo_code = State()
    waiting_promo_percent = State()
    waiting_promo_uses = State()
    waiting_broadcast = State()
    waiting_reply_text = State()
    waiting_search = State()
    waiting_ban_id = State()

# ========== БОТ ==========
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ========== КЛАВИАТУРЫ ==========
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{E['cart']} Купить GMP", callback_data="buy_gmp")],
        [InlineKeyboardButton(text=f"{E['profile']} Мой профиль", callback_data="profile"),
         InlineKeyboardButton(text=f"{E['ref']} Рефералы", callback_data="referral")],
        [InlineKeyboardButton(text=f"{E['chat']} Поддержка", callback_data="support"),
         InlineKeyboardButton(text=f"{E['megaphone']} Канал", url=f"https://t.me/{CHANNEL_USERNAME}")],
        [InlineKeyboardButton(text=f"{E['star']} Отзывы", url=f"https://t.me/{REVIEWS_USERNAME.replace('@','')}"),
         InlineKeyboardButton(text=f"{E['gift']} Бонусы", callback_data="bonuses")],
        [InlineKeyboardButton(text=f"{E['jackpot']} Лотерея", callback_data="lottery")],
    ])

def payment_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{E['bank']} Рубли (Тинькофф)", callback_data="pay_rub")],
        [InlineKeyboardButton(text=f"{E['star']} Звёзды (Подарок)", callback_data="pay_stars")],
        [InlineKeyboardButton(text=f"{E['cancel']} Отменить", callback_data="cancel_order")],
    ])

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{E['stats']} Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text=f"{E['box']} Заказы", callback_data="admin_orders"),
         InlineKeyboardButton(text=f"{E['chat']} Тикеты", callback_data="admin_tickets")],
        [InlineKeyboardButton(text=f"{E['money']} Курс", callback_data="admin_rate"),
         InlineKeyboardButton(text=f"{E['card']} Реквизиты", callback_data="admin_req")],
        [InlineKeyboardButton(text=f"{E['ticket']} Промокод", callback_data="admin_promo"),
         InlineKeyboardButton(text=f"{E['bell']} Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text=f"{E['download']} База данных", callback_data="admin_db"),
         InlineKeyboardButton(text=f"{E['ban']} Бан", callback_data="admin_ban")],
        [InlineKeyboardButton(text=f"🔍 Поиск", callback_data="admin_search")],
        [InlineKeyboardButton(text=f"{E['back']} Выйти", callback_data="admin_exit")],
    ])

def cancel_inline():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{E['cancel']} Отмена", callback_data="cancel_order")]
    ])

# ========== /start ==========
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user = message.from_user
    ref = None
    args = message.text.split()
    if len(args) > 1 and args[1].startswith('ref_'):
        try:
            ref = int(args[1].replace('ref_', ''))
        except:
            pass

    register_user(user.id, user.username, user.first_name, ref)

    if is_banned(user.id):
        await message.answer(f"{E['ban']} <b>Вы заблокированы в этом боте.</b>")
        return

    await message.answer(
        f"{E['sparkle']} <b>Здравствуй, #{user.username or user.first_name}!</b> {E['sparkle']}\n\n"
        f"{E['diamond']} Ты попал в бота-продавца <b>GMP</b>.\n"
        f"{E['rocket']} Здесь ты можешь быстро приобрести GMP по самому выгодному курсу!\n\n"
        f"{E['lightning']} <b>Наши преимущества:</b>\n"
        f"• Мгновенная выдача\n"
        f"• Бонусы за профиль\n"
        f"• Удобные способы оплаты\n"
        f"• Лотерея с призами\n\n"
        f"{E['home']} Выбери что тебя интересует:",
        reply_markup=main_menu()
    )

# ========== ГЛАВНОЕ МЕНЮ ==========
@dp.callback_query(F.data == "buy_gmp")
async def cb_buy_gmp(callback: CallbackQuery, state: FSMContext):
    if is_banned(callback.from_user.id):
        await callback.answer("🚫 Вы заблокированы.", show_alert=True)
        return
    gmp_r = float(get_setting('gmp_rate'))
    star_r = float(get_setting('star_rate'))
    await callback.message.edit_text(
        f"{E['cart']} <b>КАЛЬКУЛЯТОР GMP</b>\n\n"
        f"{E['pin']} Курс: 1 GMP = {gmp_r} ₽\n"
        f"{E['star']} Звёзды: 1 ⭐ = {star_r} ₽\n\n"
        f"{E['numbers']} Мин. заказ: <b>{MIN_GMP_ORDER} GMP</b>\n"
        f"{E['star']} Мин. звёздами: <b>{MIN_STAR_ORDER} ⭐</b>\n\n"
        f"{E['write']} Введи сумму GMP <b>в чат</b> (числом):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{E['money']} Ввести в рублях", callback_data="calc_rub")],
            [InlineKeyboardButton(text=f"{E['star']} Ввести в звёздах", callback_data="calc_stars")],
            [InlineKeyboardButton(text=f"{E['cancel']} Отмена", callback_data="cancel_order")],
        ])
    )
    await state.set_state(OrderStates.entering_gmp)
    await callback.answer()

@dp.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery):
    if is_banned(callback.from_user.id):
        await callback.answer("🚫 Вы заблокированы.", show_alert=True)
        return
    u = get_user(callback.from_user.id)
    if not u:
        await callback.answer("Профиль не найден. Нажми /start")
        return
    text = (
        f"{E['profile']} <b>МОЙ ПРОФИЛЬ</b>\n\n"
        f"ID: <code>{u['user_id']}</code>\n"
        f"Имя: #{u['first_name'] or u['username']}\n"
        f"Юзернейм: @{u['username'] if u['username'] else 'нет'}\n"
        f"{E['calendar']} Регистрация: {u['registered_at']}\n\n"
        f"<b>СТАТИСТИКА ПОКУПОК</b>\n"
        f"{E['box']} Заказов: <b>{u['total_orders']}</b>\n"
        f"{E['diamond']} Получено GMP: <b>{u['total_gmp_received']}</b>\n"
        f"{E['money']} Потрачено ₽: <b>{u['total_spent_rub']}</b>\n"
        f"{E['star']} Потрачено ⭐: <b>{u['total_spent_stars']}</b>\n"
        f"{E['ref']} Рефералов: <b>{u['ref_count']}</b> (+{u['ref_gmp']} GMP)\n"
        f"{E['ticket']} Билетов: <b>{u['bonus_tickets']}</b>"
    )
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{E['ticket']} Активировать промокод", callback_data="enter_promo")],
        [InlineKeyboardButton(text=f"{E['back']} Назад", callback_data="back_menu")]
    ]))
    await callback.answer()

@dp.callback_query(F.data == "enter_promo")
async def cb_enter_promo(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        f"{E['ticket']} Введи промокод в чат:",
        reply_markup=cancel_inline()
    )
    await state.set_state(OrderStates.entering_promo)
    await callback.answer()

@dp.message(OrderStates.entering_promo)
async def process_promo(message: Message, state: FSMContext):
    promo, err = check_promo(message.text.strip(), message.from_user.id)
    if err:
        await message.answer(f"{E['cancel']} {err}")
    else:
        await message.answer(
            f"{E['approve']} <b>Промокод активирован!</b>\n"
            f"{E['gift']} Бонус: <b>+{promo['bonus_percent']}%</b> к следующему заказу!"
        )
    await state.clear()

@dp.callback_query(F.data == "referral")
async def cb_referral(callback: CallbackQuery):
    if is_banned(callback.from_user.id):
        await callback.answer("🚫 Вы заблокированы.", show_alert=True)
        return
    link = f"https://t.me/{BOT_USERNAME.replace('@','')}?start=ref_{callback.from_user.id}"
    u = get_user(callback.from_user.id)
    text = (
        f"{E['ref']} <b>РЕФЕРАЛЬНАЯ СИСТЕМА</b>\n\n"
        f"Приглашай друзей и получай <b>{REF_BONUS_GMP} GMP</b> за каждого!\n\n"
        f"🔗 Твоя ссылка:\n<code>{link}</code>\n\n"
        f"{E['profile']} Приглашено: <b>{u['ref_count']}</b>\n"
        f"{E['diamond']} Заработано: <b>{u['ref_gmp']} GMP</b>\n\n"
        f"{E['warning']} Вывод GMP возможен только после первого депозита."
    )
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{E['back']} Назад", callback_data="back_menu")]
    ]))
    await callback.answer()

@dp.callback_query(F.data == "support")
async def cb_support(callback: CallbackQuery, state: FSMContext):
    if is_banned(callback.from_user.id):
        await callback.answer("🚫 Вы заблокированы.", show_alert=True)
        return
    await callback.message.edit_text(
        f"{E['chat']} <b>ПОДДЕРЖКА</b>\n\n"
        f"{E['write']} Опишите ваш вопрос, и мы ответим в течение <b>24 часов</b>.\n"
        f"Просто напишите сообщение в чат:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{E['cancel']} Отмена", callback_data="back_menu")]
        ])
    )
    await state.set_state(SupportStates.waiting_message)
    await callback.answer()

@dp.message(SupportStates.waiting_message)
async def receive_support_message(message: Message, state: FSMContext):
    if message.text and message.text.startswith('/'):
        await state.clear()
        return
    tid = create_ticket(message.from_user.id, message.from_user.username or str(message.from_user.id), message.text)
    await message.answer(
        f"{E['chat']} <b>Сообщение #{tid} отправлено!</b>\n"
        f"{E['loading']} Ожидайте ответа в течение 24 часов.",
        reply_markup=main_menu()
    )
    with suppress(Exception):
        await bot.send_message(
            ADMIN_ID,
            f"{E['chat']} <b>Новый тикет #{tid}</b>\n"
            f"{E['profile']} От: @{message.from_user.username or message.from_user.id}\n"
            f"{E['write']} Текст: {message.text[:300]}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{E['write']} Ответить", callback_data=f"reply_ticket_{tid}")]
            ])
        )
    await state.clear()

@dp.callback_query(F.data == "bonuses")
async def cb_bonuses(callback: CallbackQuery):
    text = (
        f"{E['gift']} <b>БОНУСНАЯ ПРОГРАММА</b>\n\n"
        f"Хочешь получить дополнительный бонус к заказу?\n\n"
        f"{E['sparkle']} <b>Как получить бонус:</b>\n"
        f"1. Зайди в настройки своего профиля Telegram\n"
        f"2. В разделе «О себе» (Bio) напиши эту фразу:\n"
        f"<code>{E['diamond']} {BOT_USERNAME} — Лучший выбор для депа! {E['diamond']}</code>\n"
        f"3. Сделай заказ через бота\n"
        f"4. Мы автоматически проверим твой профиль и начислим бонус!\n\n"
        f"{E['money']} <b>Размер бонуса:</b> {BONUS_PERCENT}% от GMP\n\n"
        f"{E['approve']} Бонус начисляется автоматически при проверке заказа!\n\n"
        f"{E['lightning']} Акция действует постоянно"
    )
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{E['back']} Назад", callback_data="back_menu")]
    ]))
    await callback.answer()

@dp.callback_query(F.data == "lottery")
async def cb_lottery(callback: CallbackQuery):
    await callback.message.edit_text(
        f"{E['jackpot']} <b>ЛОТЕРЕЯ</b>\n\n"
        f"{E['loading']} Раздел в разработке!\n"
        f"Скоро здесь можно будет выиграть крутые призы.\n\n"
        f"{E['megaphone']} Следите за обновлениями в канале!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{E['back']} Назад", callback_data="back_menu")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "back_menu")
async def cb_back_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        f"{E['home']} <b>Главное меню</b>\nВыбери раздел:",
        reply_markup=main_menu()
    )
    await callback.answer()

# ========== КАЛЬКУЛЯТОР ==========
@dp.message(OrderStates.entering_gmp)
async def process_gmp_input(message: Message, state: FSMContext):
    if message.text and message.text.startswith('/'):
        return
    try:
        gmp = float(message.text.replace(",", "."))
        if gmp < MIN_GMP_ORDER:
            await message.answer(f"{E['cancel']} Минимальный заказ: <b>{MIN_GMP_ORDER} GMP</b>")
            return
        gmp_r = float(get_setting('gmp_rate'))
        star_r = float(get_setting('star_rate'))
        rub = round(gmp * gmp_r, 2)
        stars = max(int(rub / star_r), MIN_STAR_ORDER)
        await state.update_data(gmp_amount=gmp, price_rub=rub, price_stars=stars)
        await message.answer(
            f"{E['diamond']} <b>РАСЧЁТ:</b>\n\n"
            f"💎 GMP: <b>{gmp}</b>\n"
            f"{E['money']} Рубли: <b>{rub} ₽</b>\n"
            f"{E['star']} Звёзды: <b>{stars} ⭐</b>\n\n"
            f"Выбери способ оплаты:",
            reply_markup=payment_menu()
        )
        await state.set_state(OrderStates.choosing_payment)
    except ValueError:
        await message.answer(f"{E['cancel']} Введи число!")

@dp.callback_query(F.data == "calc_rub", OrderStates.entering_gmp)
async def cb_calc_rub(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        f"{E['money']} Введи сумму в рублях:",
        reply_markup=cancel_inline()
    )
    await state.set_state(OrderStates.entering_rub)
    await callback.answer()

@dp.message(OrderStates.entering_rub)
async def process_rub_input(message: Message, state: FSMContext):
    if message.text and message.text.startswith('/'):
        return
    try:
        rub = float(message.text.replace(",", "."))
        gmp_r = float(get_setting('gmp_rate'))
        star_r = float(get_setting('star_rate'))
        gmp = round(rub / gmp_r, 2)
        stars = max(int(rub / star_r), MIN_STAR_ORDER)
        if gmp < MIN_GMP_ORDER:
            await message.answer(f"{E['cancel']} Слишком мало. Минимум: <b>{MIN_GMP_ORDER} GMP</b>")
            return
        await state.update_data(gmp_amount=gmp, price_rub=rub, price_stars=stars)
        await message.answer(
            f"{E['diamond']} <b>РАСЧЁТ:</b>\n\n"
            f"{E['money']} {rub} ₽ = 💎 {gmp} GMP = {E['star']} {stars} ⭐\n\n"
            f"Выбери способ оплаты:",
            reply_markup=payment_menu()
        )
        await state.set_state(OrderStates.choosing_payment)
    except ValueError:
        await message.answer(f"{E['cancel']} Введи число!")

@dp.callback_query(F.data == "calc_stars", OrderStates.entering_gmp)
async def cb_calc_stars(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        f"{E['star']} Введи количество звёзд:",
        reply_markup=cancel_inline()
    )
    await state.set_state(OrderStates.entering_stars)
    await callback.answer()

@dp.message(OrderStates.entering_stars)
async def process_stars_input(message: Message, state: FSMContext):
    if message.text and message.text.startswith('/'):
        return
    try:
        stars = int(message.text)
        if stars < MIN_STAR_ORDER:
            await message.answer(f"{E['cancel']} Минимум: <b>{MIN_STAR_ORDER} ⭐</b>")
            return
        star_r = float(get_setting('star_rate'))
        gmp_r = float(get_setting('gmp_rate'))
        rub = round(stars * star_r, 2)
        gmp = round(rub / gmp_r, 2)
        await state.update_data(gmp_amount=gmp, price_rub=rub, price_stars=stars)
        await message.answer(
            f"{E['diamond']} <b>РАСЧЁТ:</b>\n\n"
            f"{E['star']} {stars} ⭐ = {E['money']} {rub} ₽ = 💎 {gmp} GMP\n\n"
            f"Выбери способ оплаты:",
            reply_markup=payment_menu()
        )
        await state.set_state(OrderStates.choosing_payment)
    except ValueError:
        await message.answer(f"{E['cancel']} Введи целое число!")

# ========== ОПЛАТА ==========
@dp.callback_query(F.data == "pay_rub", OrderStates.choosing_payment)
async def cb_pay_rub(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    oid = create_order(
        callback.from_user.id,
        callback.from_user.username or str(callback.from_user.id),
        data['gmp_amount'], data['price_rub'], data['price_stars'], 'rub'
    )
    await state.update_data(order_id=oid)
    await callback.message.edit_text(
        f"{E['bank']} <b>ЗАКАЗ #{oid}</b>\n\n"
        f"{E['money']} Сумма: <b>{data['price_rub']} ₽</b>\n"
        f"{E['diamond']} Получите: <b>{data['gmp_amount']} GMP</b>\n\n"
        f"{E['gallery']} После оплаты отправьте <b>скриншот</b> в этот чат.\n"
        f"Админ проверит и начислит GMP.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{E['card']} Оплатить картой", url=TINKOFF_URL)],
            [InlineKeyboardButton(text=f"{E['cancel']} Отменить заказ", callback_data="cancel_order")]
        ])
    )
    await state.set_state(OrderStates.waiting_screenshot)
    await callback.answer()

@dp.callback_query(F.data == "pay_stars", OrderStates.choosing_payment)
async def cb_pay_stars(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    stars = max(int(data['price_stars']), MIN_STAR_ORDER)
    oid = create_order(
        callback.from_user.id,
        callback.from_user.username or str(callback.from_user.id),
        data['gmp_amount'], data['price_rub'], stars, 'stars'
    )
    await state.update_data(order_id=oid)
    await callback.message.edit_text(
        f"{E['star']} <b>ЗАКАЗ #{oid}</b>\n\n"
        f"Отправьте <b>{stars} ⭐</b> подарком на {SUPPORT_USERNAME}\n"
        f"{E['diamond']} Получите: <b>{data['gmp_amount']} GMP</b>\n\n"
        f"{E['gallery']} После отправки пришлите <b>скриншот</b> в этот чат.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{E['cancel']} Отменить заказ", callback_data="cancel_order")]
        ])
    )
    await state.set_state(OrderStates.waiting_screenshot)
    await callback.answer()

@dp.message(OrderStates.waiting_screenshot, F.photo)
async def receive_screenshot(message: Message, state: FSMContext):
    data = await state.get_data()
    oid = data.get('order_id')
    if not oid:
        await message.answer(f"{E['cancel']} Ошибка заказа. Начни заново /start")
        await state.clear()
        return

    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE orders SET screenshot_id=? WHERE order_id=?', (message.photo[-1].file_id, oid))
    conn.commit()
    conn.close()

    await message.answer(
        f"{E['gallery']} <b>Скриншот получен!</b>\n"
        f"{E['loading']} Заказ <b>#{oid}</b> ожидает проверки.\n"
        f"Обычно это занимает 5-10 минут.",
        reply_markup=main_menu()
    )

    with suppress(Exception):
        await bot.send_message(
            ADMIN_ID,
            f"{E['bell']} <b>Новый скрин по заказу #{oid}</b>\n"
            f"{E['profile']} От: @{message.from_user.username or message.from_user.id}\n"
            f"{E['money']} Сумма: {data.get('price_rub', '?')} ₽",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{E['approve']} Подтвердить", callback_data=f"approve_{oid}"),
                 InlineKeyboardButton(text=f"{E['cancel']} Отменить", callback_data=f"reject_{oid}")]
            ])
        )
        await bot.send_photo(ADMIN_ID, message.photo[-1].file_id,
                             caption=f"{E['gallery']} Скриншот заказа #{oid}")

    await state.clear()

@dp.message(OrderStates.waiting_screenshot)
async def wait_screenshot_text(message: Message, state: FSMContext):
    if message.text and message.text == f"{E['cancel']} Отменить заказ":
        data = await state.get_data()
        if 'order_id' in data:
            update_order(data['order_id'], 'cancelled', 'Отменён пользователем')
        await state.clear()
        await message.answer(f"{E['cancel']} Заказ отменён.", reply_markup=main_menu())
    else:
        await message.answer(f"{E['gallery']} Пожалуйста, отправьте <b>скриншот</b> (фото).")

@dp.callback_query(F.data == "cancel_order")
async def cb_cancel_order(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if 'order_id' in data:
        update_order(data['order_id'], 'cancelled', 'Отменён пользователем')
    await state.clear()
    await callback.message.edit_text(
        f"{E['cancel']} <b>Заказ отменён.</b>",
        reply_markup=main_menu()
    )
    await callback.answer()

# ========== АДМИН-ПАНЕЛЬ ==========
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer(f"{E['ban']} Нет доступа.")
        return
    await message.answer(
        f"{E['admin']} <b>АДМИН-ПАНЕЛЬ</b>\n"
        f"{E['write']} Выберите действие:",
        reply_markup=admin_menu()
    )

@dp.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    s = get_stats()
    text = (
        f"{E['stats']} <b>СТАТИСТИКА</b>\n\n"
        f"{E['profile']} Пользователей: <b>{s['users']}</b> (+{s['today']} сегодня)\n"
        f"{E['ban']} Забанено: <b>{s['banned']}</b>\n"
        f"{E['loading']} Заказов ожидает: <b>{s['pending']}</b>\n"
        f"{E['approve']} Выполнено: <b>{s['completed']}</b>\n"
        f"{E['cancel']} Отменено: <b>{s['cancelled']}</b>\n"
        f"{E['diamond']} GMP выдано: <b>{s['gmp']}</b>\n"
        f"{E['gift']} Бонусов: <b>{s['bonuses']}</b>\n"
        f"{E['money']} Оборот ₽: <b>{s['rub']:.2f}</b>\n"
        f"{E['star']} Оборот ⭐: <b>{int(s['stars'])}</b>\n"
        f"{E['box']} Заказов всего: <b>{s['total_orders']}</b>\n"
        f"{E['chat']} Открытых тикетов: <b>{s['tickets']}</b>"
    )
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{E['back']} Назад", callback_data="admin_back")]
    ]))
    await callback.answer()

@dp.callback_query(F.data == "admin_orders")
async def cb_admin_orders(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE status='pending' ORDER BY order_id DESC LIMIT 10")
    orders = c.fetchall()
    conn.close()

    if not orders:
        await callback.message.edit_text(
            f"{E['box']} Нет ожидающих заказов.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{E['back']} Назад", callback_data="admin_back")]
            ])
        )
        await callback.answer()
        return

    await callback.message.edit_text(f"{E['loading']} Загружаю заказы...")
    for o in orders:
        o = dict(o)
        text = (
            f"{E['box']} <b>Заказ #{o['order_id']}</b>\n"
            f"{E['profile']} @{o['username']} (ID: <code>{o['user_id']}</code>)\n"
            f"{E['diamond']} {o['gmp_amount']} GMP | {E['money']} {o['price_rub']} ₽ | {E['star']} {o['price_stars']} ⭐\n"
            f"{E['card']} Метод: {o['payment_method']}\n"
            f"{E['calendar']} {o['created_at']}"
        )
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{E['approve']} Подтвердить", callback_data=f"approve_{o['order_id']}"),
             InlineKeyboardButton(text=f"{E['cancel']} Отменить", callback_data=f"reject_{o['order_id']}")]
        ]))
    await callback.answer("✅ Заказы загружены")

@dp.callback_query(F.data.startswith("approve_"))
async def cb_approve(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    oid = int(callback.data.split("_")[1])
    update_order(oid, 'completed', 'Подтверждено')

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT user_id, gmp_amount FROM orders WHERE order_id=?', (oid,))
    o = c.fetchone()
    conn.close()

    if o:
        with suppress(Exception):
            await bot.send_message(
                o['user_id'],
                f"{E['approve']} <b>Заказ #{oid} выполнен!</b>\n"
                f"{E['diamond']} Начислено: <b>{o['gmp_amount']} GMP</b>\n"
                f"Спасибо за покупку! {E['sparkle']}"
            )

    await callback.message.edit_text(callback.message.text + f"\n{E['approve']} <b>Подтверждено</b>")
    await callback.answer("✅ Подтверждено!")

@dp.callback_query(F.data.startswith("reject_"))
async def cb_reject(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    oid = int(callback.data.split("_")[1])
    update_order(oid, 'cancelled', 'Отклонено администратором')

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT user_id FROM orders WHERE order_id=?', (oid,))
    o = c.fetchone()
    conn.close()

    if o:
        with suppress(Exception):
            await bot.send_message(
                o['user_id'],
                f"{E['cancel']} <b>Заказ #{oid} отклонён.</b>\n"
                f"{E['chat']} Обратитесь в поддержку: {SUPPORT_USERNAME}"
            )

    await callback.message.edit_text(callback.message.text + f"\n{E['cancel']} <b>Отклонено</b>")
    await callback.answer("❌ Отклонено!")

@dp.callback_query(F.data == "admin_tickets")
async def cb_admin_tickets(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    tickets = get_open_tickets()
    if not tickets:
        await callback.message.edit_text(
            f"{E['chat']} Нет открытых тикетов.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{E['back']} Назад", callback_data="admin_back")]
            ])
        )
        await callback.answer()
        return

    await callback.message.edit_text(f"{E['loading']} Загружаю тикеты...")
    for t in tickets:
        text = (
            f"{E['chat']} <b>Тикет #{t['ticket_id']}</b>\n"
            f"{E['profile']} @{t['username']} (ID: {t['user_id']})\n"
            f"{E['write']} {t['message'][:300]}\n"
            f"{E['calendar']} {t['created_at']}"
        )
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{E['write']} Ответить", callback_data=f"reply_ticket_{t['ticket_id']}")]
        ]))
    await callback.answer("✅ Тикеты загружены")

@dp.callback_query(F.data.startswith("reply_ticket_"))
async def cb_reply_ticket_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    tid = int(callback.data.split("_")[2])
    await state.update_data(reply_tid=tid)
    await callback.message.edit_text(
        f"{E['write']} Введи ответ на тикет <b>#{tid}</b>:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{E['cancel']} Отмена", callback_data="admin_back")]
        ])
    )
    await state.set_state(AdminStates.waiting_reply_text)
    await callback.answer()

@dp.message(AdminStates.waiting_reply_text)
async def process_reply(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    data = await state.get_data()
    tid = data['reply_tid']
    reply_ticket(tid, message.text)

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT user_id FROM support_tickets WHERE ticket_id=?', (tid,))
    t = c.fetchone()
    conn.close()

    if t:
        with suppress(Exception):
            await bot.send_message(
                t['user_id'],
                f"{E['chat']} <b>Ответ поддержки (тикет #{tid}):</b>\n\n"
                f"{message.text}\n\n"
                f"{E['write']} Если остались вопросы — создайте новый тикет."
            )

    await message.answer(f"{E['approve']} Ответ на тикет <b>#{tid}</b> отправлен.", reply_markup=admin_menu())
    await state.clear()

@dp.callback_query(F.data == "admin_rate")
async def cb_admin_rate(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    gmp_r = get_setting('gmp_rate')
    star_r = get_setting('star_rate')
    await callback.message.edit_text(
        f"{E['money']} <b>Текущие курсы:</b>\n"
        f"{E['diamond']} 1 GMP = <b>{gmp_r} ₽</b>\n"
        f"{E['star']} 1 ⭐ = <b>{star_r} ₽</b>\n\n"
        f"{E['write']} Введи новый курс GMP (в рублях):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{E['back']} Назад", callback_data="admin_back")]
        ])
    )
    await state.set_state(AdminStates.waiting_rate_gmp)
    await callback.answer()

@dp.message(AdminStates.waiting_rate_gmp)
async def set_rate_gmp(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        r = float(message.text.replace(",", "."))
        set_setting('gmp_rate', str(r))
        await message.answer(
            f"{E['approve']} 1 GMP = {r} ₽\n"
            f"{E['write']} Теперь введи курс звёзд (1 ⭐ = X ₽):"
        )
        await state.set_state(AdminStates.waiting_rate_star)
    except ValueError:
        await message.answer(f"{E['cancel']} Введи число!")

@dp.message(AdminStates.waiting_rate_star)
async def set_rate_star(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        r = float(message.text.replace(",", "."))
        set_setting('star_rate', str(r))
        await message.answer(
            f"{E['approve']} 1 ⭐ = {r} ₽\n"
            f"{E['lightning']} Курсы обновлены!",
            reply_markup=admin_menu()
        )
        await state.clear()
    except ValueError:
        await message.answer(f"{E['cancel']} Введи число!")

@dp.callback_query(F.data == "admin_req")
async def cb_admin_req(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    r = get_setting('requisites')
    await callback.message.edit_text(
        f"{E['card']} <b>Текущие реквизиты:</b>\n{r[:500]}\n\n"
        f"{E['write']} Введи новые реквизиты:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{E['back']} Назад", callback_data="admin_back")]
        ])
    )
    await state.set_state(AdminStates.waiting_requisites)
    await callback.answer()

@dp.message(AdminStates.waiting_requisites)
async def set_req(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    set_setting('requisites', message.text)
    await message.answer(f"{E['approve']} Реквизиты обновлены!", reply_markup=admin_menu())
    await state.clear()

@dp.callback_query(F.data == "admin_promo")
async def cb_admin_promo(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    await callback.message.edit_text(
        f"{E['ticket']} <b>СОЗДАНИЕ ПРОМОКОДА</b>\n\n"
        f"{E['write']} Введи код (латиница/цифры):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{E['back']} Назад", callback_data="admin_back")]
        ])
    )
    await state.set_state(AdminStates.waiting_promo_code)
    await callback.answer()

@dp.message(AdminStates.waiting_promo_code)
async def set_promo_code(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    code = message.text.strip().upper()
    await state.update_data(promo_code=code)
    await message.answer(f"{E['write']} Введи процент бонуса (число, например 10):")
    await state.set_state(AdminStates.waiting_promo_percent)

@dp.message(AdminStates.waiting_promo_percent)
async def set_promo_percent(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        percent = int(message.text)
        await state.update_data(promo_percent=percent)
        await message.answer(f"{E['write']} Введи максимальное число использований:")
        await state.set_state(AdminStates.waiting_promo_uses)
    except ValueError:
        await message.answer(f"{E['cancel']} Введи целое число!")

@dp.message(AdminStates.waiting_promo_uses)
async def set_promo_uses(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        uses = int(message.text)
        data = await state.get_data()
        create_promo(data['promo_code'], data['promo_percent'], uses)
        await message.answer(
            f"{E['approve']} <b>Промокод создан!</b>\n"
            f"{E['ticket']} Код: <b>{data['promo_code']}</b>\n"
            f"{E['gift']} Бонус: <b>{data['promo_percent']}%</b>\n"
            f"{E['numbers']} Использований: <b>{uses}</b>\n"
            f"{E['calendar']} Срок: 72 часа",
            reply_markup=admin_menu()
        )
        await state.clear()
    except ValueError:
        await message.answer(f"{E['cancel']} Введи целое число!")

@dp.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    await callback.message.edit_text(
        f"{E['bell']} <b>РАССЫЛКА</b>\n\n"
        f"{E['write']} Введи текст для рассылки:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{E['back']} Назад", callback_data="admin_back")]
        ])
    )
    await state.set_state(AdminStates.waiting_broadcast)
    await callback.answer()

@dp.message(AdminStates.waiting_broadcast)
async def do_broadcast(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT user_id FROM users WHERE banned=0')
    users = c.fetchall()
    conn.close()

    await message.answer(f"{E['loading']} Начинаю рассылку на {len(users)} пользователей...")

    sent = 0
    for u in users:
        with suppress(Exception):
            await bot.send_message(
                u['user_id'],
                f"{E['bell']} <b>Рассылка:</b>\n\n{message.text}"
            )
            sent += 1
            await asyncio.sleep(0.05)

    await message.answer(
        f"{E['approve']} <b>Рассылка завершена!</b>\n"
        f"Отправлено: <b>{sent}</b> / {len(users)}",
        reply_markup=admin_menu()
    )
    await state.clear()

@dp.callback_query(F.data == "admin_db")
async def cb_admin_db(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    try:
        await callback.message.answer_document(
            FSInputFile(DB_NAME),
            caption=f"{E['download']} База данных бота\n{E['calendar']} {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
    except:
        await callback.message.answer(f"{E['cancel']} Файл базы данных не найден.")
    await callback.answer()

@dp.callback_query(F.data == "admin_ban")
async def cb_admin_ban(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    await callback.message.edit_text(
        f"{E['ban']} <b>БАН ПОЛЬЗОВАТЕЛЯ</b>\n\n"
        f"{E['write']} Введи ID пользователя:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{E['back']} Назад", callback_data="admin_back")]
        ])
    )
    await state.set_state(AdminStates.waiting_ban_id)
    await callback.answer()

@dp.message(AdminStates.waiting_ban_id)
async def do_ban(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        uid = int(message.text)
        u = get_user(uid)
        if not u:
            await message.answer(f"{E['cancel']} Пользователь не найден.")
            return
        if u['banned']:
            unban_user_db(uid)
            await message.answer(
                f"{E['approve']} Пользователь <b>{uid}</b> разбанен.",
                reply_markup=admin_menu()
            )
        else:
            ban_user_db(uid)
            await message.answer(
                f"{E['ban']} Пользователь <b>{uid}</b> забанен.",
                reply_markup=admin_menu()
            )
            try:
                await bot.send_message(uid, f"{E['ban']} <b>Вы заблокированы в боте.</b>")
            except:
                pass
        await state.clear()
    except ValueError:
        await message.answer(f"{E['cancel']} Введи корректный ID!")

@dp.callback_query(F.data == "admin_search")
async def cb_admin_search(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    await callback.message.edit_text(
        f"🔍 <b>ПОИСК</b>\n\n"
        f"{E['write']} Введи ID пользователя или номер заказа:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{E['back']} Назад", callback_data="admin_back")]
        ])
    )
    await state.set_state(AdminStates.waiting_search)
    await callback.answer()

@dp.message(AdminStates.waiting_search)
async def do_search(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    query = message.text.strip()
    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT * FROM orders WHERE order_id=?', (query,))
    order = c.fetchone()
    if order:
        order = dict(order)
        await message.answer(
            f"{E['box']} <b>Заказ #{order['order_id']}</b>\n"
            f"{E['profile']} ID: {order['user_id']}\n"
            f"@{order['username']}\n"
            f"{E['diamond']} {order['gmp_amount']} GMP\n"
            f"{E['money']} {order['price_rub']} ₽ | {E['star']} {order['price_stars']} ⭐\n"
            f"{E['card']} Метод: {order['payment_method']}\n"
            f"Статус: {order['status']}\n"
            f"{E['calendar']} {order['created_at']}"
        )
        conn.close()
        await state.clear()
        return

    c.execute('SELECT * FROM orders WHERE user_id=? ORDER BY order_id DESC LIMIT 10', (query,))
    orders = c.fetchall()
    if orders:
        text = f"{E['profile']} <b>Заказы пользователя {query}:</b>\n\n"
        for o in orders:
            o = dict(o)
            text += f"{E['box']} #{o['order_id']} | {E['diamond']} {o['gmp_amount']} GMP | {o['status']} | {o['created_at']}\n"
        await message.answer(text)
    else:
        c.execute("SELECT * FROM support_tickets WHERE user_id=? ORDER BY ticket_id DESC LIMIT 5", (query,))
        tickets = c.fetchall()
        if tickets:
            text = f"{E['chat']} <b>Тикеты пользователя {query}:</b>\n\n"
            for t in tickets:
                t = dict(t)
                text += f"#{t['ticket_id']} | {t['message'][:50]}... | {t['status']}\n"
            await message.answer(text)
        else:
            await message.answer(f"{E['cancel']} Ничего не найдено по запросу: {query}")

    conn.close()
    await state.clear()

@dp.callback_query(F.data == "admin_back")
async def cb_admin_back(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    await state.clear()
    await callback.message.edit_text(
        f"{E['admin']} <b>АДМИН-ПАНЕЛЬ</b>\n{E['write']} Выберите действие:",
        reply_markup=admin_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_exit")
async def cb_admin_exit(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    await callback.message.edit_text(
        f"{E['home']} <b>Главное меню</b>\nВыбери раздел:",
        reply_markup=main_menu()
    )
    await callback.answer()

# ========== ЗАПУСК ==========
async def main():
    init_db()
    logger.info(f"✅ Бот {BOT_USERNAME} запущен!")
    logger.info(f"👑 Админ ID: {ADMIN_ID}")
    logger.info(f"💎 34 премиум-эмодзи загружено")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
