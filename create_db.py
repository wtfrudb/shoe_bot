import sqlite3
import os

# Удаляем старую базу данных обуви, если она существовала
if os.path.exists('shoe_shop.db'):
    os.remove('shoe_shop.db')

conn = sqlite3.connect('shoe_shop.db')
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

# 2. Создаем таблицу для ОБУВИ (Добавлена колонка image_url)
cursor.execute('''
    CREATE TABLE shoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price REAL,
        price_text TEXT,
        description TEXT,
        shoes_type TEXT,
        brand TEXT,
        url TEXT,
        image_url TEXT,
        gender TEXT
    )
''')

# 3. Создаем таблицу для РАЗМЕРОВ
cursor.execute('''
    CREATE TABLE stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shoe_id INTEGER,
        size INTEGER,
        quantity INTEGER,
        FOREIGN KEY(shoe_id) REFERENCES shoes(id)
    )
''')

# Наполняем базу данных (Добавлена ссылка на реальные красивые фото из Unsplash)
shoes_data = [
    # === МУЖСКАЯ ОБУВЬ ===
    ('Nike Air Force 1 07 (Men)', 13990.0, '13 990 руб.', 'Легендарные баскетбольные кроссовки. Белая классика на все времена с технологией амортизации Air.', 'кроссовки', 'Nike', 'https://www.nike.com', 'https://images.unsplash.com/photo-1600185365483-26d7a4cc7519?w=500', 'мужской'),
    ('Adidas Ultraboost 1.0 (Men)', 18900.0, '18 900 руб.', 'Премиальные кроссовки для бега и ходьбы. Мягкий вязаный верх Primeknit и легендарная подошва Boost.', 'кроссовки', 'Adidas', 'https://www.adidas.com', 'https://images.unsplash.com/photo-1508138221679-760a3892f01c?w=500', 'мужской'),
    ('Puma RS-X Efekt (Men)', 11800.0, '11 800 руб.', 'Массивные футуристичные кроссовки из комбинации сетки и замши. Яркий дизайн в стиле ретро-футуризма.', 'кроссовки', 'Puma', 'https://www.puma.com', 'https://images.unsplash.com/photo-1597045566677-8cf032ed6634?w=500', 'мужской'),
    ('Adidas Superstar (Men)', 11500.0, '11 500 руб.', 'Знаменитые мужские кеды с кожаным верхом и прорезиненным мыском-ракушкой. Икона уличной моды.', 'кеды', 'Adidas', 'https://www.adidas.com', 'https://images.unsplash.com/photo-1549298916-b41d501d3772?w=500', 'мужской'),
    ('Nike SB Chron 2 Slip', 7490.0, '7 490 руб.', 'Легкие текстильные слипоны для скейтбординга и повседневной ходьбы. Удобная посадка без шнурков.', 'слипоны', 'Nike', 'https://www.nike.com', 'https://images.unsplash.com/photo-1560769629-975ec94e6a86?w=500', 'мужской'),
    ('Nike Cole Haan Grand Oxford', 19500.0, '19 500 руб.', 'Классические мужские туфли-оксфорды со скрытой технологией беговой амортизации Nike Air в подошве.', 'туфли', 'Nike', 'https://www.nike.com', 'https://images.unsplash.com/photo-1539185441755-769473a23570?w=500', 'мужской'),
    ('Puma Palermo Loafer', 14990.0, '14 990 руб.', 'Трендовые кожаные лоферы на базе силуэта Palermo. Элегантный стиль, совмещенный со спортивной подошвой.', 'лоферы', 'Puma', 'https://www.puma.com', 'https://images.unsplash.com/photo-1614252235316-8c857d38b5f4?w=500', 'мужской'),
    ('Puma Suede Moc V', 11200.0, '11 200 руб.', 'Стильные повседневные мокасины из натуральной ультра-мягкой замши со знаковым силуэтом Puma Suede.', 'мокасины', 'Puma', 'https://www.puma.com', 'https://images.unsplash.com/photo-1520639888713-7851133b1ed0?w=500', 'мужской'),
    ('Puma Desierto v3 Rubber', 14500.0, '14 500 руб.', 'Высокие зимние ботинки с водонепроницаемой мембраной PureTex, теплой подкладкой и зимним протектором.', 'ботинки', 'Puma', 'https://www.puma.com', 'https://images.unsplash.com/photo-1483985988355-763728e1935b?w=500', 'мужской'),
    ('Adidas Terrex Conrax BOA', 24000.0, '24 000 руб.', 'Технологичные хайкинговые ботинки. Утеплитель PrimaLoft, мембрана RAIN.RDY и быстрая фиксация BOA.', 'ботинки', 'Adidas', 'https://www.adidas.com', 'https://images.unsplash.com/photo-1533867617858-e7b97e060509?w=500', 'мужской'),
    ('Adidas Originals Western Strider', 28900.0, '28 900 руб.', 'Лимитированные ковбойские сапоги-казаки со скошенным каблуком, выполненные из премиальной фактурной кожи.', 'казаки', 'Adidas', 'https://www.adidas.com', 'https://images.unsplash.com/photo-1551107696-a4b0c5a0d9a2?w=500', 'мужской'),
    ('Adidas Cyprex Ultra II', 7990.0, '7 990 руб.', 'Надежные туристические сандалии для активного отдыха у воды и прогулок в жаркие летние дни.', 'сандалии', 'Adidas', 'https://www.adidas.com', 'https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=500', 'мужской'),

    # === ЖЕНСКАЯ ОБУВЬ ===
    ('Nike Air Max 90 (Women)', 16500.0, '16 500 руб.', 'Культовый беговой силуэт из 90-х. Женская расцветка, легендарный комфорт и видимый воздушный баллон.', 'кроссовки', 'Nike', 'https://www.nike.com', 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500', 'женский'),
    ('Reebok Classic Leather (Women)', 9490.0, '9 490 руб.', 'Мягкая натуральная кожа белого цвета и лаконичный силуэт. Идеальная женская базовая пара на каждый день.', 'кроссовки', 'Reebok', 'https://www.reebok.com', 'https://images.unsplash.com/photo-1582588678413-dbf45f4823e9?w=500', 'женский'),
    ('Puma Club Nylon (Women)', 8900.0, '8 900 руб.', 'Классические низкие кеды в футбольном стиле T-toe. Легкие, аккуратно смотрятся на женской ножке.', 'кеды', 'Puma', 'https://www.puma.com', 'https://images.unsplash.com/photo-1511556532299-8f662fc26c06?w=500', 'женский'),
    ('Reebok Club C 85 (Women)', 9990.0, '9 990 руб.', 'Минималистичные женские теннисные кеды родом из 1985 года. Мягкая винтажная кожа.', 'кеды', 'Reebok', 'https://www.reebok.com', 'https://images.unsplash.com/photo-1575537359674-342ba15dfcbf?w=500', 'женский'),
    ('Adidas Court Rally Slip', 6990.0, '6 990 руб.', 'Минималистичные хлопковые слипоны на гибкой вулканизированной подошве. Идеально для жаркого лета.', 'слипоны', 'Adidas', 'https://www.adidas.com', 'https://images.unsplash.com/photo-1606107557195-0e29a4b5b4aa?w=500', 'женский'),
    ('Adidas Jabbar Dress Low', 22000.0, '22 000 руб.', 'Эксклюзивная коллекция. Премиальные строгие кожаные туфли для утонченного образа.', 'туфли', 'Adidas', 'https://www.adidas.com', 'https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=500', 'женский'),
    ('Puma Speedcat Mary Jane', 13500.0, '13 500 руб.', 'Трендовые туфли-балетки на основе гоночных Speedcat. Элегантный ремешок и мягкая натуральная замша.', 'балетки', 'Puma', 'https://www.puma.com', 'https://images.unsplash.com/photo-1491553895911-0055eca6402d?w=500', 'женский'),
    ('Adidas Terrex Winter Boot', 21990.0, '21 990 руб.', 'Высокие зимние сапоги-дутики с мембраной GORE-TEX и глубоким технологичным протектором Continental.', 'сапоги', 'Adidas', 'https://www.adidas.com', 'https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=500', 'женский'),
    ('Nike ACG Gaiadome GORE-TEX', 26500.0, '26 500 руб.', 'Профессиональные высокие сапоги-треккеры для суровых зим. Полная защита от промокания.', 'сапоги', 'Nike', 'https://www.nike.com', 'https://images.unsplash.com/photo-1607522370275-f14206abe5d3?w=500', 'женский'),
    ('Nike ACG Woodside Chukka', 13200.0, '13 200 руб.', 'Элегантные укороченные женские ботильоны с резиновой калошей для защиты от слякоти и влажной осени.', 'ботильоны', 'Nike', 'https://www.nike.com', 'https://images.unsplash.com/photo-1539185441755-769473a23570?w=500', 'женский'),
    ('Reebok Work N Cushion Boot', 11990.0, '11 990 руб.', 'Прочные осенние кожаные ботинки с поддержкой голеностопа и мягкой межподошвой.', 'ботинки', 'Reebok', 'https://www.reebok.com', 'https://images.unsplash.com/photo-1512374382149-4332c6c02150?w=500', 'женский'),
    ('Nike Air Max Sol Sandal', 8990.0, '8 990 руб.', 'Спортивные летние сандалии на регулируемых липучках. Мягкая подошва с воздушной подушкой Air Max.', 'сандалии', 'Nike', 'https://www.nike.com', 'https://images.unsplash.com/photo-1603252109303-2751441dd157?w=500', 'женский'),
    ('Puma Platform Sandal Pop', 6490.0, '6 490 руб.', 'Открытые летние босоножки на высокой легкой платформе. Яркий дизайн и надежная фиксация стопы.', 'босоножки', 'Puma', 'https://www.puma.com', 'https://images.unsplash.com/photo-1562183241-b937e95585b6?w=500', 'женский'),
    ('Adidas Adilette Clog', 4990.0, '4 990 руб.', 'Удобные закрытые сабо-клоги на основе культовых шлепанцев Adilette. Легкий полимерный материал EVA.', 'сабо', 'Adidas', 'https://www.adidas.com', 'https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?w=500', 'женский'),
    ('Nike Calm Mule', 7990.0, '7 990 руб.', 'Минималистичные мюли со съемным задним ремешком. Водонепронимаемая пена, которая легко моется.', 'мюли', 'Nike', 'https://www.nike.com', 'https://images.unsplash.com/photo-1551107696-a4b0c5a0d9a2?w=500', 'женский')
]

# Заполняем таблицу обуви (9 параметров)
cursor.executemany('''INSERT INTO shoes 
                      (name, price, price_text, description, shoes_type, brand, url, image_url, gender) 
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', shoes_data)

# Автоматически генерируем размеры для каждой пары в таблицу stock
cursor.execute("SELECT id, gender FROM shoes")
inserted_shoes = cursor.fetchall()

stock_data = []
for shoe_id, gender in inserted_shoes:
    # Женским моделям даем размеры 36, 37, 38, 39. Мужским — 41, 42, 43, 44
    sizes = [36, 37, 38, 39] if gender == 'женский' else [41, 42, 43, 44]
    for size in sizes:
        stock_data.append((shoe_id, size, 5)) # 5 штук каждого размера

cursor.executemany("INSERT INTO stock (shoe_id, size, quantity) VALUES (?, ?, ?)", stock_data)

conn.commit()
conn.close()

print("База успешно создана! Размеры и фото добавлены автоматически.")