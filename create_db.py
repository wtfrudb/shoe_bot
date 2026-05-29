import sqlite3
import os

# Удаляем старую риелторскую базу данных, если она существует
if os.path.exists('realty_bot.db'):
    os.remove('realty_bot.db')

conn = sqlite3.connect('realty_bot.db')
cursor = conn.cursor()

# 1. Создаем таблицу истории диалогов
cursor.execute('''
    CREATE TABLE conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        user_message TEXT,
        bot_answer TEXT,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# 2. Создаем таблицу для ОБУВИ
cursor.execute('''
    CREATE TABLE shoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price REAL,
        price_text TEXT,
        description TEXT,
        shoes_type TEXT,
        brand TEXT,
        url TEXT
    )
''')

# 3. Наполняем базу данных ТОЛЬКО реально существующими моделями
shoes_data = [
    # Кроссовки
    ('Nike Air Force 1 07', 13990.0, '13 990 руб.', 'Легендарные баскетбольные кроссовки. Белая классика на все времена с технологией амортизации Air.', 'кроссовки', 'Nike', 'https://www.nike.com'),
    ('Nike Air Max 90', 16500.0, '16 500 руб.', 'Культовый беговой силуэт из 90-х. Видимый воздушный баллон в пятке, превосходная поддержка стопы.', 'кроссовки', 'Nike', 'https://www.nike.com'),
    ('Adidas Ultraboost 1.0', 18900.0, '18 900 руб.', 'Премиальные кроссовки для бега и ходьбы. Мягкий вязаный верх Primeknit и легендарная подошва Boost.', 'кроссовки', 'Adidas', 'https://www.adidas.com'),
    ('Puma RS-X Efekt', 11800.0, '11 800 руб.', 'Массивные футуристичные кроссовки из комбинации сетки и замши. Яркий дизайн в стиле ретро-футуризма.', 'кроссовки', 'Puma', 'https://www.puma.com'),
    ('Reebok Classic Leather', 9490.0, '9 490 руб.', 'Мягкая натуральная кожа и лаконичный силуэт. Идеальная базовая пара на каждый день под любой гардероб.', 'кроссовки', 'Reebok', 'https://www.reebok.com'),

    # Кеды
    ('Adidas Superstar', 11500.0, '11 500 руб.', 'Знаменитые кеды с кожаным верхом и прорезиненным мыском-ракушкой. Икона уличной моды с 1969 года.', 'кеды', 'Adidas', 'https://www.adidas.com'),
    ('Puma Club Nylon', 8900.0, '8 990 руб.', 'Классические низкие кеды в футбольном стиле T-toe. Верх из прочного нейлона со вставками из замши.', 'кеды', 'Puma', 'https://www.puma.com'),
    ('Reebok Club C 85', 9990.0, '9 990 руб.', 'Минималистичные теннисные кеды родом из 1985 года. Мягкая кожа, прошитая подошва и винтажный логотип.', 'кеды', 'Reebok', 'https://www.reebok.com'),

    # Ботинки
    ('Puma Desierto v3 Rubber', 14500.0, '14 500 руб.', 'Высокие зимние ботинки с водонепроницаемой мембраной PureTex, теплой подкладкой и мощным зимним протектором.', 'ботинки', 'Puma', 'https://www.puma.com'),
    ('Adidas Terrex Conrax BOA', 24000.0, '24 000 руб.', 'Технологичные хайкинговые ботинки для экстремальных условий. Утеплитель PrimaLoft, мембрана RAIN.RDY и фиксация BOA.', 'ботинки', 'Adidas', 'https://www.adidas.com'),
    
    # Туфли (Реальные хайповые и дизайнерские модели)
    ('Adidas Jabbar Dress Low x Willy Chavarria', 22000.0, '22 000 руб.', 'Эксклюзивная коллаборация с дизайнером Вилли Чаварри. Винтажный силуэт Джаббара переосмыслен в формате премиальных строгих туфель.', 'туфли', 'Adidas', 'https://www.adidas.com'),
    ('Puma Speedcat Mary Jane', 13500.0, '13 500 руб.', 'Трендовые туфли-балетки на основе гоночных Speedcat. Элегантный ремешок сверху, тонкая подошва и мягкая натуральная замша.', 'туфли', 'Puma', 'https://www.puma.com')
]

cursor.executemany('''INSERT INTO shoes 
                      (name, price, price_text, description, shoes_type, brand, url) 
                      VALUES (?, ?, ?, ?, ?, ?, ?)''', shoes_data)

conn.commit()
conn.close()

print("👟 База данных успешно пересоздана!")
print("Загружены только РЕАЛЬНЫЕ модели обуви.")
print("Категории: кроссовки, кеды, ботинки, туфли")