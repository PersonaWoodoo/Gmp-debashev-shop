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
    InlineKeyboardMarkup, InlineKeyboardButton,
    Message, CallbackQuery, FSInputFile, MessageEntity
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

# ========== ПРЕМИУМ-ЭМОДЗИ ==========
EID = {
    'money':    5409048419211682843,
    'stats':    5231200819986047254,
    'diamond':  6037083366438737901,
    'back':     5960671702059848143,
    'sparkle':  5424972470023104089,
    'ref':      5454068128969417666,
    'card':     5454134258580877567,
    'bell':     5458603043203327669,
    'gallery':  6030466823290360017,
    'loading':  5296562641613897196,
    'cancel':   5298742255912235479,
    'bank':     5303310305818855597,
    'free':     5406756500108501710,
    'star':     5310224206732996002,
    'profile':  5298545073963679624,
    'chat':     5253742260054409879,
    'ban':      5240241223632954241,
    'box':      5208610193952248503,
    'approve':  5465542769755826716,
    'rocket':   5312548789062483252,
    'jackpot':  5915833712368424979,
    'ticket':   5211209302001355411,
    'write':    5458382591121964689,
    'pin':      5397782960512444700,
    'calendar': 5413879192267805083,
    'numbers':  5467459132623691529,
    'lightning': 5219943216781995020,
    'warning':  5447644880824181073,
    'home':     6042137469204303531,
    'download': 6032745346390560408,
    'gift':     5235511932064129087,
    'cart':     5902206159095339799,
    'megaphone': 5424818078833715060,
    'admin':    5341715473882955310,
}

EMOJI_CHAR = {
    'money': '💰', 'stats': '📊', 'diamond': '💎', 'back': '🔙',
    'sparkle': '✨', 'ref': '🔗', 'card': '💳', 'bell': '🔔',
    'gallery': '🖼', 'loading': '⏳', 'cancel': '❌', 'bank': '🏦',
    'free': '🆓', 'star': '⭐', 'profile': '👤', 'chat': '💬',
    'ban': '🚫', 'box': '📦', 'approve': '✅', 'rocket': '🚀',
    'jackpot': '🎰', 'ticket': '🎫', 'write': '✍️', 'pin': '📌',
    'calendar': '📅', 'numbers': '🔢', 'lightning': '⚡', 'warning': '⚠️',
    'home': '🏠', 'download': '📥', 'gift': '🎁', 'cart': '🛒',
    'megaphone': '📢', 'admin': '👑'
}

B = EMOJI_CHAR  # для кнопок

def msg(text):
    """
    Преобразует текст с метками {key} в текст с премиум-эмодзи и список entities.
    """
    result = ""
    entities = []
    i = 0
    while i < len(text):
        if text[i] == '{' and '}' in text[i:]:
            end = text.index('}', i)
            key = text[i+1:end]
            if key in EID:
                emoji_char = EMOJI_CHAR.get(key, '')
                entities.append(MessageEntity(
                    type="custom_emoji",
                    offset=len(result),
                    length=len(emoji_char),
                    custom_emoji_id=str(EID[key])
                ))
                result += emoji_char
                i = end + 1
                continue
        result += text[i]
        i += 1
    return result, entities

async def send_msg(target, text, reply_markup=None):
    """Отправляет сообщение с премиум-эмодзи (target: Message, CallbackQuery или chat_id)."""
    text, entities = msg(text)
    kwargs = {'text': text, 'reply_markup': reply_markup}
    if entities:
        kwargs['entities'] = entities

    if isinstance(target, Message):
        await target.answer(**kwargs)
    elif isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(**kwargs)
        except Exception:
            await target.message.answer(**kwargs)
    else:
        await bot.send_message(target, **kwargs)

async def send_html(target, text, reply_markup=None):
    """Отправляет HTML-сообщение без эмодзи."""
    if isinstance(target, Message):
        await target.answer(text, reply_markup=reply_markup)
    elif isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=reply_markup)
        except Exception:
            await target.message.answer(text, reply_markup=reply_markup)
    else:
        await bot.send_message(target, text, reply_markup=reply_markup)

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
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT value FROM settings WHERE key=?', (key,))
    row = c.fetchone(); conn.close()
    return row['value'] if row else None

def set_setting(key, value):
    conn = get_db(); c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, value))
    conn.commit(); conn.close()

def register_user(user_id, username, first_name, ref=None):
    conn = get_db(); c = conn.cursor()
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
    conn.commit(); conn.close()

def get_user(user_id):
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone(); conn.close()
    return dict(row) if row else None

def is_banned(user_id):
    u = get_user(user_id)
    return u and u['banned'] == 1

def create_order(user_id, username, gmp, rub, stars, method):
    conn = get_db(); c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('''INSERT INTO orders (user_id, username, gmp_amount, price_rub, price_stars, payment_method, created_at, updated_at)
                 VALUES (?,?,?,?,?,?,?,?)''', (user_id, username, gmp, rub, stars, method, now, now))
    oid = c.lastrowid; conn.commit(); conn.close()
    return oid

def update_order(order_id, status, comment='', bonus=0):
    conn = get_db(); c = conn.cursor()
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
    conn.commit(); conn.close()

