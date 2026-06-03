import sqlite3
import os

# Удаляем старую базу данных обуви, если она существовала
if os.path.exists('shoe_shop.db'):
    os.remove('shoe_shop.db')

conn = sqlite3.connect('shoe_shop.db')
cursor = conn.cursor()

# Создание таблиц
cursor.execute('''
    CREATE TABLE conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        user_id TEXT, 
        user_message TEXT, 
        bot_answer TEXT, 
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

cursor.execute('''
    CREATE TABLE shoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, price REAL, 
        price_text TEXT, 
        description TEXT, 
        shoes_type TEXT, 
        brand TEXT, 
        url TEXT, 
        image_url TEXT,
        gender TEXT
    )
''')

cursor.execute('CREATE INDEX idx_shoes_type_gender ON shoes(shoes_type, gender)')

cursor.execute('''
    CREATE TABLE stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        shoe_id INTEGER, 
        size REAL, 
        quantity INTEGER, 
        FOREIGN KEY(shoe_id) REFERENCES shoes(id)
    )
''')

shoes_data = [
    # МУЖСКИЕ
    ('Nike Air Max Muse (Men)', 13439.0, '13 439 руб.', 'Кроссовки Nike Air Max Muse выполнены из комбинации текстиля и синтетической кожи', 'Кроссовки', 'Nike', 
     'https://www.lamoda.ru/p/rtlaez517101/shoes-nike-krossovki/?utm_source=YDirect&utm_medium=cpc&utm_campaign=709827212.RU_SEMNB_WEB_Gallery_Sport_bns_2&utm_content=5751561535&utm_term=205751561535.---autotargeting&adjust_tracker=fk2tk4_56bkkg&adjust_campaign=RU_SEMNB_WEB_Gallery_Sport_bns_2&adjust_adgroup=5751561535&adjust_creative=205751561535.---autotargeting&adjust_ya_click_id=12738065913458720767&yclid=12738065913458720767&utm_referrer=https%3a%2f%2fyandex.ru%2f', 
     r'C:\Users\Tania\Desktop\images_boots\Nike Air Max Muse.jpg', 'мужской'),

    ('Adidas ULTRABOOST 22 (Men)', 15320.0, '15 320 руб.', 'Кроссовки выполнены из текстиля в комбинации с полимерными материалами', 'Кроссовки', 'Adidas', 
     'https://www.lamoda.ru/p/rtlaaz638502/shoes-adidas-krossovki/?utm_source=YDirect&utm_medium=cpc&utm_campaign=709827212.RU_SEMNB_WEB_Gallery_Sport_bns_2&utm_content=5749954374&utm_term=205749954374.---autotargeting&adjust_tracker=fk2tk4_56bkkg&adjust_campaign=RU_SEMNB_WEB_Gallery_Sport_bns_2&adjust_adgroup=5749954374&adjust_creative=205749954374.---autotargeting&adjust_ya_click_id=1953357114619199487&yclid=1953357114619199487', 
     r'C:\Users\Tania\Desktop\images_boots\ULTRABOOST 22.jpg', 'мужской'),

    ('Reebok CLASSIC LEATHER (Men)', 5149.0, '5 149 руб.', 'Универсальные кроссовки, которые всегда будут твоей любимой классикой', 'Кроссовки', 'Reebok', 
     'https://www.lamoda.ru/p/rtlaeb048901/shoes-reebok-krossovki/?utm_source=m_medium=cpc&utm_campaign=709827212.RU_SEMNB_WEB_Gallery_Sport_bns_2&utm_content=5749954YDirect&ut374&utm_term=205749954374.---autotargeting&adjust_tracker=fk2tk4_56bkkg&adjust_campaign=RU_SEMNB_WEB_Gallery_Sport_bns_2&adjust_adgroup=5749954374&adjust_creative=205749954374.---autotargeting&adjust_ya_click_id=920558410857447423&yclid=920558410857447423', 
     r'C:\Users\Tania\Desktop\images_boots\reebok CLASSIC LEATHER.jpg', 'мужской'),

    ('New Balance 574 (Men)', 13599.0, '13 599 руб.', 'New Balance 574 — это самая узнаваемая и продаваемая модель бренда, ставшая символом комфорта и классического спортивного стиля с момента своего выхода в 1988 году', 'Кроссовки', 'New Balance', 
     'https://www.lamoda.ru/p/rtlafa234101/shoes-newbalance-krossovki/?utm_source=YDirect&utm_medium=cpc&utm_campaign=709827212.RU_SEMNB_WEB_Gallery_Sport_bns_2&utm_content=5749954374&utm_term=205749954374.---autotargeting&adjust_tracker=fk2tk4_56bkkg&adjust_campaign=RU_SEMNB_WEB_Gallery_Sport_bns_2&adjust_adgroup=5749954374&adjust_creative=205749954374.---autotargeting&adjust_ya_click_id=6134153342547394559&yclid=6134153342547394559', 
     r'C:\Users\Tania\Desktop\images_boots\New Balance 574.jpg', 'мужской'),

    ('Puma RS-X Efekt Perf (Men)', 12344.0, '12 344 руб.', 'Силуэт этих кроссовок, сочетающий элементы стиля ретро и футуризма, возвращается с прогрессивной эстетикой и угловатыми деталями, и такая комбинация создает сногсшибательный образ, свидетельствующий о вашем потрясающем стиле', 'Кроссовки', 'Puma', 
     'https://www.lamoda.ru/p/rtlaeg505401/shoes-puma-krossovki/?utm_source=YDirect&utm_medium=cpc&utm_campaign=709827212.RU_SEMNB_WEB_Gallery_Sport_bns_2&utm_content=5749954374&utm_term=205749954374.---autotargeting&adjust_tracker=fk2tk4_56bkkg&adjust_campaign=RU_SEMNB_WEB_Gallery_Sport_bns_2&adjust_adgroup=5749954374&adjust_creative=205749954374.---autotargeting&adjust_ya_click_id=12191341694089428991&yclid=12191341694089428991', 
     r'C:\Users\Tania\Desktop\images_boots\puma RS-X Efekt Perf.jpg', 'мужской'),

    ('Asics KIRSH x Asics Gel-Lyte 5 (Men)', 15762.0, '15 762 руб.', 'Кроссовки выполнены из текстильного материала. Детали: система амортизации GEL обеспечивает превосходное поглощение ударных нагрузок', 'Кроссовки', 'Asics', 
     'https://www.lamoda.ru/p/rtlaer589601/shoes-asics-krossovki/', 
     r'C:\Users\Tania\Desktop\images_boots\Asics KIRSH x Asics Gel-Lyte 5.jpg', 'мужской'),

    ('Demix BITCRAZY KNIT (Men)', 3055.0, '3 055 руб.', 'Кроссовки изготовлены из воздухопроницаемого вязаного текстиля, что обеспечивает оптимальную вентиляцию и комфортный микроклимат в течение дня', 'Кроссовки', 'Demix', 
     'https://www.lamoda.ru/p/mp002xm0db3j/shoes-demix-krossovki/', 
     r'C:\Users\Tania\Desktop\images_boots\demix BITCRAZY KNIT.jpg', 'мужской'),

    ('Converse Chuck Taylor All Star (Men)', 14490.0, '14 490 руб.', 'Классические кеды', 'Кеды', 'Converse', 'url', 'img', 'мужской'),
    ('Vans Old Skool (Men)', 7500.0, '7 500 руб.', 'Скейт-кеды', 'Кеды', 'Vans', 
     'https://www.lamoda.ru/p/rtladk150501/shoes-converse-kedy/', 
     r'C:\Users\Tania\Desktop\images_boots\Converse All Star.jpg', 'мужской'),

    ('Dr. Martens (Men)', 29999.0, '29 999 руб.', 'Ботинки 1460 – первая и самая популярная модель Dr. Martens', 'Ботинки', 'Dr. Martens',
     'https://www.lamoda.ru/p/rtlacq300003/shoes-drmartens-botinki/?utm_source=YDirect&utm_medium=cpc&utm_campaign=117318975.RU_SEMNB_Web_Gallery_SKU%20with%20potential&utm_content=5531119999&utm_term=54092077223.---autotargeting&adjust_tracker=fk2tk4_56bkkg&adjust_campaign=RU_SEMNB_Web_Gallery_SKU%20with%20potential&adjust_adgroup=5531119999&adjust_creative=54092077223.---autotargeting&adjust_ya_click_id=8705016481717420031&yclid=8705016481717420031', 
     r'C:\Users\Tania\Desktop\images_boots\Dr. Martens.jpg', 'мужской'),
    
    ('Salomon OUTCHILL TS WP (Men)', 22000.0, '22 000 руб.', 'Мужские трекинговые ботинки выполнены из износостойкого текстиля', 'Ботинки', 'Salomon', 
     'https://www.lamoda.ru/p/rtlaeu739201/shoes-salomon-botinki-trekingovye/', 
     r'C:\Users\Tania\Desktop\images_boots\salomon OUTCHILL TS WP.jpg', 'мужской'),

    ('Diesel Boots (Men)', 30748.0, '30 748 руб.', 'Надежные сапоги из замши', 'Сапоги', 'Diesel', 
     'https://www.lamoda.ru/p/rtlaen250801/shoes-diesel-sapogi/url', 
     r'C:\Users\Tania\Desktop\images_boots\Diesel.jpg', 'мужской'),

    ('Salamander Moccasins (Men)', 13699.0, '13 699 руб.', 'Удобные классические лоферы', 'Лоферы', 'Salamander', 
     'https://www.lamoda.ru/p/mp002xm084tx/shoes-salamander-mokasiny/', 
     r'C:\Users\Tania\Desktop\images_boots\Moccasins Salamander.jpg', 'мужской'),

    # ЖЕНСКИЕ
    ('Nike Air Force 1 (Women)', 19999.0, '19 999 руб.', 'Низкие кеды Air Force 1 от Nike в лаконичном дизайне — то что нужно для твоего повседневного образа.', 'Кроссовки', 'Nike', 
     'https://www.sportmaster.ru/product/33933150299/?utm_referrer=https%3A%2F%2Fwww.sportmaster.ru%2Fcatalog%2Fbrendy%2Fnike%2Fall%2F%3Ff-ware_line_ishop%3Dware_line_ishop_nike_air_force_1%26utm_referrer%3Dhttps%253A%252F%252Fyandex.ru%252F%26watched%3D2', 'https://images.unsplash.com/photo-1597350584914-55bb62285896?w=300', 'женский'),
    
    ('Gucci Blonde Boots (Women)', 309500.0, '309 500 руб.', 'Кожаные сапоги Blondie', 'Сапоги', 'Gucci', 
     'https://www.tsum.ru/product/6853409-kozhanye-sapogi-blondie-gucci-chernyi/', 
     r'C:\Users\Tania\Desktop\images_boots\gucci ankle boots.jpg', 'женский'),    
    
    ('Valentino Shoes Bowow Pink (Women)', 181000.0, '118 000 руб.', 'Кожаные туфли Bowow 45 Pink', 'Туфли', 'Valentino', 
     'https://www.tsum.ru/product/7029704-kozhanye-tufli-bowow-45-valentino-svetlo-rozovyi/', 
     r'C:\Users\Tania\Desktop\images_boots\valentino shoes.png', 'женский'),
    
    ('Valentino Shoes Rockstud (Women)', 125000.0, '125 000 руб.', 'Кожаные туфли Rockstud 100', 'Туфли', 'Valentino', 
     'https://www.tsum.ru/product/7026716-kozhanye-tufli-rockstud-100-valentino-bezhevyi/', 
     r'C:\Users\Tania\Desktop\images_boots\valentino shoes 2.png', 'женский'),
    
    ('Valentino Shoes Bowow Brown (Women)', 113000.0, '113 000 руб.', 'Кожаные туфли Bowow 45 Brown', 'Туфли', 'Valentino', 
     'https://www.tsum.ru/product/7029112-kozhanye-tufli-bowow-45-valentino-korichnevyi/', 
     r'C:\Users\Tania\Desktop\images_boots\valentino shoes 3.png', 'женский'),
    
    ('Jimmy Choo Stevie (Women)', 144500.0, '144 500 руб.', 'Атласные туфли Stevie 100', 'Туфли', 'Jimmy Choo', 
     'https://www.tsum.ru/product/7093590-atlasnye-tufli-stevie-100-jimmy-choo-fioletovyi/', 
     r'C:\Users\Tania\Desktop\images_boots\Jimmy Choo shoes.png', 'женский'),
    
    ('Bottega Veneta Loafers (Women)', 161000.0, '161 000 руб.', 'Черные лоферы из мягкой кожи', 'Лоферы', 'Bottega Veneta', 
     'https://vipavenue.ru/product/1463629-lofery-koghanye-bottega-veneta/?utm_source=yandex&utm_medium=cpc&utm_term=---autotargeting&utm_campaign=reg0_dynamic_site_brand_poisk&adjust_ya_click_id=15390824404223000575&adjust_campaign=Reg0%20Динамическая%20по%20сайту%20Бренды%20Поиск%20%28reg0_dynamic_site_brand_poisk%29&utm_content=region%3AСингапур%7Cgeoid%3A10105%7Ccid%7C87939385%7Caid%7C1855273604544625770%7Cgid%7C5498428375%7Cph%7C53240101246%7Csrc%7Cyd%7Cyclid%3D15390824404223000575&referrer=reattribution%3D1&etext&yclid=15390824404223000575', 
     r'C:\Users\Tania\Desktop\images_boots\loafers bottega veneta.jpg', 'женский'),
    
    ('Chanel Ballerina (Women)', 73550.0, '73 550 руб.', 'Кожаные балетки Ballerina', 'Балетки', 'Chanel', 
     'https://www.tsum.ru/product/6423737-kozhanye-baletki-ballerina-co-chernyi-id103302447/', 
     r'C:\Users\Tania\Desktop\images_boots\chanel ballerina.png', 'женский'),
    
    ('Maison Margiela Tabi (Women)', 137000.0, '137 000 руб.', 'Текстильные балетки Tabi Jazz', 'Таби', 'Maison Margiela', 
     'https://www.tsum.ru/product/7104316-tekstilnye-baletki-tabi-jazz-maison-margiela-chernyi/?utm_source=yandex&utm_medium=cpc&is_retargeting=true&utm_campaign=cid.702649813_cn.tsum-performance-campaign-all-cat-all-source-new-clients-rf&utm_term=ph.205700116296_kw.---autotargeting&utm_content=dev.desktop_rid.213_gid.5700116296_aid.1898968452183945744_re.205700116296_drf.no_pos.2_postype.premium&af_sub1=ph.205700116296_kw.---autotargeting&af_adset=gid.5700116296_b.1898968452183945744_p.2_coef.35995563_st.search&yclid=7327593555405307903&redirect_source=m_domain', 
     r'C:\Users\Tania\Desktop\images_boots\tabi.png', 'женский'),
    
    ('Valentino Mules (Women)', 104000, '104 000 руб.', 'Элегантные мюли', 'Мюли', 'Valentino', 
     'https://www.tsum.ru/product/7060208-kozhanye-myuli-knotty-60-valentino-temno-korichnevyi/?utm_source=yandex&utm_medium=cpc&is_retargeting=true&utm_campaign=cid.702649813_cn.tsum-performance-campaign-all-cat-all-source-new-clients-rf&utm_term=ph.205700116296_kw.---autotargeting&utm_content=dev.desktop_rid.213_gid.5700116296_aid.1898968452183945744_re.205700116296_drf.no_pos.2_postype.premium&af_sub1=ph.205700116296_kw.---autotargeting&af_adset=gid.5700116296_b.1898968452183945744_p.2_coef.35995563_st.search&yclid=16316545127634960383&redirect_source=m_domain', 
     r'C:\Users\Tania\Desktop\images_boots\mules valentino.png', 'женский'),
    
    ('Gucci Sandals (Women)', 113000.0, '113 000 руб.', 'Сандалии', 'Сандалии', 'Gucci', 
     'https://www.tsum.ru/product/7067017-kombinirovannye-bosonozhki-gucci-sinii/?utm_source=yandex&utm_medium=cpc&is_retargeting=true&utm_campaign=cid.702649813_cn.tsum-performance-campaign-all-cat-all-source-new-clients-rf&utm_term=ph.205700116296_kw.---autotargeting&utm_content=dev.desktop_rid.213_gid.5700116296_aid.1898968452183945744_re.205700116296_drf.no_pos.2_postype.premium&af_sub1=ph.205700116296_kw.---autotargeting&af_adset=gid.5700116296_b.1898968452183945744_p.2_coef.35995563_st.search&yclid=2802904779170250751&redirect_source=m_domain', 
     r'C:\Users\Tania\Desktop\images_boots\gucci sandals.png', 'женский'),
    
    ('Prada Sabo (Women)', 131000.0, '131 000', 'Кожаные сабо', 'Сабо', 'Prada', 
     'https://www.tsum.ru/product/7064148-kozhanye-sabo-prada-chernyi/', 
     r'C:\Users\Tania\Desktop\images_boots\prada sabo.png', 'женский')
]

cursor.executemany('''INSERT INTO shoes 
                      (name, price, price_text, description, shoes_type, brand, url, image_url, gender) 
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', shoes_data)

