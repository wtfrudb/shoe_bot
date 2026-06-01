import logging
import sqlite3
import os
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from nlp_utils import process_message
from price_utils import parse_price
from telegram.request import HTTPXRequest

TOKEN = "8321615785:AAGZNYwUQyeyWiPeslWq50EDcvvH9n0G4-Y"

# Глобальные константы для брендов
BRANDS = {
    'nike': 'Nike', 'adidas': 'Adidas', 'puma': 'Puma', 'reebok': 'Reebok'
}

# ТРЁХУРОВНЕВЫЙ КАТАЛОГ
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

# --- ПОСТОЯННАЯ КЛАВИАТУРА ВНИЗУ ---
def get_main_keyboard():
    return ReplyKeyboardMarkup([['🏠 В главное меню']], resize_keyboard=True)

# --- ГЕНЕРАЦИЯ ИНЛАЙН-КНОПОК ---

def get_start_inline():
    keyboard = [
        [
            # ИСПРАВЛЕНО: callback_data теперь совпадает с тем, что ждет обработчик
            InlineKeyboardButton("👟 Подобрать обувь", callback_data="start_selection"),
            InlineKeyboardButton("💬 Просто поболтать", callback_data="start_chat")
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

# --- ГЕНЕРАЦИЯ ИНЛАЙН-КНОПОК (ПОД СООБЩЕНИЯМИ) ---

def get_gender_inline():
    keyboard = [
        [InlineKeyboardButton("👨 Мужская обувь", callback_data="gender_male"),
         InlineKeyboardButton("👩 Женская обувь", callback_data="gender_female")],
        [InlineKeyboardButton("🏠 В главное меню", callback_data="menu_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_categories_inline(gender):
    categories = list(CATALOG.get(gender, {}).keys())
    keyboard = []
    row = []
    for cat in categories:
        row.append(InlineKeyboardButton(cat, callback_data=f"cat_{cat}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_gender"),
                     InlineKeyboardButton("🏠 В главное меню", callback_data="menu_main")])
    return InlineKeyboardMarkup(keyboard)

def get_subcategories_inline(gender, category):
    subcategories = CATALOG.get(gender, {}).get(category, [])
    keyboard = []
    row = []
    for sub in subcategories:
        row.append(InlineKeyboardButton(sub, callback_data=f"sub_{sub}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_cat"),
                     InlineKeyboardButton("🏠 В главное меню", callback_data="menu_main")])
    return InlineKeyboardMarkup(keyboard)

def get_brands_inline(available_brands):
    keyboard = []
    row = []
    for brand in available_brands:
        row.append(InlineKeyboardButton(brand.capitalize(), callback_data=f"brand_{brand}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("✨ Любой бренд", callback_data="brand_Any")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_sub"),
                     InlineKeyboardButton("🏠 В главное меню", callback_data="menu_main")])
    return InlineKeyboardMarkup(keyboard)

def get_price_inline():
    keyboard = [
        [InlineKeyboardButton("💰 Любой бюджет", callback_data="price_any")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_brand"),
         InlineKeyboardButton("🏠 В главное меню", callback_data="menu_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_rejection_inline():
    keyboard = [
        [InlineKeyboardButton("🔄 Изменить бренд", callback_data="reject_brand"),
         InlineKeyboardButton("💰 Изменить бюджет", callback_data="reject_price")], 
        [InlineKeyboardButton("🗂 Другая категория", callback_data="reject_cat")],
        [InlineKeyboardButton("🏠 В главное меню", callback_data="menu_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_failure_inline():
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад к бренду", callback_data="back_to_brand"),
         InlineKeyboardButton("💰 Изменить бюджет", callback_data="reject_price")],
        [InlineKeyboardButton("🏠 В главное меню", callback_data="menu_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


# --- ФУНКЦИИ РАБОТЫ С БД ---

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
    if brand and brand != "Any" and brand != "Любой":
        query += " AND LOWER(brand) = ?"
        params.append(brand.lower())
    if max_price is not None and max_price != float('inf'):
        query += " AND price <= ?"
        params.append(max_price)
        
    if gender:
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
        db_gender = "женский" if "жен" in gender.lower() else "мужской"
        cur.execute("SELECT DISTINCT brand FROM shoes WHERE LOWER(shoes_type) = ? AND LOWER(gender) = ?", (shoes_type.lower(), db_gender))
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
        result += f"• {item[0]}\n  Бренд: {item[5]}\n  Стоимость: {item[2]}\n  Описание: {item[3]}\n  Ссылка: {item[6]}\n\n"
    return result


# --- ОБРАБОТКА СТАРТА И ОБЫЧНОГО ТЕКСТА ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    # ИСПРАВЛЕНО: удаляем старую клавиатуру при старте
    await update.message.reply_text("Запускаю меню...", reply_markup=ReplyKeyboardRemove())
    response = "Привет! Я бот-помощник магазина обуви. 👟\n\nЧем вы хотите заняться? Выберите действие ниже:"
    await update.message.reply_text(response, reply_markup=get_start_inline())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = context.user_data.pop('voice_text_override', update.message.text)
    user_id = update.effective_user.id
    user_text_lower = user_text.lower().strip()

    from telegram import ReplyKeyboardRemove

    # 1. Умный счетчик сообщений и определение темы
    context.user_data['msg_count'] = context.user_data.get('msg_count', 0) + 1
    msg_count = context.user_data['msg_count']
    current_topic = context.user_data.get('last_topic', 'general')
    
    # Извлекаем последнее сообщение бота для памяти
    last_bot_msg = context.user_data.get('last_bot_message', '')

    # Определение флага показа рекламы
    if any(word in user_text_lower for word in ["нет", "не хочу", "не надо", "хватит"]):
        context.user_data['msg_count'] = -5 
        should_show_ad = False
    else:
        if (msg_count >= 4 and current_topic == 'sports') or (msg_count >= 6):
            should_show_ad = True
            context.user_data['msg_count'] = 0  
        else:
            should_show_ad = False

    # 2. БЛОК 0: Системные команды
    if "в главное меню" in user_text_lower or user_text_lower == "/start":
        context.user_data.clear()
        response = "Вы вернулись в главное меню. Чем займемся?"
        await update.message.reply_text("Очищаю меню...", reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text(response, reply_markup=get_start_inline())
        save_dialog(user_id, user_text, response)
        return

    # 3. БЛОК 1: Техническое состояние (ожидание цены)
    if context.user_data.get('awaiting_price_text'):
        max_price = parse_price(user_text)
        if max_price is None:
            await update.message.reply_text("Не понял сумму. Введите числом (напр. 15000).", reply_markup=get_main_keyboard())
            return
        context.user_data['max_price'] = max_price
        context.user_data['awaiting_price_text'] = False
        await process_final_search(update.message, context)
        return

    # 4. БЛОК 2: Интеллектуальный анализ с ПЕРЕДАЧЕЙ ИСТОРИИ (last_bot_msg)
    intent, response = process_message(
        user_text, 
        allow_ad=should_show_ad, 
        topic=current_topic, 
        last_bot_msg=last_bot_msg
    )

    # Логика перехода к покупке
    buying_phrases = ["хочу купить", "купить обувь", "купить кроссовки", "подбор обуви", "выбрать обувь"]
    if intent == "buy_shoes" or any(phrase in user_text_lower for phrase in buying_phrases):
        context.user_data.clear()
        await update.message.reply_text("Перехожу к подбору...", reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text("О, подбор обуви — это по моей части! 👟 Какой ассортимент Вас интересует?", reply_markup=get_gender_inline())
        save_dialog(user_id, user_text, "Начал подбор обуви")
        return

    # 5. Обновление контекста темы и ЗАПОМИНАНИЕ ОТВЕТА
    if response:
        r = response.lower()
        if any(w in r for w in ["спорт", "волейбол", "футбол", "бег", "тренировка"]):
            context.user_data['last_topic'] = 'sports'
        elif any(w in r for w in ["кино", "фильм", "сериал", "книга", "аниме"]):
            context.user_data['last_topic'] = 'movies'
        
        # Сохраняем ответ, чтобы в следующий раз бот знал, что он уже сказал
        context.user_data['last_bot_message'] = response

    # 6. БЛОК 4: Ответ пользователю
    if response:
        await update.message.reply_text(response, reply_markup=get_main_keyboard())
        save_dialog(user_id, user_text, response)
        return

    # 7. БЛОК 5: Заглушка
    await update.message.reply_text("Интересно, расскажи подробнее!", reply_markup=get_main_keyboard())
    save_dialog(user_id, user_text, "Не понял")

async def handle_inline_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data

    if data == "menu_main":
        context.user_data.clear()
        response = "Вы вернулись в главное меню. Чем займемся?"
        # Убираем старую клавиатуру и не ставим новую (ReplyKeyboardRemove)
        await query.message.reply_text(response, reply_markup=ReplyKeyboardRemove())
        await query.message.reply_text("Выберите действие:", reply_markup=get_start_inline())
        return

    if data == "start_selection":
        # Активируем кнопку внизу только здесь
        await query.message.reply_text("Переходим к подбору:", reply_markup=get_main_keyboard())
        # И сразу вызываем первый шаг
        await query.message.reply_text("Какой ассортимент Вас интересует?", reply_markup=get_gender_inline())
        return
    
    # Шаг 1: Выбор Пола
    if data.startswith("gender_"):
        gender_map = {"gender_male": "Мужская обувь", "gender_female": "Женская обувь"}
        context.user_data['current_gender'] = gender_map[data]
        response = f"Раздел: '{gender_map[data]}'. Выберите общую категорию обуви:"
        await query.edit_message_text(response, reply_markup=get_categories_inline(gender_map[data]))
        return

    # Возврат к выбору пола
    if data == "back_to_gender":
        response = "Какой ассортимент Вас интересует?"
        await query.edit_message_text(response, reply_markup=get_gender_inline())
        return

    # Шаг 2: Выбор Общей Категории
    if data.startswith("cat_"):
        category = data.replace("cat_", "")
        context.user_data['current_category'] = category
        gender = context.user_data.get('current_gender')
        response = f"Категория '{category}'. Теперь уточните тип обуви, который вы ищете:"
        await query.edit_message_text(response, reply_markup=get_subcategories_inline(gender, category))
        return

    # Возврат к категориям
    if data == "back_to_cat":
        gender = context.user_data.get('current_gender')
        response = f"Раздел: '{gender}'. Выберите общую категорию обуви:"
        await query.edit_message_text(response, reply_markup=get_categories_inline(gender))
        return

    # Шаг 3: Выбор Подкатегории (Типа обуви)
    if data.startswith("sub_"):
        sub = data.replace("sub_", "")
        context.user_data['shoes_type'] = sub
        gender = context.user_data.get('current_gender')
        
        available_brands = get_available_brands_for_type(sub, gender)
        if not available_brands:
            response = f"К сожалению, моделей '{sub}' сейчас нет в базе. Выберите другой тип:"
            category = context.user_data.get('current_category')
            await query.edit_message_text(response, reply_markup=get_subcategories_inline(gender, category))
            return
            
        response = f"Ищем {sub.lower()}. Какой бренд предпочитаете?"
        await query.edit_message_text(response, reply_markup=get_brands_inline(available_brands))
        return

    # Возврат к подкатегориям
    if data == "back_to_sub":
        gender = context.user_data.get('current_gender')
        category = context.user_data.get('current_category')
        response = f"Категория '{category}'. Теперь уточните тип обуви:"
        await query.edit_message_text(response, reply_markup=get_subcategories_inline(gender, category))
        return

    # Шаг 4: Выбор Бренда
    if data.startswith("brand_"):
        brand = data.replace("brand_", "")
        context.user_data['brand'] = brand
        
        response = f"Выбран бренд: {brand if brand != 'Any' else 'Любой'}.\nНа какой максимальный бюджет рассчитываете?\n\nВы можете нажать кнопку ниже или просто отправить сумму текстом в чат (например, 15000):"
        context.user_data['awaiting_price_text'] = True 
        await query.edit_message_text(response, reply_markup=get_price_inline())
        return

    # Возврат к брендам
    if data == "back_to_brand":
        shoes_type = context.user_data.get('shoes_type')
        gender = context.user_data.get('current_gender')
        available_brands = get_available_brands_for_type(shoes_type, gender)
        response = f"Ищем {shoes_type.lower()}. Какой бренд предпочитаете?"
        await query.edit_message_text(response, reply_markup=get_brands_inline(available_brands))
        return

    # Шаг 5: Выбор цены "Любой бюджет"
    if data == "price_any":
        context.user_data['max_price'] = float('inf')
        context.user_data['awaiting_price_text'] = False
        await process_final_search(query.message, context, edit_mode=True)
        return
    
    # Обработка уточнения цены после отказа
    if data == "reject_price":
        context.user_data['awaiting_price_text'] = True
        response = "Хорошо, давайте изменим бюджет. На какую максимальную сумму рассчитываете? (Введите числом или выберите кнопку)"
        await query.message.reply_text(response, reply_markup=get_price_inline())
        return

    # Шаги Финала: Одобрение или отказ
    if data == "shoes_yes":
        response = "Замечательно! 🎉 Вы сделали отличный выбор. Для оформления заказа перейдите по ссылкам у товаров.\n\nЧем ещё я могу Вам помочь?"
        context.user_data.clear()
        await query.message.reply_text(response, reply_markup=get_start_inline())
        return

    if data == "shoes_no":
        shoes_type = context.user_data.get('shoes_type', 'обувь')
        response = f"Принял! Модели '{shoes_type}' не подошли. Что мы изменим, чтобы найти идеальную пару?"
        await query.message.reply_text(response, reply_markup=get_rejection_inline())
        return

    # Обработка уточнений после отказа
    if data == "reject_brand":
        shoes_type = context.user_data.get('shoes_type')
        gender = context.user_data.get('current_gender')
        available_brands = get_available_brands_for_type(shoes_type, gender)
        response = f"Давайте выберем другой бренд для подкатегории '{shoes_type}':"
        await query.message.reply_text(response, reply_markup=get_brands_inline(available_brands))
        return

    if data == "reject_cat":
        response = "Давайте начнем сначала. Какой ассортимент Вас интересует?"
        await query.message.reply_text(response, reply_markup=get_gender_inline())
        return
    
    if data == "start_chat":
        await query.answer()
        # Сначала убираем старое инлайн-меню, если это необходимо, или сразу пишем:
        await query.message.reply_text(
            "С удовольствием поболтаю! Расскажи, как твои дела?", 
            reply_markup=get_main_keyboard()  # <-- ТЕПЕРЬ КНОПКА ПОЯВИТСЯ МГНОВЕННО!
        )
        return


# --- ФУНКЦИЯ ФИНАЛЬНОГО ПОИСКА И ВЫДАЧИ РЕЗУЛЬТАТОВ ---

async def process_final_search(message_obj, context, edit_mode=False):
    shoes_type = context.user_data.get('shoes_type')
    brand_filter = context.user_data.get('brand')
    max_price = context.user_data.get('max_price')
    gender_filter = context.user_data.get('current_gender')
    
    shoes_list = search_shoes(shoes_type, brand_filter, max_price, gender_filter)
    
    if shoes_list:
        response = format_shoes_list(shoes_list)
        response += "Вам нравится какой-нибудь вариант?"
        
        inline_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Да, супер! 🎉", callback_data="shoes_yes"),
             InlineKeyboardButton("Нет, не нравится ⬅️", callback_data="shoes_no")]
        ])
        
        if edit_mode:
            await message_obj.edit_text(response, reply_markup=inline_keyboard)
        else:
            await message_obj.reply_text(response, reply_markup=inline_keyboard)
    else:
        response = "К сожалению, не нашёл обуви по Вашим критериям. 😔\nВы можете вернуться назад и изменить параметры!"
        if edit_mode:
            await message_obj.edit_text(response, reply_markup=get_failure_inline())
        else:
            await message_obj.reply_text(response, reply_markup=get_failure_inline())


# --- ОБРАБОТКА ГОЛОСА ---

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from voice_utils import transcribe_voice
    user_id = update.effective_user.id
    voice = update.message.voice
    await update.message.reply_text("Распознаю голос...")
    
    voice_dir = "temp_voice"
    if not os.path.exists(voice_dir):
        os.makedirs(voice_dir)
        
    ogg_path = os.path.join(voice_dir, f"voice_{user_id}_{voice.file_unique_id}.ogg")
    try:
        file = await context.bot.get_file(voice.file_id)
        await file.download_to_drive(ogg_path)
        transcribed_text = transcribe_voice(ogg_path)
        
        if not transcribed_text or "Ошибка" in transcribed_text:
            await update.message.reply_text("Не удалось распознать речь.")
            return
            
        await update.message.reply_text(f"🎤 Вы сказали: {transcribed_text}")
        context.user_data['voice_text_override'] = transcribed_text
        await handle_message(update, context)
    finally:
        if os.path.exists(ogg_path):
            try: os.remove(ogg_path)
            except: pass


# --- ЗАПУСК БОТА ---

def main():
    request_config = HTTPXRequest(proxy=None, connect_timeout=30.0, read_timeout=30.0)
    app = Application.builder().token(TOKEN).request(request_config).build()    
    
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error(msg="Ошибка:", exc_info=context.error)

    app.add_error_handler(error_handler)
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_inline_click))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    print("🚀 Бот ПОЛНОСТЬЮ исправлен!")
    app.run_polling()

if __name__ == '__main__':
    main()