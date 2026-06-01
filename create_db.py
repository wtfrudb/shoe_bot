import sqlite3
import os

if os.path.exists('shoe_shop.db'):
    os.remove('shoe_shop.db')

conn = sqlite3.connect('shoe_shop.db')
cursor = conn.cursor()

# 1. Таблица истории (без изменений)
cursor.execute('''CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    user_message TEXT,
    bot_answer TEXT,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

# 2. Таблица моделей (только общая информация)
cursor.execute('''CREATE TABLE shoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    description TEXT,
    shoes_type TEXT,
    brand TEXT,
    gender TEXT
)''')

# 3. Вариации (Цвета + Ссылка на картинку для этого цвета)
cursor.execute('''CREATE TABLE shoe_variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shoe_id INTEGER,
    color_name TEXT,
    image_url TEXT,
    price REAL,
    FOREIGN KEY(shoe_id) REFERENCES shoes(id)
)''')

# 4. Наличие (Связь варианта с размером и количеством)
cursor.execute('''CREATE TABLE stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id INTEGER,
    size INTEGER,
    quantity INTEGER,
    FOREIGN KEY(variant_id) REFERENCES shoe_variants(id)
)''')

conn.commit()
conn.close()
print("База данных успешно пересоздана для новой структуры!")