def get_stats():
    conn = get_db(); c = conn.cursor()
    s = {}
    c.execute('SELECT COUNT(*) as c FROM users'); s['users'] = c.fetchone()['c']
    c.execute('SELECT COUNT(*) as c FROM users WHERE banned=1'); s['banned'] = c.fetchone()['c']
    c.execute("SELECT COUNT(*) as c FROM orders WHERE status='pending'"); s['pending'] = c.fetchone()['c']
    c.execute("SELECT COUNT(*) as c FROM orders WHERE status='completed'"); s['completed'] = c.fetchone()['c']
    c.execute("SELECT COUNT(*) as c FROM orders WHERE status='cancelled'"); s['cancelled'] = c.fetchone()['c']
    c.execute("SELECT COALESCE(SUM(gmp_amount),0) as s FROM orders WHERE status='completed'"); s['gmp'] = c.fetchone()['s']
    c.execute('SELECT COALESCE(SUM(bonus_tickets),0) as s FROM users'); s['bonuses'] = c.fetchone()['s']
    c.execute("SELECT COALESCE(SUM(price_rub),0) as s FROM orders WHERE status='completed'"); s['rub'] = c.fetchone()['s']
    c.execute("SELECT COALESCE(SUM(price_stars),0) as s FROM orders WHERE status='completed'"); s['stars'] = c.fetchone()['s'] or 0
    c.execute('SELECT COUNT(*) as c FROM orders'); s['total_orders'] = c.fetchone()['c']
    c.execute("SELECT COUNT(*) as c FROM support_tickets WHERE status='open'"); s['tickets'] = c.fetchone()['c']
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute("SELECT COUNT(*) as c FROM users WHERE date(registered_at)=?", (today,)); s['today'] = c.fetchone()['c']
    conn.close()
    return s

def create_ticket(user_id, username, message):
    conn = get_db(); c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('INSERT INTO support_tickets (user_id, username, message, created_at) VALUES (?,?,?,?)',
              (user_id, username, message, now))
    tid = c.lastrowid; conn.commit(); conn.close()
    return tid

def get_open_tickets():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM support_tickets WHERE status='open' ORDER BY ticket_id DESC LIMIT 20")
    rows = c.fetchall(); conn.close()
    return [dict(r) for r in rows]

def reply_ticket(ticket_id, reply):
    conn = get_db(); c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("UPDATE support_tickets SET admin_reply=?, status='closed', replied_at=? WHERE ticket_id=?",
              (reply, now, ticket_id))
    conn.commit(); conn.close()

def create_promo(code, bonus_percent, max_uses):
    conn = get_db(); c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    exp = (datetime.now() + timedelta(hours=72)).strftime('%Y-%m-%d %H:%M:%S')
    c.execute('INSERT OR IGNORE INTO promo_codes (code, bonus_percent, max_uses, created_at, expires_at) VALUES (?,?,?,?,?)',
              (code.upper(), bonus_percent, max_uses, now, exp))
    conn.commit(); conn.close()

def check_promo(code, user_id):
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT * FROM promo_codes WHERE code=? AND is_active=1', (code.upper(),))
    promo = c.fetchone()
    if not promo: conn.close(); return None, "Промокод не найден"
    promo = dict(promo)
    if promo['used_count'] >= promo['max_uses']: conn.close(); return None, "Промокод исчерпан"
    if promo['expires_at'] and datetime.strptime(promo['expires_at'], '%Y-%m-%d %H:%M:%S') < datetime.now():
        conn.close(); return None, "Промокод истёк"
    c.execute('SELECT * FROM promo_usage WHERE user_id=? AND code=?', (user_id, code.upper()))
    if c.fetchone(): conn.close(); return None, "Вы уже использовали этот промокод"
    c.execute('UPDATE promo_codes SET used_count=used_count+1 WHERE code=?', (code.upper(),))
    c.execute('INSERT INTO promo_usage (user_id, code, used_at) VALUES (?,?,?)',
              (user_id, code.upper(), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit(); conn.close()
    return promo, None

def ban_user_db(user_id):
    conn = get_db(); c = conn.cursor()
    c.execute('UPDATE users SET banned=1 WHERE user_id=?', (user_id,))
    conn.commit(); conn.close()

def unban_user_db(user_id):
    conn = get_db(); c = conn.cursor()
    c.execute('UPDATE users SET banned=0 WHERE user_id=?', (user_id,))
    conn.commit(); conn.close()

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
        [InlineKeyboardButton(text=f"{B['cart']} Купить GMP", callback_data="buy_gmp")],
        [InlineKeyboardButton(text=f"{B['profile']} Мой профиль", callback_data="profile"),
         InlineKeyboardButton(text=f"{B['ref']} Рефералы", callback_data="referral")],
        [InlineKeyboardButton(text=f"{B['chat']} Поддержка", callback_data="support"),
         InlineKeyboardButton(text=f"{B['megaphone']} Канал", url=f"https://t.me/{CHANNEL_USERNAME}")],
        [InlineKeyboardButton(text=f"{B['star']} Отзывы", url=f"https://t.me/{REVIEWS_USERNAME.replace('@','')}"),
         InlineKeyboardButton(text=f"{B['gift']} Бонусы", callback_data="bonuses")],
        [InlineKeyboardButton(text=f"{B['jackpot']} Лотерея", callback_data="lottery")],
    ])

