import re
import sqlite3

def parse_price(price_text):
    """
    Вытаскивает из текста пользователя сумму бюджета в рублях.
    Например: 'до 15000', '12000 рублей', 'около 10к' -> возвращает чистый инт.
    """
    price_text = price_text.lower().strip()
    
    # Если пользователю не важна цена
    if any(word in price_text for word in ['любой', 'не важно', 'без разницы', 'все равно', 'любая']):
        return float('inf') # Бесконечный бюджет
    
    # Обработка сокращения 'к' (например, 10к -> 10000)
    if re.search(r'\d+к', price_text):
        price_text = price_text.replace('к', '000')
    if re.search(r'\d+k', price_text):
        price_text = price_text.replace('k', '000')

    # Находим все цифры
    numbers = re.findall(r'\d+', price_text)
    if not numbers:
        return None
    
    price = int(numbers[0])
    
    # Если написали 'тыс' или 'тысяч', а 'к' не сработало
    if 'тыс' in price_text and price < 1000:
        price = price * 1000
        
    return price


def get_shoes_by_filters(shoes_type, brand, max_price):
    """
    Ищет обувь в базе данных shoe_shop.db по типу, бренду и бюджету.
    """
    try:
        conn = sqlite3.connect('shoe_shop.db')
        cursor = conn.cursor()
        
        # Переводим в нижний регистр для надежности сравнения
        shoes_type = shoes_type.lower().strip()
        brand = brand.lower().strip()
        
        # Формируем SQL-запрос в зависимости от того, выбран ли конкретный бренд
        if brand == 'любой' or brand == 'все равно':
            query = "SELECT name, price_text, description, url FROM shoes WHERE LOWER(shoes_type) = ? AND price <= ?"
            params = (shoes_type, max_price)
        else:
            query = "SELECT name, price_text, description, url FROM shoes WHERE LOWER(shoes_type) = ? AND LOWER(brand) = ? AND price <= ?"
            params = (shoes_type, brand, max_price)
            
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return f"К сожалению, в категории '{shoes_type}' под ваш бюджет (до {max_price} руб.) ничего не нашлось. Попробуйте увеличить бюджет или выбрать другой бренд!"
            
        # Формируем красивый текстовый ответ со списком моделей
        result = f"👟 Вот что я подобрал в категории '{shoes_type}' до {max_price} руб.:\n\n"
        for row in rows:
            name, price_str, desc, url = row
            result += f"🔹 **{name}** — {price_str}\n"
            result += f"📝 {desc}\n"
            result += f"🔗 [Ссылка на товар]({url})\n\n"
            
        result += "Какая пара вам понравилась? Можем перейти к оформлению!"
        return result

    except Exception as e:
        return f"Ошибка при поиске в каталоге: {e}"