# --- ИНДИВИДУАЛЬНЫЕ РАЗМЕРЫ ---
size_config = {
    'Nike Air Force 1': [36.5, 37.5, 38, 39],
    'Gucci Blonde Boots': [37, 38, 38.5, 39],
    'Valentino Shoes Bowow Pink': [37],
    'Valentino Shoes Bowow Brown': [37.5, 38, 38.5, 39],
    'Valentino Shoes Rockstud': [40],
    'Jimmy Choo Stevie': [37, 38, 38.5, 39, 39.5, 40]
}

cursor.execute("SELECT id, name, gender FROM shoes")
all_shoes = cursor.fetchall()

stock_data = []
for shoe_id, name, gender in all_shoes:
    sizes = None
    # Ищем, есть ли правило для этой модели
    for key, val in size_config.items():
        if key.lower() in name.lower():
            sizes = val
            break
    
    # Если правил нет, ставим дефолт
    if not sizes:
        sizes = [36, 36.5, 37, 37.5, 38, 38.5, 39, 39.5, 40] if gender == 'женский' else [40, 40.5, 41, 41.5, 42, 42.5, 43, 43.5, 44, 44.5, 45]
        
    for size in sizes:
        stock_data.append((shoe_id, size, 5))

cursor.executemany("INSERT INTO stock (shoe_id, size, quantity) VALUES (?, ?, ?)", stock_data)

conn.commit()
conn.close()

print("База успешно создана с уникальными размерами!")