def payment_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{B['bank']} Рубли (Тинькофф)", callback_data="pay_rub")],
        [InlineKeyboardButton(text=f"{B['star']} Звёзды (Подарок)", callback_data="pay_stars")],
        [InlineKeyboardButton(text=f"{B['cancel']} Отменить", callback_data="cancel_order")],
    ])

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{B['stats']} Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text=f"{B['box']} Заказы", callback_data="admin_orders"),
         InlineKeyboardButton(text=f"{B['chat']} Тикеты", callback_data="admin_tickets")],
        [InlineKeyboardButton(text=f"{B['money']} Курс", callback_data="admin_rate"),
         InlineKeyboardButton(text=f"{B['card']} Реквизиты", callback_data="admin_req")],
        [InlineKeyboardButton(text=f"{B['ticket']} Промокод", callback_data="admin_promo"),
         InlineKeyboardButton(text=f"{B['bell']} Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text=f"{B['download']} База данных", callback_data="admin_db"),
         InlineKeyboardButton(text=f"{B['ban']} Бан", callback_data="admin_ban")],
        [InlineKeyboardButton(text=f"🔍 Поиск", callback_data="admin_search")],
        [InlineKeyboardButton(text=f"{B['back']} Выйти", callback_data="admin_exit")],
    ])

def cancel_inline():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{B['cancel']} Отмена", callback_data="cancel_order")]
    ])

# ========== /start ==========
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user = message.from_user
    ref = None
    args = message.text.split()
    if len(args) > 1 and args[1].startswith('ref_'):
        try: ref = int(args[1].replace('ref_', ''))
        except: pass

    register_user(user.id, user.username, user.first_name, ref)

    if is_banned(user.id):
        await send_msg(message, "{ban} <b>Вы заблокированы в этом боте.</b>")
        return

    name = f"#{user.username or user.first_name}"
    await send_msg(message,
        "{sparkle} <b>Здравствуй, " + name + "!</b> {sparkle}\n\n"
        "{diamond} Ты попал в бота-продавца <b>GMP</b>.\n"
        "{rocket} Здесь ты можешь быстро приобрести GMP по самому выгодному курсу!\n\n"
        "{lightning} <b>Наши преимущества:</b>\n"
        "• Мгновенная выдача\n• Бонусы за профиль\n• Удобные способы оплаты\n• Лотерея с призами\n\n"
        "{home} Выбери что тебя интересует:",
        reply_markup=main_menu()
    )

# ========== ГЛАВНОЕ МЕНЮ ==========
@dp.callback_query(F.data == "buy_gmp")
async def cb_buy_gmp(callback: CallbackQuery, state: FSMContext):
    if is_banned(callback.from_user.id): await callback.answer("🚫", show_alert=True); return
    gmp_r = float(get_setting('gmp_rate'))
    star_r = float(get_setting('star_rate'))
    await send_msg(callback,
        f"{{cart}} <b>КАЛЬКУЛЯТОР GMP</b>\n\n{{pin}} Курс: 1 GMP = {gmp_r} ₽\n{{star}} Звёзды: 1 ⭐ = {star_r} ₽\n\n"
        f"{{numbers}} Мин. заказ: <b>{MIN_GMP_ORDER} GMP</b>\n{{star}} Мин. звёздами: <b>{MIN_STAR_ORDER} ⭐</b>\n\n"
        "{write} Введи сумму GMP <b>в чат</b> (числом):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{B['money']} Ввести в рублях", callback_data="calc_rub")],
            [InlineKeyboardButton(text=f"{B['star']} Ввести в звёздах", callback_data="calc_stars")],
            [InlineKeyboardButton(text=f"{B['cancel']} Отмена", callback_data="cancel_order")],
        ])
    )
    await state.set_state(OrderStates.entering_gmp)
    await callback.answer()

@dp.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery):
    if is_banned(callback.from_user.id): await callback.answer("🚫", show_alert=True); return
    u = get_user(callback.from_user.id)
    if not u: await callback.answer("Профиль не найден. Нажми /start"); return
    await send_msg(callback,
        f"{{profile}} <b>МОЙ ПРОФИЛЬ</b>\n\nID: <code>{u['user_id']}</code>\n"
        f"Имя: #{u['first_name'] or u['username']}\n"
        f"Юзернейм: @{u['username'] if u['username'] else 'нет'}\n"
        f"{{calendar}} Регистрация: {u['registered_at']}\n\n<b>СТАТИСТИКА ПОКУПОК</b>\n"
        f"{{box}} Заказов: <b>{u['total_orders']}</b>\n"
        f"{{diamond}} Получено GMP: <b>{u['total_gmp_received']}</b>\n"
        f"{{money}} Потрачено ₽: <b>{u['total_spent_rub']}</b>\n"
        f"{{star}} Потрачено ⭐: <b>{u['total_spent_stars']}</b>\n"
        f"{{ref}} Рефералов: <b>{u['ref_count']}</b> (+{u['ref_gmp']} GMP)\n"
        f"{{ticket}} Билетов: <b>{u['bonus_tickets']}</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{B['ticket']} Активировать промокод", callback_data="enter_promo")],
            [InlineKeyboardButton(text=f"{B['back']} Назад", callback_data="back_menu")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "enter_promo")
async def cb_enter_promo(callback: CallbackQuery, state: FSMContext):
    await send_msg(callback, "{ticket} Введи промокод в чат:", reply_markup=cancel_inline())
    await state.set_state(OrderStates.entering_promo)
    await callback.answer()

