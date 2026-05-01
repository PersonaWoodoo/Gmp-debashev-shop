import sqlite3
from datetime import datetime

DB_NAME = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Пользователи
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            registered_at TEXT,
            banned INTEGER DEFAULT 0,
            total_gmp_received REAL DEFAULT 0,
            bonus_tickets INTEGER DEFAULT 0
        )
    ''')

    # Заказы
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            gmp_amount REAL,
            price_rub REAL,
            price_stars REAL,
            payment_method TEXT,
            status TEXT DEFAULT 'pending',
            screenshot_id TEXT,
            admin_comment TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')

    # Промокоды
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS promo_codes (
            code TEXT PRIMARY KEY,
            bonus_percent INTEGER,
            max_uses INTEGER,
            used_count INTEGER DEFAULT 0,
            created_by INTEGER,
            is_active
