import sqlite3

DB_PATH = 'shoe_shop.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Регистрируем собственную функцию "py_lower" внутри SQLite для работы с кириллицей.
    conn.create_function("py_lower", 1, lambda val: val.lower().strip() if val else "")
    
    return conn

def save_dialog(user_id, user_message, bot_answer):
    conn = get_db_connection()
    conn.execute('''INSERT INTO conversations (user_id, user_message, bot_answer) 
                    VALUES (?, ?, ?)''', (str(user_id), user_message, bot_answer))
    conn.commit()
    conn.close()

def get_available_brands_for_type(shoes_type, gender_text):
    gender = "мужской" if "муж" in gender_text.lower() else "женский"
    conn = get_db_connection()
    
    cursor = conn.execute(
        "SELECT DISTINCT brand FROM shoes WHERE py_lower(shoes_type) = py_lower(?) AND gender = ?", 
        (shoes_type, gender)
    )
    brands = [row['brand'] for row in cursor.fetchall()]
    conn.close()
    
    return brands

def search_shoes(shoes_type, brand_filter, max_price, gender_text):
    gender = "мужской" if "муж" in gender_text.lower() else "женский"
    conn = get_db_connection()
    
    params = []
    
    # РЕАЛИЗАЦИЯ ЗАДАНИЙ 1 и 2: Поддержка списков типов обуви для сквозного поиска
    if isinstance(shoes_type, list):
        # Формируем плейсхолдеры py_lower(?), py_lower(?) для SQL оператора IN
        placeholders = ', '.join(['py_lower(?)'] * len(shoes_type))
        query = (
            f"SELECT id, name, price, price_text, description, shoes_type, brand, url, image_url, gender "
            f"FROM shoes WHERE py_lower(shoes_type) IN ({placeholders}) AND gender = ?"
        )
        for t in shoes_type:
            params.append(t)
    else:
        # Стандартный поиск по одной конкретной подкатегории
        query = (
            "SELECT id, name, price, price_text, description, shoes_type, brand, url, image_url, gender "
            "FROM shoes WHERE py_lower(shoes_type) = py_lower(?) AND gender = ?"
        )
        params.append(shoes_type)
        
    params.append(gender)
    
    if brand_filter and brand_filter != 'Any':
        query += " AND py_lower(brand) = py_lower(?)"
        params.append(brand_filter)
        
    if max_price and max_price != float('inf'):
        query += " AND price <= ?"
        params.append(max_price)
        
    cursor = conn.execute(query, params)
    shoes = [dict(row) for row in cursor.fetchall()]
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