@dp.message(OrderStates.entering_promo)
async def process_promo(message: Message, state: FSMContext):
    promo, err = check_promo(message.text.strip(), message.from_user.id)
    if err:
        await send_html(message, f"❌ {err}")
    else:
        await send_msg(message,
            f"{{approve}} <b>Промокод активирован!</b>\n{{gift}} Бонус: <b>+{promo['bonus_percent']}%</b> к следующему заказу!"
        )
    await state.clear()

@dp.callback_query(F.data == "referral")
async def cb_referral(callback: CallbackQuery):
    if is_banned(callback.from_user.id): await callback.answer("🚫", show_alert=True); return
    link = f"https://t.me/{BOT_USERNAME.replace('@','')}?start=ref_{callback.from_user.id}"
    u = get_user(callback.from_user.id)
    await send_msg(callback,
        "{ref} <b>РЕФЕРАЛЬНАЯ СИСТЕМА</b>\n\nПриглашай друзей и получай <b>{ref_bonus} GMP</b> за каждого!\n\n"
        f"🔗 Твоя ссылка:\n<code>{link}</code>\n\n"
        f"{{profile}} Приглашено: <b>{u['ref_count']}</b>\n"
        f"{{diamond}} Заработано: <b>{u['ref_gmp']} GMP</b>\n\n"
        "{warning} Вывод GMP возможен только после первого депозита.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{B['back']} Назад", callback_data="back_menu")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "support")
async def cb_support(callback: CallbackQuery, state: FSMContext):
    if is_banned(callback.from_user.id): await callback.answer("🚫", show_alert=True); return
    await send_msg(callback,
        "{chat} <b>ПОДДЕРЖКА</b>\n\n{write} Опишите ваш вопрос, и мы ответим в течение <b>24 часов</b>.\nПросто напишите сообщение в чат:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{B['cancel']} Отмена", callback_data="back_menu")]
        ])
    )
    await state.set_state(SupportStates.waiting_message)
    await callback.answer()

@dp.message(SupportStates.waiting_message)
async def receive_support_message(message: Message, state: FSMContext):
    if message.text and message.text.startswith('/'): await state.clear(); return
    tid = create_ticket(message.from_user.id, message.from_user.username or str(message.from_user.id), message.text)
    await send_msg(message,
        f"{{chat}} <b>Сообщение #{tid} отправлено!</b>\n{{loading}} Ожидайте ответа в течение 24 часов.",
        reply_markup=main_menu()
    )
    with suppress(Exception):
        await send_msg(ADMIN_ID,
            f"{{chat}} <b>Новый тикет #{tid}</b>\n{{profile}} От: @{message.from_user.username or message.from_user.id}\n{{write}} Текст: {message.text[:300]}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{B['write']} Ответить", callback_data=f"reply_ticket_{tid}")]
            ])
        )
    await state.clear()

@dp.callback_query(F.data == "bonuses")
async def cb_bonuses(callback: CallbackQuery):
    await send_msg(callback,
        f"{{gift}} <b>БОНУСНАЯ ПРОГРАММА</b>\n\nХочешь получить дополнительный бонус к заказу?\n\n"
        "{{sparkle}} <b>Как получить бонус:</b>\n1. Зайди в настройки своего профиля Telegram\n"
        f"2. В разделе «О себе» (Bio) напиши эту фразу:\n<code>💎 {BOT_USERNAME} — Лучший выбор для депа! 💎</code>\n"
        "3. Сделай заказ через бота\n4. Мы автоматически проверим твой профиль и начислим бонус!\n\n"
        f"{{money}} <b>Размер бонуса:</b> {BONUS_PERCENT}% от GMP\n\n"
        "{{approve}} Бонус начисляется автоматически при проверке заказа!\n\n"
        "{lightning} Акция действует постоянно",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{B['back']} Назад", callback_data="back_menu")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "lottery")
async def cb_lottery(callback: CallbackQuery):
    await send_msg(callback,
        "{jackpot} <b>ЛОТЕРЕЯ</b>\n\n{loading} Раздел в разработке!\nСкоро здесь можно будет выиграть крутые призы.\n\n{megaphone} Следите за обновлениями в канале!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{B['back']} Назад", callback_data="back_menu")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "back_menu")
async def cb_back_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await send_msg(callback, "{home} <b>Главное меню</b>\nВыбери раздел:", reply_markup=main_menu())
    await callback.answer()

# ========== КАЛЬКУЛЯТОР ==========
@dp.message(OrderStates.entering_gmp)
async def process_gmp_input(message: Message, state: FSMContext):
    if message.text and message.text.startswith('/'): return
    try:
        gmp = float(message.text.replace(",", "."))
        if gmp < MIN_GMP_ORDER:
            await send_html(message, f"❌ Минимальный заказ: <b>{MIN_GMP_ORDER} GMP</b>"); return
        gmp_r = float(get_setting('gmp_rate')); star_r = float(get_setting('star_rate'))
        rub = round(gmp * gmp_r, 2); stars = max(int(rub / star_r), MIN_STAR_ORDER)
        await state.update_data(gmp_amount=gmp, price_rub=rub, price_stars=stars)
        await send_msg(message,
            f"{{diamond}} <b>РАСЧЁТ:</b>\n\n💎 GMP: <b>{gmp}</b>\n{{money}} Рубли: <b>{rub} ₽</b>\n{{star}} Звёзды: <b>{stars} ⭐</b>\n\nВыбери способ оплаты:",
            reply_markup=payment_menu()
        )
        await state.set_state(OrderStates.choosing_payment)
    except ValueError: await send_html(message, "❌ Введи число!")

