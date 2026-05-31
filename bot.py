import logging
import sqlite3
import random
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from nlp_utils import process_message, get_intent
from price_utils import parse_price
from telegram.request import HTTPXRequest

TOKEN = "8321615785:AAGZNYwUQyeyWiPeslWq50EDcvvH9n0G4-Y"

# Глобальные константы для брендов
BRANDS = {
    'nike': 'Nike', 'найк': 'Nike', 'найки': 'Nike',
    'adidas': 'Adidas', 'адидас': 'Adidas',
    'puma': 'Puma', 'пума': 'Puma',
    'reebok': 'Reebok', 'рибок': 'Reebok', 'рибук': 'Reebok'
}

# ТРЁХУРОВНЕВЫЙ КАТАЛОГ: Пол -> Общая категория -> Подкатегория
CATALOG = {
    "Мужская обувь": {
        "Кроссовки и кеды": ["Кроссовки", "Кеды", "Слипоны"],
        "Туфли и лоферы": ["Туфли", "Лоферы", "Мокасины"],
        "Сапоги и ботинки": ["Ботинки", "Казаки"],
        "Сандалии и открытая": ["Сандалии"]
    },
    "Женская обувь": {
        "Кроссовки и кеды": ["Кроссовки", "Кеды", "Слипоны"],
        "Туфли и балетки": ["Туфли", "Лоферы", "Мокасины", "Балетки", "Таби"],
        "Сапоги и ботинки": ["Сапоги", "Ботильоны", "Ботинки", "Казаки"],
        "Босоножки и сандалии": ["Босоножки", "Сандалии", "Сабо", "Мюли"]
    }
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- ФУНКЦИИ ГЕНЕРАЦИИ КНОПОК ---

def get_start_keyboard():
    return ReplyKeyboardMarkup([['👟 Подобрать обувь', '💬 Просто поболтать']], resize_keyboard=True)

def get_gender_keyboard():
    return ReplyKeyboardMarkup([
        ['Мужская обувь', 'Женская обувь'],
        ['🏠 В главное меню']
    ], resize_keyboard=True)

def get_categories_keyboard(gender):
    categories = list(CATALOG.get(gender, {}).keys())
    keyboard = []
    row = []
    for cat in categories:
        row.append(cat)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append(['⬅️ Назад', '🏠 В главное меню'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_subcategories_keyboard(gender, category):
    subcategories = CATALOG.get(gender, {}).get(category, [])
    keyboard = []
    row = []
    for sub in subcategories:
        row.append(sub)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append(['⬅️ Назад', '🏠 В главное меню'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_brands_keyboard(available_brands):
    keyboard = []
    row = []
    for brand in available_brands:
        row.append(brand.capitalize())
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append(['Любой бренд'])
    keyboard.append(['⬅️ Назад', '🏠 В главное меню'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_price_keyboard():
    return ReplyKeyboardMarkup([['Любой бюджет'], ['⬅️ Назад', '🏠 В главное меню']], resize_keyboard=True)

def get_rejection_keyboard():
    return ReplyKeyboardMarkup([
        ['🔄 Изменить бренд', '🗂 Другая категория'],
        ['⬅️ Назад (Бюджет)', '🏠 В главное меню']
    ], resize_keyboard=True)

def get_failure_keyboard():
    return ReplyKeyboardMarkup([['⬅️ Назад'], ['🏠 В главное меню']], resize_keyboard=True)


# --- РАБОТА С БД ---

def save_dialog(user_id, user_msg, bot_msg):
    conn = sqlite3.connect('shoe_shop.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO conversations (user_id, user_message, bot_answer) VALUES (?, ?, ?)", 
                (str(user_id), user_msg, bot_msg))
    conn.commit()
    conn.close()

def search_shoes(shoes_type=None, brand=None, max_price=None, gender=None):
    conn = sqlite3.connect('shoe_shop.db')
    cur = conn.cursor()
    query = "SELECT name, price, price_text, description, shoes_type, brand, url FROM shoes WHERE 1=1"
    params = []
    
    if shoes_type:
        query += " AND LOWER(shoes_type) = ?"
        params.append(shoes_type.lower())
    if brand and brand != "Любой":
        query += " AND LOWER(brand) = ?"
        params.append(brand.lower())
    if max_price is not None and max_price != float('inf'):
        query += " AND price <= ?"
        params.append(max_price)
        
    if gender:
        # Транслируем "Женская обувь" -> "женский", "Мужская обувь" -> "мужской"
        db_gender = "женский" if "жен" in gender.lower() else "мужской"
        query += " AND LOWER(gender) = ?"
        params.append(db_gender)
        
    query += " ORDER BY RANDOM() LIMIT 3"
    cur.execute(query, params)
    shoes = cur.fetchall()
    conn.close()
    return shoes

def get_available_brands_for_type(shoes_type, gender=None):
    conn = sqlite3.connect('shoe_shop.db')
    cur = conn.cursor()
    
    if gender:
        # Транслируем "Женская обувь" -> "женский", "Мужская обувь" -> "мужской"
        db_gender = "женский" if "жен" in gender.lower() else "мужской"
        cur.execute(
            "SELECT DISTINCT brand FROM shoes WHERE LOWER(shoes_type) = ? AND LOWER(gender) = ?", 
            (shoes_type.lower(), db_gender)
        )
    else:
        cur.execute("SELECT DISTINCT brand FROM shoes WHERE LOWER(shoes_type) = ?", (shoes_type.lower(),))
        
    brands = [row[0] for row in cur.fetchall() if row[0]]
    conn.close()
    return brands

def format_shoes_list(shoes_list):
    if not shoes_list:
        return None
    result = "Нашел для Вас отличные варианты: 🛍\n\n"
    for item in shoes_list:
        result += f"• **{item[0]}**\n  Бренд: {item[5]}\n  Стоимость: {item[2]}\n  Описание: {item[3]}\n  Ссылка: {item[6]}\n\n"
    return result


# --- ОСНОВНАЯ ЛОГИКА ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    response = "Привет! Я бот-помощник магазина обуви. 👟\n\nЧем вы хотите заняться? Выберите действие на клавиатуре ниже:"
    await update.message.reply_text(response, reply_markup=get_start_keyboard())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = context.user_data.pop('voice_text_override', update.message.text)
    user_id = update.effective_user.id
    user_text_lower = user_text.lower()
    
    if 'msg_count' not in context.user_data:
        context.user_data['msg_count'] = 0
        context.user_data['ad_triggered'] = False

    # СТРОГИЙ ПЕРЕХВАТ КНОПКИ ГЛАВНОГО МЕНЮ
    if "в главное меню" in user_text_lower or user_text_lower == "/start":
        context.user_data.clear()
        response = "Вы вернулись в главное меню. Чем займемся?"
        await update.message.reply_text(response, reply_markup=get_start_keyboard())
        save_dialog(user_id, user_text, response)
        return

    # УМНАЯ КНОПКА НАЗАД (Трёхуровневая глубина)
    if user_text_lower == "назад" or "⬅️ назад" in user_text_lower or user_text_lower == "назад (бюджет)":
        if context.user_data.get('awaiting_category'):
            context.user_data['awaiting_category'] = False
            context.user_data['awaiting_gender'] = True
            response = "Хорошо, давайте вернемся к выбору ассортимента. Что ищем?"
            await update.message.reply_text(response, reply_markup=get_gender_keyboard())
            return
            
        elif context.user_data.get('awaiting_subcategory'):
            context.user_data['awaiting_subcategory'] = False
            context.user_data['awaiting_category'] = True
            gender = context.user_data.get('current_gender')
            response = f"Возвращаемся к общим категориям для раздела '{gender}':"
            await update.message.reply_text(response, reply_markup=get_categories_keyboard(gender))
            return
            
        elif context.user_data.get('awaiting_brand'):
            context.user_data['awaiting_brand'] = False
            context.user_data['awaiting_subcategory'] = True
            gender = context.user_data.get('current_gender')
            category = context.user_data.get('current_category')
            response = f"Возвращаемся к подкатегориям для '{category}':"
            await update.message.reply_text(response, reply_markup=get_subcategories_keyboard(gender, category))
            return
            
        elif context.user_data.get('awaiting_price') or context.user_data.get('waiting_for_failure'):
            context.user_data['awaiting_price'] = False
            context.user_data['waiting_for_failure'] = False
            context.user_data['awaiting_brand'] = True
            shoes_type = context.user_data.get('shoes_type', 'кроссовки')
            gender = context.user_data.get('current_gender')
            available_brands = get_available_brands_for_type(shoes_type, gender)
            response = f"Возвращаемся к выбору бренда для '{shoes_type}':"
            await update.message.reply_text(response, reply_markup=get_brands_keyboard(available_brands))
            return
            
        elif context.user_data.get('awaiting_rejection_choice'):
            context.user_data['awaiting_rejection_choice'] = False
            context.user_data['awaiting_price'] = True
            brand = context.user_data.get('brand', 'Любой')
            response = f"Хорошо, скорректируем бюджет. На какой максимальный бюджет в рублях рассчитываете (для бренда {brand})?"
            await update.message.reply_text(response, reply_markup=get_price_keyboard())
            return

    # Отказ в режиме болталки
    rejection_words = ["не нужно", "не нужна", "не хочу", "ничего", "не интересует", "отмена", "отстань", "хватить"]
    if any(word in user_text_lower for word in rejection_words) and not context.user_data.get('waiting_for_shoes_answer') and not context.user_data.get('awaiting_rejection_choice'):
        context.user_data.clear()
        response = "Понял-принял, закрыли тему покупок. 😊 Как вообще дела?"
        await update.message.reply_text(response, reply_markup=get_start_keyboard())
        save_dialog(user_id, user_text, response)
        return

    # МАРШРУТИЗАЦИЯ ТЕКУЩИХ ШАГОВ
    if context.user_data.get('awaiting_gender'):
        await handle_gender_selection(update, context, user_text)
        return
    if context.user_data.get('awaiting_category'):
        await handle_category_selection(update, context, user_text)
        return
    if context.user_data.get('awaiting_subcategory'):
        await handle_subcategory_selection(update, context, user_text)
        return
    if context.user_data.get('awaiting_brand'):
        await handle_brand(update, context, user_text)
        return
    if context.user_data.get('awaiting_price'):
        await handle_price(update, context, user_text)
        return
    if context.user_data.get('waiting_for_shoes_answer'):
        await handle_answer_after_shoes(update, context, user_text)
        return
    if context.user_data.get('awaiting_rejection_choice'):
        await handle_rejection_choice(update, context, user_text)
        return
    if context.user_data.get('waiting_for_failure'):
        await update.message.reply_text("Пожалуйста, нажмите кнопку '⬅️ Назад', чтобы изменить параметры, или '🏠 В главное меню'.", reply_markup=get_failure_keyboard())
        return

    # ОБРАБОТКА СТАРТОВЫХ КНОПОК
    if "подобрать обувь" in user_text_lower or "купить обувь" in user_text_lower or "подбор" in user_text_lower:
        response = "О, подбор обуви — это по моей части! 👟 Какой ассортимент Вас интересует?"
        context.user_data['awaiting_gender'] = True
        await update.message.reply_text(response, reply_markup=get_gender_keyboard())
        save_dialog(user_id, user_text, response)
        return

    if "просто поболтать" in user_text_lower:
        response = "С удовольствием поболтаю! Расскажи, как дела?"
        await update.message.reply_text(response, reply_markup=ReplyKeyboardRemove()) 
        save_dialog(user_id, user_text, response)
        return

    # Болталка
    context.user_data['msg_count'] += 1
    should_advertise = (context.user_data['msg_count'] == 3 and not context.user_data['ad_triggered'])
    if should_advertise:
        context.user_data['ad_triggered'] = True

    intent, auto_response = process_message(user_text, allow_ad=should_advertise)
    
    if intent == "buy_shoes":
        from nlp_utils import check_specific_shoe_request
        detected_sub = check_specific_shoe_request(user_text)
        
        if detected_sub:
            context.user_data['shoes_type'] = detected_sub
            gender = context.user_data.get('current_gender')
            available_brands = get_available_brands_for_type(detected_sub, gender)
            
            if available_brands:
                context.user_data['awaiting_gender'] = False
                context.user_data['awaiting_category'] = False
                context.user_data['awaiting_subcategory'] = False
                context.user_data['awaiting_brand'] = True
                
                response = f"Понял, ищем {detected_sub.lower()}. Какому бренду отдаете предпочтение? (Я вывел только те, что сейчас есть в наличии):"
                await update.message.reply_text(response, reply_markup=get_brands_keyboard(available_brands))
                save_dialog(user_id, user_text, response)
                return

        response = auto_response if should_advertise else "О, подбор обуви — это по моей части! 👟 Выберите интересующий Вас ассортимент:"
        context.user_data['awaiting_gender'] = True
        await update.message.reply_text(response, reply_markup=get_gender_keyboard())
        
    elif should_advertise:
        response = auto_response
        context.user_data['awaiting_gender'] = True 
        await update.message.reply_text(response, reply_markup=get_gender_keyboard())
    else:
        response = auto_response if auto_response else "Интересно! Расскажи подробнее?"
        await update.message.reply_text(response)

    save_dialog(user_id, user_text, response)


# --- ПОШАГОВЫЕ ОБРАБОТЧИКИ ---

async def handle_gender_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str):
    chosen_gender = None
    for gen in CATALOG.keys():
        if gen.lower() in user_text.lower():
            chosen_gender = gen
            break
            
    if chosen_gender:
        context.user_data['current_gender'] = chosen_gender
        context.user_data['awaiting_gender'] = False
        context.user_data['awaiting_category'] = True
        response = f"Отлично! Раздел: '{chosen_gender}'. Выберите общую категорию обуви:"
        await update.message.reply_text(response, reply_markup=get_categories_keyboard(chosen_gender))
        save_dialog(update.effective_user.id, user_text, response)
        return
        
    await update.message.reply_text("Пожалуйста, выберите раздел на кнопках.", reply_markup=get_gender_keyboard())

async def handle_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str):
    gender = context.user_data.get('current_gender')
    chosen_category = None
    for cat in CATALOG.get(gender, {}).keys():
        if cat.lower() in user_text.lower():
            chosen_category = cat
            break
            
    if chosen_category:
        context.user_data['current_category'] = chosen_category
        context.user_data['awaiting_category'] = False
        context.user_data['awaiting_subcategory'] = True
        response = f"Категория '{chosen_category}'. Теперь уточните тип обуви, который вы ищете:"
        await update.message.reply_text(response, reply_markup=get_subcategories_keyboard(gender, chosen_category))
        save_dialog(update.effective_user.id, user_text, response)
        return
        
    await update.message.reply_text("Пожалуйста, выберите общую категорию из списка.", reply_markup=get_categories_keyboard(gender))

async def handle_subcategory_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str):
    gender = context.user_data.get('current_gender')
    category = context.user_data.get('current_category')
    subcategories = CATALOG.get(gender, {}).get(category, [])
    
    chosen_sub = None
    for sub in subcategories:
        if sub.lower() in user_text.lower():
            chosen_sub = sub
            break
            
    if chosen_sub:
        context.user_data['shoes_type'] = chosen_sub 
        available_brands = get_available_brands_for_type(chosen_sub, gender)
        
        if not available_brands:
            response = f"К сожалению, моделей '{chosen_sub}' для раздела {gender} сейчас нет в базе. Выберите другой тип:"
            await update.message.reply_text(response, reply_markup=get_subcategories_keyboard(gender, category))
            return
            
        context.user_data['awaiting_subcategory'] = False
        context.user_data['awaiting_brand'] = True
        response = f"Ищем {chosen_sub.lower()}. Какой бренд предпочитаете? (Выведены доступные в базе):"
        await update.message.reply_text(response, reply_markup=get_brands_keyboard(available_brands))
        save_dialog(update.effective_user.id, user_text, response)
        return
        
    await update.message.reply_text("Пожалуйста, выберите тип обуви на кнопках.", reply_markup=get_subcategories_keyboard(gender, category))

async def handle_brand(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str):
    user_text_lower = user_text.lower()
    brand = None
    
    if 'любой' in user_text_lower or 'все равно' in user_text_lower or 'любые' in user_text_lower:
        brand = "Любой"
    else:
        for key, value in BRANDS.items():
            if key in user_text_lower:
                brand = value
                break
                
    if brand:
        context.user_data['brand'] = brand
        context.user_data['awaiting_brand'] = False
        context.user_data['awaiting_price'] = True
        response = f"Отлично, бренд: {brand}. На какой максимальный бюджет в рублях рассчитываете?\nВведите сумму текстом (например: 15000, до 12000) или нажмите кнопку:"
        await update.message.reply_text(response, reply_markup=get_price_keyboard())
        save_dialog(update.effective_user.id, user_text, response)
        return
        
    shoes_type = context.user_data.get('shoes_type', 'кроссовки')
    gender = context.user_data.get('current_gender')
    available_brands = get_available_brands_for_type(shoes_type, gender)
    response = "Не совсем понял бренд. Пожалуйста, выберите бренд из списка на кнопках или напишите 'Любой бренд'."
    await update.message.reply_text(response, reply_markup=get_brands_keyboard(available_brands))
    save_dialog(update.effective_user.id, user_text, response)
    return

async def handle_price(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str):
    user_text_lower = user_text.lower()
    
    if 'любой' in user_text_lower or 'все равно' in user_text_lower:
        max_price = float('inf')
    else:
        max_price = parse_price(user_text)
    
    if max_price is None:
        await update.message.reply_text(
            "Не совсем понял сумму бюджета. Напишите, пожалуйста, числом (например, 15000) или нажмите 'Любой бюджет'.",
            reply_markup=get_price_keyboard()
        )
        return
        
    context.user_data['max_price'] = max_price
    context.user_data['awaiting_price'] = False
    
    brand_filter = context.user_data.get('brand')
    if brand_filter == "Любой":
        brand_filter = None
        
    gender_filter = context.user_data.get('current_gender')
    shoes_list = search_shoes(context.user_data.get('shoes_type'), brand_filter, max_price, gender_filter)
    
    if shoes_list:
        response = format_shoes_list(shoes_list)
        response += "Вам нравится какой-нибудь вариант?"
        context.user_data['waiting_for_shoes_answer'] = True 
        final_keyboard = [['Да, супер! 🎉', 'Нет, не нравится ⬅️']]
        await update.message.reply_text(response, reply_markup=ReplyKeyboardMarkup(final_keyboard, resize_keyboard=True))
    else:
        response = "К сожалению, не нашёл обуви по Вашим критериям в базе. 😔\n\nВы можете вернуться назад и изменить бюджет или бренд!"
        context.user_data['waiting_for_failure'] = True
        await update.message.reply_text(response, reply_markup=get_failure_keyboard())
        
    save_dialog(update.effective_user.id, user_text, response)

def get_user_intent(text):
    text = text.lower().strip()
    shoe_categories = [
        "балетки", "босоножки", "ботильоны", "ботинки", "казаки", 
        "кроссовки", "кеды", "лоферы", "мокасины", "сабо", 
        "мюли", "сандалии", "сандали", "сапоги", "слипоны", "таби", "туфли"
    ]
    has_category = any(category in text for category in shoe_categories)
    change_words = ["другой", "другие", "хочу", "купить", "искать", "выбрать", "поменяем", "всё-таки"]
    
    if has_category and (any(word in text for word in change_words) or len(text.split()) <= 2):
        return "change_category"
    elif any(word in text for word in ["нет", "не нравится", "не то", "отмена", "другое", "заново"]):
        return "decline"
    elif any(word in text for word in ["да", "нравится", "оформляем", "беру", "отлично", "хорошо", "подходит"]):
        return "approve"
    return "unknown"

def extract_category(text):
    text = text.lower()
    shoe_categories = [
        "балетки", "босоножки", "ботильоны", "ботинки", "казаки", 
        "кроссовки", "кеды", "лоферы", "мокасины", "сабо", 
        "мюли", "сандалии", "сапоги", "слипоны", "таби", "туфли"
    ]
    for category in shoe_categories:
        if category in text or (category[:-1] in text if len(category) > 4 else False): 
            return category
    return "обувь"

async def handle_answer_after_shoes(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str):
    user_text_lower = user_text.lower()
    intent = get_user_intent(user_text)
    
    if intent == "change_category":
        new_shoe = extract_category(user_text) 
        gender = context.user_data.get('current_gender')
        available_brands = get_available_brands_for_type(new_shoe, gender)
        
        if not available_brands:
            response = f"К сожалению, моделей из категории '{new_shoe}' для раздела {gender} сейчас нет в наличии. 😔 Пожалуйста, выберите что-то другое."
            await update.message.reply_text(response)
            return

        context.user_data['shoes_type'] = new_shoe          
        context.user_data['waiting_for_shoes_answer'] = False 
        context.user_data['awaiting_brand'] = True            
        
        response = f"Понял, переключаемся! Ищем {new_shoe.lower()}. Какой бренд предпочитаете? (Выведены доступные в базе):"
        await update.message.reply_text(response, reply_markup=get_brands_keyboard(available_brands))
        save_dialog(update.effective_user.id, user_text, response)
        return

    elif intent == "approve" or "да" in user_text_lower or "супер" in user_text_lower:
        response = "Замечательно! 🎉 Вы сделали отличный выбор. Для оформления заказа перейдите по ссылке товара.\n\nЧем ещё я могу Вам помочь?"
        context.user_data.clear()  
        await update.message.reply_text(response, reply_markup=get_start_keyboard())
        
    elif intent == "decline" or "нет" in user_text_lower or "не нравится" in user_text_lower:
        context.user_data['waiting_for_shoes_answer'] = False
        context.user_data['awaiting_rejection_choice'] = True
        shoes_type = context.user_data.get('shoes_type', 'обувь')
        response = f"Принял! Модели из категории '{shoes_type}' не подошли. Что мы изменим, чтобы найти идеальную пару?"
        await update.message.reply_text(response, reply_markup=get_rejection_keyboard())
        
    else:
        await update.message.reply_text(
            "Пожалуйста, ответьте: 'Да, супер! 🎉' или 'Нет, не нравится ⬅️', либо скажите, какую другую обувь вы хотите найти.", 
            reply_markup=ReplyKeyboardMarkup([['Да, супер! 🎉', 'Нет, не нравится ⬅️']], resize_keyboard=True)
        )
        return
        
    save_dialog(update.effective_user.id, user_text, response)

async def handle_rejection_choice(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str):
    user_text_lower = user_text.lower()
    
    if "бренд" in user_text_lower or "изменить бренд" in user_text_lower:
        context.user_data['awaiting_rejection_choice'] = False
        context.user_data['awaiting_brand'] = True
        shoes_type = context.user_data.get('shoes_type', 'кроссовки')
        gender = context.user_data.get('current_gender')
        available_brands = get_available_brands_for_type(shoes_type, gender)
        response = f"Давайте выберем другой бренд именно для подкатегории '{shoes_type}':"
        await update.message.reply_text(response, reply_markup=get_brands_keyboard(available_brands))
        save_dialog(update.effective_user.id, user_text, response)
        return
        
    elif "категория" in user_text_lower or "другая категория" in user_text_lower:
        context.user_data['awaiting_rejection_choice'] = False
        context.user_data['awaiting_gender'] = True
        response = "Хорошо, давайте начнем подбор с выбора ассортимента. Что ищем?"
        await update.message.reply_text(response, reply_markup=get_gender_keyboard())
        save_dialog(update.effective_user.id, user_text, response)
        return

    await update.message.reply_text("Пожалуйста, выберите действие на кнопках: '🔄 Изменить бренд' или '🗂 Другая категория'.", reply_markup=get_rejection_keyboard())

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from voice_utils import transcribe_voice
    user_id = update.effective_user.id
    voice = update.message.voice
    await update.message.reply_text("Распознаю голос, подождите, пожалуйста...")
    
    voice_dir = "temp_voice"
    if not os.path.exists(voice_dir):
        os.makedirs(voice_dir)
        
    ogg_path = os.path.join(voice_dir, f"voice_{user_id}_{voice.file_unique_id}.ogg")
    try:
        file = await context.bot.get_file(voice.file_id)
        await file.download_to_drive(ogg_path)
        transcribed_text = transcribe_voice(ogg_path)
        
        if not transcribed_text or "Не удалось" in transcribed_text or "Ошибка" in transcribed_text:
            await update.message.reply_text("Не удалось распознать речь. Попробуйте написать текстом или сказать чётче.")
            return
            
        await update.message.reply_text(f"🎤 Вы сказали: {transcribed_text}")
        context.user_data['voice_text_override'] = transcribed_text
        await handle_message(update, context)
    finally:
        if os.path.exists(ogg_path):
            try: os.remove(ogg_path)
            except: pass

def main():
    # Увеличиваем тайм-ауты подключения и чтения до 30 секунд (по умолчанию там около 5)
    request_config = HTTPXRequest(
        proxy=None,
        connect_timeout=30.0,
        read_timeout=30.0
    )
    
    # Собираем приложение с обновленными настройками сети
    app = Application.builder().token(TOKEN).request(request_config).build()    
    
    # Добавляем стандартный обработчик сетевых ошибок, чтобы бот не "молчал" при сбоях
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error(msg="Исключение при обработке обновления:", exc_info=context.error)
        # Если ошибка случилась во время диалога с пользователем, аккуратно сообщим ему
        if isinstance(update, Update) and update.message:
            await update.message.reply_text(
                "Ой, что-то сервер Telegram долго отвечает... 🙈 Пожалуйста, повтори команду еще раз!"
            )

    app.add_error_handler(error_handler)
    
    # Твои стандартные хэндлеры
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    print("🚀 Обновленный трехструктурный ИИ-Бот успешно запущен!")
    app.run_polling()

if __name__ == '__main__':
    main()