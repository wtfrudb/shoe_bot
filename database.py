import sqlite3

DB_PATH = 'shoe_shop.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # ВАЖНОЕ ИСПРАВЛЕНИЕ: Регистрируем собственную функцию "py_lower" внутри SQLite.
    # Теперь база данных сможет идеально переводить в нижний регистр РУССКИЕ буквы, используя возможности Python.
    conn.create_function("py_lower", 1, lambda val: val.lower().strip() if val else "")
    
    return conn

def save_dialog(user_id, user_message, bot_answer):
    conn = get_db_connection()
    conn.execute('''INSERT INTO conversations (user_id, user_message, bot_answer) 
                    VALUES (?, ?, ?)''', (str(user_id), user_message, bot_answer))
    conn.commit()
    conn.close()

def get_available_brands_for_type(shoes_type, gender_text):
    # Приводим к формату бд ("Мужская обувь" -> "мужской")
    gender = "мужской" if "муж" in gender_text.lower() else "женский"
    conn = get_db_connection()
    
    # ИСПРАВЛЕНО: Вместо штатного LOWER() используем нашу функцию py_lower()
    cursor = conn.execute(
        "SELECT DISTINCT brand FROM shoes WHERE py_lower(shoes_type) = py_lower(?) AND gender = ?", 
        (shoes_type, gender)
    )
    brands = [row['brand'] for row in cursor.fetchall()]
    conn.close()
    
    return brands

def search_shoes(shoes_type=None, brand=None, max_price=None, gender=None):
    conn = sqlite3.connect('shoe_shop.db')
    conn.row_factory = sqlite3.Row  # Это позволит обращаться к полям по именам (shoe['id'])
    cur = conn.cursor()
    query = "SELECT id, name, price, price_text, description, shoes_type, brand, url, image_url FROM shoes WHERE 1=1"
    params = []
    
    # 1. Обработка типов обуви (с учетом наших новых кнопок "Показать все")
    if shoes_type:
        if shoes_type.startswith("all_in_"):
            
            cat_name = shoes_type.replace("all_in_", "")
    
            import bot  
            subcategories = bot.CATALOG.get(gender, {}).get(cat_name, [])
            
            # Формируем условие IN (?, ?, ?)
            placeholders = ", ".join(["?"] * len(subcategories))
            query += f" AND LOWER(shoes_type) IN ({placeholders})"
            for sub in subcategories:
                params.append(sub.lower())
        else:
            # Обычный поиск по одной подкатегории
            query += " AND LOWER(shoes_type) = ?"
            params.append(shoes_type.lower())
            
    # 2. Фильтр по бренду
    if brand and brand != "Any" and brand != "Любой":
        query += " AND LOWER(brand) = ?"
        params.append(brand.lower())
        
    # 3. Фильтр по цене
    if max_price is not None and max_price != float('inf'):
        query += " AND price <= ?"
        params.append(max_price)
        
    # 4. Фильтр по полу
    if gender:
        db_gender = "женский" if "жен" in gender.lower() else "мужской"
        query += " AND LOWER(gender) = ?"
        params.append(db_gender)
        
    query += " ORDER BY RANDOM() LIMIT 3"
    cur.execute(query, params)
    shoes = cur.fetchall()
    conn.close()
    return shoes

def get_sizes_for_shoe(shoe_id):
    conn = get_db_connection()
    cursor = conn.execute("SELECT size FROM stock WHERE shoe_id = ? AND quantity > 0", (shoe_id,))
    sizes = [row['size'] for row in cursor.fetchall()]
    conn.close()
    return sizes

def get_shoe_url(shoe_id):
    conn = get_db_connection()
    cursor = conn.execute("SELECT url FROM shoes WHERE id = ?", (shoe_id,))
    row = cursor.fetchone()
    conn.close()
    return row['url'] if row else None