@dp.callback_query(F.data == "calc_rub", OrderStates.entering_gmp)
async def cb_calc_rub(callback: CallbackQuery, state: FSMContext):
    await send_html(callback, "💰 Введи сумму в рублях:", reply_markup=cancel_inline())
    await state.set_state(OrderStates.entering_rub); await callback.answer()

@dp.message(OrderStates.entering_rub)
async def process_rub_input(message: Message, state: FSMContext):
    if message.text and message.text.startswith('/'): return
    try:
        rub = float(message.text.replace(",", "."))
        gmp_r = float(get_setting('gmp_rate')); star_r = float(get_setting('star_rate'))
        gmp = round(rub / gmp_r, 2); stars = max(int(rub / star_r), MIN_STAR_ORDER)
        if gmp < MIN_GMP_ORDER:
            await send_html(message, f"❌ Слишком мало. Минимум: <b>{MIN_GMP_ORDER} GMP</b>"); return
        await state.update_data(gmp_amount=gmp, price_rub=rub, price_stars=stars)
        await send_msg(message,
            f"{{diamond}} <b>РАСЧЁТ:</b>\n\n{{money}} {rub} ₽ = 💎 {gmp} GMP = {{star}} {stars} ⭐\n\nВыбери способ оплаты:",
            reply_markup=payment_menu()
        )
        await state.set_state(OrderStates.choosing_payment)
    except ValueError: await send_html(message, "❌ Введи число!")

@dp.callback_query(F.data == "calc_stars", OrderStates.entering_gmp)
async def cb_calc_stars(callback: CallbackQuery, state: FSMContext):
    await send_html(callback, "⭐ Введи количество звёзд:", reply_markup=cancel_inline())
    await state.set_state(OrderStates.entering_stars); await callback.answer()

@dp.message(OrderStates.entering_stars)
async def process_stars_input(message: Message, state: FSMContext):
    if message.text and message.text.startswith('/'): return
    try:
        stars = int(message.text)
        if stars < MIN_STAR_ORDER:
            await send_html(message, f"❌ Минимум: <b>{MIN_STAR_ORDER} ⭐</b>"); return
        star_r = float(get_setting('star_rate')); gmp_r = float(get_setting('gmp_rate'))
        rub = round(stars * star_r, 2); gmp = round(rub / gmp_r, 2)
        await state.update_data(gmp_amount=gmp, price_rub=rub, price_stars=stars)
        await send_msg(message,
            f"{{diamond}} <b>РАСЧЁТ:</b>\n\n{{star}} {stars} ⭐ = {{money}} {rub} ₽ = 💎 {gmp} GMP\n\nВыбери способ оплаты:",
            reply_markup=payment_menu()
        )
        await state.set_state(OrderStates.choosing_payment)
    except ValueError: await send_html(message, "❌ Введи целое число!")

# ========== ОПЛАТА ==========
@dp.callback_query(F.data == "pay_rub", OrderStates.choosing_payment)
async def cb_pay_rub(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    oid = create_order(callback.from_user.id, callback.from_user.username or str(callback.from_user.id), data['gmp_amount'], data['price_rub'], data['price_stars'], 'rub')
    await state.update_data(order_id=oid)
    await send_msg(callback,
        f"{{bank}} <b>ЗАКАЗ #{oid}</b>\n\n{{money}} Сумма: <b>{data['price_rub']} ₽</b>\n{{diamond}} Получите: <b>{data['gmp_amount']} GMP</b>\n\n{{gallery}} После оплаты отправьте <b>скриншот</b> в этот чат.\nАдмин проверит и начислит GMP.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{B['card']} Оплатить картой", url=TINKOFF_URL)],
            [InlineKeyboardButton(text=f"{B['cancel']} Отменить заказ", callback_data="cancel_order")]
        ])
    )
    await state.set_state(OrderStates.waiting_screenshot); await callback.answer()

@dp.callback_query(F.data == "pay_stars", OrderStates.choosing_payment)
async def cb_pay_stars(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data(); stars = max(int(data['price_stars']), MIN_STAR_ORDER)
    oid = create_order(callback.from_user.id, callback.from_user.username or str(callback.from_user.id), data['gmp_amount'], data['price_rub'], stars, 'stars')
    await state.update_data(order_id=oid)
    await send_msg(callback,
        f"{{star}} <b>ЗАКАЗ #{oid}</b>\n\nОтправьте <b>{stars} ⭐</b> подарком на {SUPPORT_USERNAME}\n{{diamond}} Получите: <b>{data['gmp_amount']} GMP</b>\n\n{{gallery}} После отправки пришлите <b>скриншот</b> в этот чат.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{B['cancel']} Отменить заказ", callback_data="cancel_order")]
        ])
    )
    await state.set_state(OrderStates.waiting_screenshot); await callback.answer()

