import sqlite3

def fill_database():
    # Подключаемся к базе
    conn = sqlite3.connect('shoe_shop.db')
    cursor = conn.cursor()

    # Очищаем таблицы перед наполнением
    cursor.execute("DELETE FROM stock")
    cursor.execute("DELETE FROM shoe_variants")
    cursor.execute("DELETE FROM shoes")

    # Список товаров
    items = [
        {
            'name': 'Nike Air Force 1 07', 'desc': 'Легендарные баскетбольные кроссовки.', 'type': 'кроссовки', 
            'brand': 'Nike', 'gender': 'мужской',
            'variants': [
                {'color': 'Белый', 'img': 'https://link1.jpg', 'price': 13990, 'sizes': {40: 5, 41: 5, 42: 0}}, # 42 нет
                {'color': 'Черный', 'img': 'https://link2.jpg', 'price': 13990, 'sizes': {40: 2, 41: 2, 42: 2}}
            ]
        },
        {
            'name': 'Adidas Ultraboost 1.0', 'desc': 'Премиальные кроссовки для бега.', 'type': 'кроссовки', 
            'brand': 'Adidas', 'gender': 'мужской',
            'variants': [
                {'color': 'Синий', 'img': 'https://link3.jpg', 'price': 18900, 'sizes': {41: 4, 42: 4}}
            ]
        },
        {
            'name': 'Puma RS-X Efekt', 'desc': 'Футуристичные кроссовки.', 'type': 'кроссовки', 
            'brand': 'Puma', 'gender': 'мужской',
            'variants': [
                {'color': 'Бежевый', 'img': 'https://link4.jpg', 'price': 11800, 'sizes': {40: 3, 41: 3}}
            ]
        },
        {
            'name': 'Adidas Superstar', 'desc': 'Знаменитые кеды с ракушкой.', 'type': 'кеды', 
            'brand': 'Adidas', 'gender': 'мужской',
            'variants': [
                {'color': 'Белый с черным', 'img': 'https://link5.jpg', 'price': 11500, 'sizes': {40: 5, 41: 5, 42: 5}}
            ]
        },
        {
            'name': 'Nike SB Chron 2 Slip', 'desc': 'Удобные слипоны.', 'type': 'слипоны', 
            'brand': 'Nike', 'gender': 'мужской',
            'variants': [
                {'color': 'Серый', 'img': 'https://link6.jpg', 'price': 7490, 'sizes': {40: 10, 41: 10}}
            ]
        },
        {
            'name': 'Nike Air Max 90 (Women)', 'desc': 'Культовый силуэт из 90-х.', 'type': 'кроссовки', 
            'brand': 'Nike', 'gender': 'женский',
            'variants': [
                {'color': 'Розовый', 'img': 'https://link7.jpg', 'price': 16500, 'sizes': {36: 2, 37: 2, 38: 0}},
                {'color': 'Белый', 'img': 'https://link8.jpg', 'price': 16500, 'sizes': {36: 5, 37: 5, 38: 5}}
            ]
        },
        {
            'name': 'Reebok Classic Leather', 'desc': 'Базовая кожаная пара.', 'type': 'кроссовки', 
            'brand': 'Reebok', 'gender': 'женский',
            'variants': [
                {'color': 'Белый', 'img': 'https://link9.jpg', 'price': 9490, 'sizes': {36: 3, 37: 3}}
            ]
        },
        {
            'name': 'Puma Speedcat Mary Jane', 'desc': 'Трендовые балетки.', 'type': 'балетки', 
            'brand': 'Puma', 'gender': 'женский',
            'variants': [
                {'color': 'Черный', 'img': 'https://link10.jpg', 'price': 13500, 'sizes': {36: 4, 37: 4}}
            ]
        },
        {
            'name': 'Adidas Terrex Winter Boot', 'desc': 'Технологичные зимние сапоги.', 'type': 'сапоги', 
            'brand': 'Adidas', 'gender': 'женский',
            'variants': [
                {'color': 'Черный', 'img': 'https://link11.jpg', 'price': 21990, 'sizes': {37: 2, 38: 2}}
            ]
        },
        {
            'name': 'Nike Calm Mule', 'desc': 'Минималистичные мюли.', 'type': 'мюли', 
            'brand': 'Nike', 'gender': 'женский',
            'variants': [
                {'color': 'Бежевый', 'img': 'https://link12.jpg', 'price': 7990, 'sizes': {36: 8, 37: 8}}
            ]
        }
    ]

    for item in items:
        # Вставляем модель
        cursor.execute("INSERT INTO shoes (name, description, shoes_type, brand, gender) VALUES (?, ?, ?, ?, ?)",
                       (item['name'], item['desc'], item['type'], item['brand'], item['gender']))
        shoe_id = cursor.lastrowid
        
        # Вставляем варианты (цвета)
        for var in item['variants']:
            cursor.execute("INSERT INTO shoe_variants (shoe_id, color_name, image_url, price) VALUES (?, ?, ?, ?)",
                           (shoe_id, var['color'], var['img'], var['price']))
            variant_id = cursor.lastrowid
            
            # Вставляем размеры
            for size, qty in var['sizes'].items():
                cursor.execute("INSERT INTO stock (variant_id, size, quantity) VALUES (?, ?, ?)",
                               (variant_id, size, qty))

    conn.commit()
    conn.close()
    print("База данных успешно наполнена!")

if __name__ == '__main__':
    fill_database()