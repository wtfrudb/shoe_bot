import re

def parse_price(price_text):
    price_text = price_text.lower()
    
    if any(word in price_text for word in ['любой', 'не важно', 'без разницы', 'все равно']):
        return None
    
    numbers = re.findall(r'\d+[\.,]?\d*', price_text)
    if not numbers:
        return None
    
    price = float(numbers[0].replace(',', '.'))
    
    if 'млн' in price_text or 'миллион' in price_text:
        return price
    
    if 'тыс' in price_text:
        return price / 1000
    
    if 'сот' in price_text:
        return price / 1000
    
    if 'до' in price_text and 'млн' in price_text:
        return price
    
    if price > 1000:  
        return price / 1000000
    else:
        return price

def format_price(price_million):
    if price_million >= 1:
        if price_million == int(price_million):
            return f"{int(price_million)} млн ₽"
        else:
            return f"{price_million} млн ₽"
    else:
        return f"{int(price_million * 1000)} тыс. ₽"