@dp.message(OrderStates.waiting_screenshot, F.photo)
async def receive_screenshot(message: Message, state: FSMContext):
    data = await state.get_data(); oid = data.get('order_id')
    if not oid: await send_html(message, "❌ Ошибка заказа. Начни заново /start"); await state.clear(); return
    conn = get_db(); c = conn.cursor()
    c.execute('UPDATE orders SET screenshot_id=? WHERE order_id=?', (message.photo[-1].file_id, oid)); conn.commit(); conn.close()
    await send_msg(message,
        f"{{gallery}} <b>Скриншот получен!</b>\n{{loading}} Заказ <b>#{oid}</b> ожидает проверки.\nОбычно это занимает 5-10 минут.",
        reply_markup=main_menu()
    )
    with suppress(Exception):
        await send_msg(ADMIN_ID,
            f"{{bell}} <b>Новый скрин по заказу #{oid}</b>\n{{profile}} От: @{message.from_user.username or message.from_user.id}\n{{money}} Сумма: {data.get('price_rub', '?')} ₽",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{B['approve']} Подтвердить", callback_data=f"approve_{oid}"),
                 InlineKeyboardButton(text=f"{B['cancel']} Отменить", callback_data=f"reject_{oid}")]
            ])
        )
        await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"🖼 Скрин заказа #{oid}")
    await state.clear()

@dp.message(OrderStates.waiting_screenshot)
async def wait_screenshot_text(message: Message, state: FSMContext):
    data = await state.get_data()
    if 'order_id' in data: update_order(data['order_id'], 'cancelled', 'Отменён пользователем')
    await state.clear()
    await send_html(message, "❌ Заказ отменён.", reply_markup=main_menu())

@dp.callback_query(F.data == "cancel_order")
async def cb_cancel_order(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if 'order_id' in data: update_order(data['order_id'], 'cancelled', 'Отменён пользователем')
    await state.clear()
    await send_html(callback, "❌ <b>Заказ отменён.</b>", reply_markup=main_menu())
    await callback.answer()

# ========== АДМИН-ПАНЕЛЬ ==========
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID: await send_html(message, "🚫 Нет доступа."); return
    await send_msg(message, "{admin} <b>АДМИН-ПАНЕЛЬ</b>\n{write} Выберите действие:", reply_markup=admin_menu())

@dp.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    s = get_stats()
    await send_msg(callback,
        f"{{stats}} <b>СТАТИСТИКА</b>\n\n{{profile}} Пользователей: <b>{s['users']}</b> (+{s['today']} сегодня)\n"
        f"{{ban}} Забанено: <b>{s['banned']}</b>\n{{loading}} Заказов ожидает: <b>{s['pending']}</b>\n"
        f"{{approve}} Выполнено: <b>{s['completed']}</b>\n{{cancel}} Отменено: <b>{s['cancelled']}</b>\n"
        f"{{diamond}} GMP выдано: <b>{s['gmp']}</b>\n{{gift}} Бонусов: <b>{s['bonuses']}</b>\n"
        f"{{money}} Оборот ₽: <b>{s['rub']:.2f}</b>\n{{star}} Оборот ⭐: <b>{int(s['stars'])}</b>\n"
        f"{{box}} Заказов всего: <b>{s['total_orders']}</b>\n{{chat}} Открытых тикетов: <b>{s['tickets']}</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{B['back']} Назад", callback_data="admin_back")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_orders")
async def cb_admin_orders(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE status='pending' ORDER BY order_id DESC LIMIT 10")
    orders = c.fetchall(); conn.close()
    if not orders:
        await send_msg(callback, "{box} Нет ожидающих заказов.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{B['back']} Назад", callback_data="admin_back")]
            ])
        ); await callback.answer(); return
    await send_msg(callback, "{loading} Загружаю заказы...")
    for o in orders:
        o = dict(o)
        await send_html(callback.message.chat.id,
            f"📦 <b>Заказ #{o['order_id']}</b>\n👤 @{o['username']} (ID: <code>{o['user_id']}</code>)\n💎 {o['gmp_amount']} GMP | 💰 {o['price_rub']} ₽ | ⭐ {o['price_stars']} ⭐\n💳 Метод: {o['payment_method']}\n📅 {o['created_at']}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{B['approve']} Подтвердить", callback_data=f"approve_{o['order_id']}"),
                 InlineKeyboardButton(text=f"{B['cancel']} Отменить", callback_data=f"reject_{o['order_id']}")]
            ])
        )
    await callback.answer("✅ Заказы загружены")

@dp.callback_query(F.data.startswith("approve_"))
async def cb_approve(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    oid = int(callback.data.split("_")[1]); update_order(oid, 'completed', 'Подтверждено')
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT user_id, gmp_amount FROM orders WHERE order_id=?', (oid,)); o = c.fetchone(); conn.close()
    if o:
        with suppress(Exception):
            await send_msg(o['user_id'],
                f"{{approve}} <b>Заказ #{oid} выполнен!</b>\n{{diamond}} Начислено: <b>{o['gmp_amount']} GMP</b>\nСпасибо за покупку! {{sparkle}}"
            )
    await callback.message.edit_text(callback.message.text + "\n✅ Подтверждено")
    await callback.answer("✅ Подтверждено!")

@dp.callback_query(F.data.startswith("reject_"))
async def cb_reject(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    oid = int(callback.data.split("_")[1]); update_order(oid, 'cancelled', 'Отклонено')
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT user_id FROM orders WHERE order_id=?', (oid,)); o = c.fetchone(); conn.close()
    if o:
        with suppress(Exception):
            await send_msg(o['user_id'],
                f"{{cancel}} <b>Заказ #{oid} отклонён.</b>\n{{chat}} Обратитесь в поддержку: {SUPPORT_USERNAME}"
            )
    await callback.message.edit_text(callback.message.text + "\n❌ Отклонено")
    await callback.answer("❌ Отклонено!")

@dp.callback_query(F.data == "admin_tickets")
async def cb_admin_tickets(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    tickets = get_open_tickets()
    if not tickets:
        await send_msg(callback, "{chat} Нет открытых тикетов.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{B['back']} Назад", callback_data="admin_back")]
            ])
        ); await callback.answer(); return
    await send_msg(callback, "{loading} Загружаю тикеты...")
    for t in tickets:
        await send_html(callback.message.chat.id,
            f"💬 <b>Тикет #{t['ticket_id']}</b>\n👤 @{t['username']} (ID: {t['user_id']})\n✍️ {t['message'][:300]}\n📅 {t['created_at']}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{B['write']} Ответить", callback_data=f"reply_ticket_{t['ticket_id']}")]
            ])
        )
    await callback.answer("✅ Тикеты загружены")

