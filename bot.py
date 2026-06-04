import logging
import sqlite3
import os
import database
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from nlp_utils import process_message
from price_utils import parse_price
from telegram.request import HTTPXRequest

TOKEN = "8321615785:AAGZNYwUQyeyWiPeslWq50EDcvvH9n0G4-Y"

BRANDS = {
    'nike': 'Nike', 'adidas': 'Adidas', 'puma': 'Puma', 'reebok': 'Reebok',
    'new balance': 'New Balance', 'asics': 'Asics', 'demix': 'Demix',
    'converse': 'Converse', 'vans': 'Vans', 'tofa': 'Tofa',
    'dr. martens': 'Dr. Martens', 'salomon': 'Salomon', 'salamander':'Salamander',
    'gucci': 'Gucci', 'chanel': 'Chanel', 'prada': 'Prada', 'hermes': 'Hermes',
    'maison margiela': 'Maison Margiela', 'bottega veneta': 'Bottega Veneta',
    'valentino': 'Valentino', 'jimmy choo':'Jimmy Choo', 'diesel':'Diesel'
}

CATALOG = {
    "Мужская обувь": {
        "Кроссовки и кеды": ["Кроссовки", "Кеды", "Слипоны"],
        "Туфли": ["Туфли", "Мокасины"],
        "Сапоги и ботинки": ["Сапоги", "Ботинки"], 
        "Сандалии и открытая": ["Сандалии"]
    },
    "Женская обувь": {
        "Кроссовки и кеды": ["Кроссовки", "Кеды", "Слипоны"],
        "Туфли и балетки": ["Туфли", "Балетки", "Мокасины", "Лоферы", "Таби"],
        "Сапоги и ботинки": ["Сапоги", "Ботинки", "Ботильоны"], 
        "Босоножки и сандалии": ["Босоножки", "Сабо", "Мюли", "Сандалии"]
    }
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def format_size(size):
    try:
        size_float = float(size)
        return str(int(size_float)) if size_float == int(size_float) else str(size_float)
    except (ValueError, TypeError):
        return str(size)

def get_main_keyboard():
    return ReplyKeyboardMarkup([['🏠 В главное меню']], resize_keyboard=True)

def get_start_inline():
    keyboard = [
        [
            InlineKeyboardButton("👟 Подобрать обувь", callback_data="start_selection"),
            InlineKeyboardButton("💬 Просто поболтать", callback_data="start_chat")
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_gender_inline():
    keyboard = [
        [InlineKeyboardButton("👨 Мужская обувь", callback_data="gender_male"),
         InlineKeyboardButton("👩 Женская обувь", callback_data="gender_female")],
        [InlineKeyboardButton("🏠 В главное меню", callback_data="menu_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ЗАДАНИЕ 1: Добавлена кнопка "Показать весь ассортимент"
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
    
    keyboard.append([InlineKeyboardButton("✨ Показать весь ассортимент", callback_data="show_all_gender_shoes")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_gender"),
                     InlineKeyboardButton("🏠 В главное меню", callback_data="menu_main")])
    return InlineKeyboardMarkup(keyboard)

# ЗАДАНИЕ 2: Добавлена кнопка "Показать все типы"
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
        
    keyboard.append([InlineKeyboardButton("✨ Показать все типы", callback_data="show_all_category_types")])
    
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
    keyboard.append([InlineKeyboardButton("✨ Показать все бренды", callback_data="brand_Any")])
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Запускаю меню...", reply_markup=ReplyKeyboardRemove())
    response = "Привет! Я бот-помощник магазина обуви. 👟\n\nЧем вы хотите заняться? Выберите действие ниже:"
    await update.message.reply_text(response, reply_markup=get_start_inline())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = context.user_data.pop('voice_text_override', update.message.text)
    user_id = update.effective_user.id
    user_text_lower = user_text.lower().strip()

    context.user_data['msg_count'] = context.user_data.get('msg_count', 0) + 1
    msg_count = context.user_data['msg_count']
    current_topic = context.user_data.get('last_topic', 'general')
    last_bot_msg = context.user_data.get('last_bot_message', '')

    if any(word in user_text_lower for word in ["нет", "не хочу", "не надо", "хватит"]):
        context.user_data['msg_count'] = -5 
        should_show_ad = False
    else:
        if (msg_count >= 4 and current_topic == 'sports') or (msg_count >= 6):
            should_show_ad = True
            context.user_data['msg_count'] = 0  
        else:
            should_show_ad = False

    if "в главное меню" in user_text_lower or user_text_lower == "/start":
        context.user_data.clear()
        response = "Вы вернулись в главное меню. Чем займемся?"
        await update.message.reply_text("Очищаю меню...", reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text(response, reply_markup=get_start_inline())
        database.save_dialog(user_id, user_text, response)
        return

    if context.user_data.get('awaiting_price_text'):
        max_price = parse_price(user_text)
        if max_price is None:
            await update.message.reply_text("Не понял сумму. Введите числом (напр. 15000).", reply_markup=get_main_keyboard())
            return
        context.user_data['max_price'] = max_price
        context.user_data['awaiting_price_text'] = False
        context.user_data['current_page'] = 0
        await process_final_search(update.message, context)
        return

    intent, response = process_message(
        user_text, 
        allow_ad=should_show_ad, 
        topic=current_topic, 
        last_bot_msg=last_bot_msg
    )

    buying_phrases = ["хочу купить", "купить обувь", "купить кроссовки", "подбор обуви", "выбрать обувь"]
    if intent == "buy_shoes" or any(phrase in user_text_lower for phrase in buying_phrases):
        context.user_data.clear()
        await update.message.reply_text("Перехожу к подбору...", reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text("О, подбор обуви — это по моей части! 👟 Какой ассортимент Вас интересует?", reply_markup=get_gender_inline())
        database.save_dialog(user_id, user_text, "Начал подбор обуви")
        return

    if response:
        r = response.lower()
        if any(w in r for w in ["спорт", "волейбол", "футбол", "бег", "тренировка"]):
            context.user_data['last_topic'] = 'sports'
        elif any(w in r for w in ["кино", "фильм", "сериал", "книга", "аниме"]):
            context.user_data['last_topic'] = 'movies'
        context.user_data['last_bot_message'] = response

    if response:
        await update.message.reply_text(response, reply_markup=get_main_keyboard())
        database.save_dialog(user_id, user_text, response)
        return

    await update.message.reply_text("Интересно, расскажи подробнее!", reply_markup=get_main_keyboard())
    database.save_dialog(user_id, user_text, "Не понял")


async def handle_inline_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data

    if data == "menu_main":
        context.user_data.clear()
        response = "Вы вернулись в главное меню. Чем займемся?"
        await query.message.reply_text(response, reply_markup=ReplyKeyboardRemove())
        await query.message.reply_text("Выберите действие:", reply_markup=get_start_inline())
        return

    if data == "start_selection":
        await query.message.reply_text("Переходим к подбору:", reply_markup=get_main_keyboard())
        await query.message.reply_text("Какой ассортимент Вас интересует?", reply_markup=get_gender_inline())
        return
    
    if data.startswith("gender_"):
        gender_map = {"gender_male": "Мужская обувь", "gender_female": "Женская обувь"}
        context.user_data['current_gender'] = gender_map[data]
        response = f"Раздел: '{gender_map[data]}'. Выберите общую категорию обуви:"
        await query.edit_message_text(response, reply_markup=get_categories_inline(gender_map[data]))
        return

    # ОБРАБОТКА ЗАДАНИЯ 1: Клиент нажал "Показать весь ассортимент"
    if data == "show_all_gender_shoes":
        context.user_data['shoes_type'] = "all_gender"
        context.user_data['brand'] = "Any"
        response = "Вы выбрали весь ассортимент раздела. На какой максимальный бюджет рассчитываете?\n\nОтправьте сумму текстом или выберите кнопку:"
        context.user_data['awaiting_price_text'] = True
        await query.edit_message_text(response, reply_markup=get_price_inline())
        return

    if data == "back_to_gender":
        response = "Какой ассортимент Вас интересует?"
        await query.edit_message_text(response, reply_markup=get_gender_inline())
        return

    if data.startswith("cat_"):
        category = data.replace("cat_", "")
        context.user_data['current_category'] = category
        gender = context.user_data.get('current_gender')
        response = f"Категория '{category}'. Теперь уточните тип обуви, который вы ищете:"
        await query.edit_message_text(response, reply_markup=get_subcategories_inline(gender, category))
        return

    # ОБРАБОТКА ЗАДАНИЯ 2: Клиент нажал "Показать все типы" в категории
    if data == "show_all_category_types":
        context.user_data['shoes_type'] = "all_category"
        context.user_data['brand'] = "Any"
        response = f"Вы выбрали показ всех типов категории '{context.user_data.get('current_category')}'. На какой максимальный бюджет рассчитываете?\n\nОтправьте сумму текстом или выберите кнопку:"
        context.user_data['awaiting_price_text'] = True
        await query.edit_message_text(response, reply_markup=get_price_inline())
        return

    if data == "back_to_cat":
        gender = context.user_data.get('current_gender')
        response = f"Раздел: '{gender}'. Выберите общую категорию обуви:"
        await query.edit_message_text(response, reply_markup=get_categories_inline(gender))
        return

    if data.startswith("sub_"):
        sub = data.replace("sub_", "").lower().strip()
        context.user_data['shoes_type'] = sub
        gender = context.user_data.get('current_gender')
        
        available_brands = database.get_available_brands_for_type(sub, gender)
        if not available_brands:
            response = f"К сожалению, моделей '{sub.capitalize()}' сейчас нет в базе. Выберите другой тип:"
            category = context.user_data.get('current_category')
            await query.edit_message_text(response, reply_markup=get_subcategories_inline(gender, category))
            return
            
        response = f"Ищем {sub}. Какой бренд предпочитаете?"
        await query.edit_message_text(response, reply_markup=get_brands_inline(available_brands))
        return

    if data == "back_to_sub":
        gender = context.user_data.get('current_gender')
        category = context.user_data.get('current_category')
        response = f"Категория '{category}'. Теперь уточните тип обуви:"
        await query.edit_message_text(response, reply_markup=get_subcategories_inline(gender, category))
        return

    if data.startswith("brand_"):
        brand = data.replace("brand_", "")
        context.user_data['brand'] = brand
        
        response = f"Выбран бренд: {brand if brand != 'Any' else 'Любой'}.\nНа какой максимальный бюджет рассчитываете?\n\nВы можете нажать кнопку ниже или просто отправить сумму текстом в чат (например, 15000):"
        context.user_data['awaiting_price_text'] = True 
        await query.edit_message_text(response, reply_markup=get_price_inline())
        return

    if data == "back_to_brand":
        shoes_type = context.user_data.get('shoes_type')
        gender = context.user_data.get('current_gender')
        if shoes_type in ["all_gender", "all_category"]:
            response = "Давайте вернемся к выбору ассортимента:"
            await query.edit_message_text(response, reply_markup=get_gender_inline())
            return
        available_brands = database.get_available_brands_for_type(shoes_type, gender)
        response = f"Ищем {shoes_type.lower()}. Какой бренд предпочитаете?"
        await query.edit_message_text(response, reply_markup=get_brands_inline(available_brands))
        return

    if data == "price_any":
        context.user_data['max_price'] = float('inf')
        context.user_data['awaiting_price_text'] = False
        context.user_data['current_page'] = 0
        await process_final_search(query.message, context, edit_mode=True)
        return
    
    if data == "reject_price":
        context.user_data['awaiting_price_text'] = True
        response = "Хорошо, давайте изменим бюджет. На какую максимальную сумму рассчитываете? (Введите числом или выберите кнопку)"
        await query.message.reply_text(response, reply_markup=get_price_inline())
        return

    # ОБРАБОТКА ЗАДАНИЯ 3: Кнопки навигации пагинации
    if data == "page_next":
        context.user_data['current_page'] = context.user_data.get('current_page', 0) + 1
        await process_final_search(query.message, context, edit_mode=True)
        return

    if data == "page_prev":
        context.user_data['current_page'] = max(0, context.user_data.get('current_page', 0) - 1)
        await process_final_search(query.message, context, edit_mode=True)
        return

    if data == "shoes_yes":
        response = "Замечательно! 🎉 Вы сделали отличный выбор. Для оформления заказа перейдите по ссылкам у товаров.\n\nЧем ещё я могу Вам помочь?"
        context.user_data.clear()
        await query.message.reply_text(response, reply_markup=get_start_inline())
        return

    if data == "shoes_no":
        shoes_type = context.user_data.get('shoes_type', 'обувь')
        if shoes_type == "all_gender": shoes_type = "весь ассортимент"
        elif shoes_type == "all_category": shoes_type = "вся категория"
        response = f"Принял! Модели '{shoes_type.capitalize()}' не подошли. Что мы изменим, чтобы найти идеальную пару?"
        await query.message.reply_text(response, reply_markup=get_rejection_inline())
        return

    if data == "reject_brand":
        shoes_type = context.user_data.get('shoes_type')
        gender = context.user_data.get('current_gender')
        if shoes_type in ["all_gender", "all_category"]:
            await query.message.reply_text("Для сквозного поиска бренд выбрать нельзя. Начнем сначала?", reply_markup=get_gender_inline())
            return
        available_brands = database.get_available_brands_for_type(shoes_type, gender)
        response = f"Давайте выберем другой бренд для подкатегории '{shoes_type.capitalize()}':"
        await query.message.reply_text(response, reply_markup=get_brands_inline(available_brands))
        return

    if data == "reject_cat":
        response = "Давайте начнем сначала. Какой ассортимент Вас интересует?"
        await query.message.reply_text(response, reply_markup=get_gender_inline())
        return
    
    if data == "start_chat":
        await query.answer()
        await query.message.reply_text(
            "С удовольствием поболтаю! Расскажи, как твои дела?", 
            reply_markup=get_main_keyboard()
        )
        return

    if data.startswith("select_shoe_"):
        shoe_id = int(data.split("_")[2])
        sizes = database.get_sizes_for_shoe(shoe_id)
        
        if not sizes:
            await query.message.reply_text("К сожалению, этого товара временно нет в наличии.", reply_markup=get_rejection_inline())
            return
            
        keyboard = []
        for size in sizes:
            fmt_size = format_size(size)
            keyboard.append([InlineKeyboardButton(f"Размер {fmt_size}", callback_data=f"select_size_{shoe_id}_{fmt_size}")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад к моделям", callback_data="shoes_no")])
        
        markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Выберите доступный размер этой модели:", reply_markup=markup)
        return

    if data.startswith("select_size_"):
        parts = data.split("_")
        shoe_id = int(parts[2])
        chosen_size = parts[3]
        
        product_url = database.get_shoe_url(shoe_id)
        clean_url = product_url.split('?')[0] if product_url else ""
        
        response = (
            f"Отличный выбор! Размер {chosen_size} успешно забронирован за Вами. 🎉\n\n"
            f"Чтобы завершить оформление и оплатить товар, "
            f"[нажмите здесь]({clean_url})"
        )
        
        context.user_data.clear()
        
        await query.message.reply_text(
            response, 
            reply_markup=get_start_inline(),
            parse_mode="Markdown"
        )
        return

# ОБРАБОТКА ЗАДАНИЯ 3: ФУНКЦИЯ ВЫДАЧИ РЕЗУЛЬТАТОВ (ПО 5 ТОВАРОВ С ОЧИСТКОЙ)
async def process_final_search(message_obj, context, edit_mode=False):
    # Удаляем старые отправленные карточки и управляющее сообщение, чтобы очистить чат
    if 'sent_message_ids' in context.user_data:
        for msg_id in context.user_data['sent_message_ids']:
            try:
                await context.bot.delete_message(chat_id=message_obj.chat_id, message_id=msg_id)
            except:
                pass
        context.user_data['sent_message_ids'] = []
    else:
        context.user_data['sent_message_ids'] = []

    if edit_mode:
        try:
            await message_obj.delete()
        except:
            pass

    shoes_type = context.user_data.get('shoes_type')
    brand_filter = context.user_data.get('brand')
    max_price = context.user_data.get('max_price')
    gender_filter = context.user_data.get('current_gender')
    current_page = context.user_data.get('current_page', 0)
    
    # Сбор списка всех подкатегорий для выполнения сквозного SQL запроса
    if shoes_type == "all_gender":
        db_search_type = []
        categories = CATALOG.get(gender_filter, {})
        for cat, subs in categories.items():
            db_search_type.extend(subs)
    elif shoes_type == "all_category":
        category = context.user_data.get('current_category')
        db_search_type = CATALOG.get(gender_filter, {}).get(category, [])
    else:
        db_search_type = shoes_type

    # Выгружаем весь отфильтрованный ассортимент одним запросом
    unique_shoes = database.search_shoes(db_search_type, brand_filter, max_price, gender_filter)
    total_shoes = len(unique_shoes)

    if not unique_shoes:
        response = "К сожалению, не нашёл обуви по Вашим критериям. 😔\nВы можете вернуться назад и изменить параметры!"
        msg = await context.bot.send_message(chat_id=message_obj.chat_id, text=response, reply_markup=get_failure_inline())
        context.user_data['sent_message_ids'].append(msg.message_id)
        return

    # Разбивка на страницы по 5 элементов
    ITEMS_PER_PAGE = 5
    start_idx = current_page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_shoes = unique_shoes[start_idx:end_idx]

    # Защитный откат на первую страницу, если индекс вышел за границы
    if not page_shoes and current_page > 0:
        context.user_data['current_page'] = 0
        current_page = 0
        start_idx = 0
        end_idx = ITEMS_PER_PAGE
        page_shoes = unique_shoes[start_idx:end_idx]

    # Отправка фото-карточек текущей страницы
    for index, shoe in enumerate(page_shoes):
        global_index = start_idx + index + 1
        sizes = database.get_sizes_for_shoe(shoe['id'])
        sizes_text = ", ".join([format_size(s) for s in sizes]) if sizes else "Нет в наличии"
        
        caption = (
            f"Модель №{global_index}\n\n"
            f"👟 Название: {shoe['name']}\n"
            f"🏷 Бренд: {shoe['brand']}\n"
            f"💰 Стоимость: {shoe['price_text']}\n"
            f"📝 Описание: {shoe['description']}\n"
            f"📏 Доступные размеры: {sizes_text}"
        )
        
        photo_msg = await context.bot.send_photo(
            chat_id=message_obj.chat_id,
            photo=shoe['image_url'],
            caption=caption
        )
        context.user_data['sent_message_ids'].append(photo_msg.message_id)

    # Динамическая строка кнопок для выбора моделей на этой странице
    buttons_row = []
    for index, shoe in enumerate(page_shoes):
        global_index = start_idx + index + 1
        buttons_row.append(InlineKeyboardButton(f"№ {global_index}", callback_data=f"select_shoe_{shoe['id']}"))

    keyboard_structure = [buttons_row]

    # Кнопки пагинации "Назад" и "Вперед", если товаров > 5
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data="page_prev"))
    if end_idx < total_shoes:
        nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data="page_next"))
    
    if nav_buttons:
        keyboard_structure.append(nav_buttons)

    keyboard_structure.append([InlineKeyboardButton("Нет, не нравится ⬅️", callback_data="shoes_no")])
    
    inline_keyboard = InlineKeyboardMarkup(keyboard_structure)
    
    page_text = f"Показаны модели {start_idx + 1}-{min(end_idx, total_shoes)} из {total_shoes}. Какая модель вам нравится?"
    action_msg = await context.bot.send_message(
        chat_id=message_obj.chat_id,
        text=page_text,
        reply_markup=inline_keyboard
    )
    context.user_data['sent_message_ids'].append(action_msg.message_id)


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