@dp.callback_query(F.data.startswith("reply_ticket_"))
async def cb_reply_ticket_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    tid = int(callback.data.split("_")[2]); await state.update_data(reply_tid=tid)
    await send_msg(callback, f"{{write}} Введи ответ на тикет <b>#{tid}</b>:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{B['cancel']} Отмена", callback_data="admin_back")]
        ])
    ); await state.set_state(AdminStates.waiting_reply_text); await callback.answer()

@dp.message(AdminStates.waiting_reply_text)
async def process_reply(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    data = await state.get_data(); tid = data['reply_tid']; reply_ticket(tid, message.text)
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT user_id FROM support_tickets WHERE ticket_id=?', (tid,)); t = c.fetchone(); conn.close()
    if t:
        with suppress(Exception):
            await send_msg(t['user_id'],
                f"{{chat}} <b>Ответ поддержки (тикет #{tid}):</b>\n\n{message.text}\n\n{{write}} Если остались вопросы — создайте новый тикет."
            )
    await send_msg(message, f"{{approve}} Ответ на тикет <b>#{tid}</b> отправлен.", reply_markup=admin_menu())
    await state.clear()

@dp.callback_query(F.data == "admin_rate")
async def cb_admin_rate(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    gmp_r = get_setting('gmp_rate'); star_r = get_setting('star_rate')
    await send_msg(callback,
        f"{{money}} <b>Текущие курсы:</b>\n{{diamond}} 1 GMP = <b>{gmp_r} ₽</b>\n{{star}} 1 ⭐ = <b>{star_r} ₽</b>\n\n{{write}} Введи новый курс GMP (в рублях):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{B['back']} Назад", callback_data="admin_back")]
        ])
    ); await state.set_state(AdminStates.waiting_rate_gmp); await callback.answer()

@dp.message(AdminStates.waiting_rate_gmp)
async def set_rate_gmp(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        r = float(message.text.replace(",", ".")); set_setting('gmp_rate', str(r))
        await send_html(message, f"✅ 1 GMP = {r} ₽\n✍️ Теперь введи курс звёзд (1 ⭐ = X ₽):")
        await state.set_state(AdminStates.waiting_rate_star)
    except ValueError: await send_html(message, "❌ Введи число!")

@dp.message(AdminStates.waiting_rate_star)
async def set_rate_star(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        r = float(message.text.replace(",", ".")); set_setting('star_rate', str(r))
        await send_msg(message, f"{{approve}} 1 ⭐ = {r} ₽\n{{lightning}} Курсы обновлены!", reply_markup=admin_menu())
        await state.clear()
    except ValueError: await send_html(message, "❌ Введи число!")

@dp.callback_query(F.data == "admin_req")
async def cb_admin_req(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    r = get_setting('requisites')
    await send_msg(callback,
        f"{{card}} <b>Текущие реквизиты:</b>\n{r[:500]}\n\n{{write}} Введи новые реквизиты:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{B['back']} Назад", callback_data="admin_back")]
        ])
    ); await state.set_state(AdminStates.waiting_requisites); await callback.answer()

@dp.message(AdminStates.waiting_requisites)
async def set_req(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    set_setting('requisites', message.text)
    await send_msg(message, "{approve} Реквизиты обновлены!", reply_markup=admin_menu()); await state.clear()

@dp.callback_query(F.data == "admin_promo")
async def cb_admin_promo(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await send_msg(callback, "{ticket} <b>СОЗДАНИЕ ПРОМОКОДА</b>\n\n{write} Введи код (латиница/цифры):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{B['back']} Назад", callback_data="admin_back")]
        ])
    ); await state.set_state(AdminStates.waiting_promo_code); await callback.answer()

@dp.message(AdminStates.waiting_promo_code)
async def set_promo_code(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.update_data(promo_code=message.text.strip().upper())
    await send_html(message, "✍️ Введи процент бонуса (число):")
    await state.set_state(AdminStates.waiting_promo_percent)

@dp.message(AdminStates.waiting_promo_percent)
async def set_promo_percent(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        await state.update_data(promo_percent=int(message.text))
        await send_html(message, "✍️ Введи макс. число использований:")
        await state.set_state(AdminStates.waiting_promo_uses)
    except ValueError: await send_html(message, "❌ Введи целое число!")

@dp.message(AdminStates.waiting_promo_uses)
async def set_promo_uses(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        uses = int(message.text); data = await state.get_data()
        create_promo(data['promo_code'], data['promo_percent'], uses)
        await send_msg(message,
            f"{{approve}} <b>Промокод создан!</b>\n{{ticket}} Код: <b>{data['promo_code']}</b>\n{{gift}} Бонус: <b>{data['promo_percent']}%</b>\n{{numbers}} Использований: <b>{uses}</b>\n{{calendar}} Срок: 72 часа",
            reply_markup=admin_menu()
        ); await state.clear()
    except ValueError: await send_html(message, "❌ Введи целое число!")

@dp.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await send_msg(callback, "{bell} <b>РАССЫЛКА</b>\n\n{write} Введи текст для рассылки:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{B['back']} Назад", callback_data="admin_back")]
        ])
    ); await state.set_state(AdminStates.waiting_broadcast); await callback.answer()

@dp.message(AdminStates.waiting_broadcast)
async def do_broadcast(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT user_id FROM users WHERE banned=0'); users = c.fetchall(); conn.close()
    await send_html(message, f"⏳ Начинаю рассылку на {len(users)} пользователей...")
    sent = 0
    for u in users:
        with suppress(Exception):
            await bot.send_message(u['user_id'], f"🔔 <b>Рассылка:</b>\n\n{message.text}")
            sent += 1; await asyncio.sleep(0.05)
    await send_html(message, f"✅ <b>Рассылка завершена!</b>\nОтправлено: <b>{sent}</b> / {len(users)}", reply_markup=admin_menu())
    await state.clear()

@dp.callback_query(F.data == "admin_db")
async def cb_admin_db(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    try:
        await callback.message.answer_document(FSInputFile(DB_NAME), caption=f"📥 База данных\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    except: await send_html(callback, "❌ Файл БД не найден.")
    await callback.answer()

@dp.callback_query(F.data == "admin_ban")
async def cb_admin_ban(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await send_msg(callback, "{ban} <b>БАН ПОЛЬЗОВАТЕЛЯ</b>\n\n{write} Введи ID пользователя:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{B['back']} Назад", callback_data="admin_back")]
        ])
    ); await state.set_state(AdminStates.waiting_ban_id); await callback.answer()

@dp.message(AdminStates.waiting_ban_id)
async def do_ban(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        uid = int(message.text); u = get_user(uid)
        if not u: await send_html(message, "❌ Пользователь не найден."); return
        if u['banned']:
            unban_user_db(uid)
            await send_html(message, f"✅ Пользователь <b>{uid}</b> разбанен.", reply_markup=admin_menu())
        else:
            ban_user_db(uid)
            await send_html(message, f"🚫 Пользователь <b>{uid}</b> забанен.", reply_markup=admin_menu())
            try: await bot.send_message(uid, "🚫 <b>Вы заблокированы в боте.</b>")
            except: pass
        await state.clear()
    except ValueError: await send_html(message, "❌ Введи корректный ID!")

@dp.callback_query(F.data == "admin_search")
async def cb_admin_search(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await send_msg(callback, "🔍 <b>ПОИСК</b>\n\n{write} Введи ID пользователя или номер заказа:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{B['back']} Назад", callback_data="admin_back")]
        ])
    ); await state.set_state(AdminStates.waiting_search); await callback.answer()

@dp.message(AdminStates.waiting_search)
async def do_search(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    query = message.text.strip(); conn = get_db(); c = conn.cursor()
    c.execute('SELECT * FROM orders WHERE order_id=?', (query,)); order = c.fetchone()
    if order:
        order = dict(order)
        await send_html(message,
            f"📦 <b>Заказ #{order['order_id']}</b>\n👤 ID: {order['user_id']}\n@{order['username']}\n💎 {order['gmp_amount']} GMP\n💰 {order['price_rub']} ₽ | ⭐ {order['price_stars']} ⭐\n💳 Метод: {order['payment_method']}\nСтатус: {order['status']}\n📅 {order['created_at']}"
        ); conn.close(); await state.clear(); return
    c.execute('SELECT * FROM orders WHERE user_id=? ORDER BY order_id DESC LIMIT 10', (query,)); orders = c.fetchall()
    if orders:
        text = f"👤 <b>Заказы пользователя {query}:</b>\n\n"
        for o in orders: o = dict(o); text += f"📦 #{o['order_id']} | 💎 {o['gmp_amount']} GMP | {o['status']} | {o['created_at']}\n"
        await send_html(message, text)
    else:
        c.execute("SELECT * FROM support_tickets WHERE user_id=? ORDER BY ticket_id DESC LIMIT 5", (query,)); tickets = c.fetchall()
        if tickets:
            text = f"💬 <b>Тикеты пользователя {query}:</b>\n\n"
            for t in tickets: t = dict(t); text += f"#{t['ticket_id']} | {t['message'][:50]}... | {t['status']}\n"
            await send_html(message, text)
        else: await send_html(message, "❌ Ничего не найдено.")
    conn.close(); await state.clear()

@dp.callback_query(F.data == "admin_back")
async def cb_admin_back(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await state.clear()
    await send_msg(callback, "{admin} <b>АДМИН-ПАНЕЛЬ</b>\n{write} Выберите действие:", reply_markup=admin_menu())
    await callback.answer()

@dp.callback_query(F.data == "admin_exit")
async def cb_admin_exit(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    await send_msg(callback, "{home} <b>Главное меню</b>\nВыбери раздел:", reply_markup=main_menu())
    await callback.answer()

# ========== ЗАПУСК ==========
async def main():
    init_db()
    logger.info(f"✅ Бот {BOT_USERNAME} запущен!")
    logger.info(f"👑 Админ ID: {ADMIN_ID}")
    logger.info(f"💎 34 премиум-эмодзи готовы")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
