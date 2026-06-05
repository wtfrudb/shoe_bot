import logging
import sqlite3
import os
import re
import difflib
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

TEXT_NUMBERS = {
    "один": "1", "первый": "1", "первую": "1", "первая": "1",
    "два": "2", "второй": "2", "вторую": "2", "вторая": "2",
    "три": "3", "третий": "3", "третью": "3", "третья": "3",
    "четыре": "4", "четвертый": "4", "четвертую": "4", "четвертая": "4",
    "пять": "5", "пятый": "5", "пятую": "5", "пятая": "5",
    "шесть": "6", "шестой": "6", "шестую": "6",
    "семь": "7", "седьмой": "7", "седьмую": "7",
    "восемь": "8", "восьмой": "8", "восьмую": "8",
    "девять": "9", "девятый": "9", "девятую": "9",
    "десять": "10", "десятый": "10", "десятую": "10"
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Функция тотальной очистки временной папки при старте
def clear_temp_voice_dir():
    voice_dir = "temp_voice"
    if os.path.exists(voice_dir):
        for file in os.listdir(voice_dir):
            file_path = os.path.join(voice_dir, file)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.error(f"Не удалось удалить старый файл {file_path}: {e}")

class SimulatedQuery:
    def __init__(self, message, data):
        self.message = message
        self.data = data
    async def answer(self): 
        pass
    async def edit_message_text(self, text, reply_markup=None):
        return await self.message.reply_text(text, reply_markup=reply_markup)

def format_size(size):
    try:
        size_float = float(size)
        return str(int(size_float)) if size_float == int(size_float) else str(size_float)
    except (ValueError, TypeError):
        return str(size)

def get_main_keyboard():
    return ReplyKeyboardMarkup([['🏠 В главное меню']], resize_keyboard=True)

def get_start_inline():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("👟 Подобрать обувь", callback_data="start_selection"),
        InlineKeyboardButton("💬 Просто поболтать", callback_data="start_chat")
    ]])

def get_gender_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👨 Мужская обувь", callback_data="gender_male"),
         InlineKeyboardButton("👩 Женская обувь", callback_data="gender_female")],
        [InlineKeyboardButton("🏠 В главное меню", callback_data="menu_main")]
    ])

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
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Любой бюджет", callback_data="price_any")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_brand"),
         InlineKeyboardButton("🏠 В главное меню", callback_data="menu_main")]
    ])

def get_rejection_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Изменить бренд", callback_data="reject_brand"),
         InlineKeyboardButton("💰 Изменить бюджет", callback_data="reject_price")], 
        [InlineKeyboardButton("🗂 Другая категория", callback_data="reject_cat")],
        [InlineKeyboardButton("🏠 В главное меню", callback_data="menu_main")]
    ])

def get_failure_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад к бренду", callback_data="back_to_brand"),
         InlineKeyboardButton("💰 Изменить бюджет", callback_data="reject_price")],
        [InlineKeyboardButton("🏠 В главное меню", callback_data="menu_main")]
    ])


# Глобальная и видимая функция START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Запускаю меню...", reply_markup=ReplyKeyboardRemove())
    response = "Привет! Я бот-помощник магазина обуви. 👟\n\nЧем вы хотите заняться? Выберите действие ниже:"
    await update.message.reply_text(response, reply_markup=get_start_inline())


async def handle_shoe_selection_by_text(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    user_text_cleaned = user_text.replace('"', '').replace('«', '').replace('»', '').strip()
    user_text_lower = user_text_cleaned.lower()
    last_bot_msg = context.user_data.get('last_bot_message', '').lower()
    
    # ТРИГГЕР СМЕНЫ ТЕМЫ: Если пользователь явно спрашивает сторонние вещи, выходим из подбора
    if any(word in user_text_lower for word in ["погода", "как дела", "привет", "кто ты", "что умеешь"]):
        return False

    # 1. ЭТАП: Выбор пола
    if "ассортимент вас интересует" in last_bot_msg or not context.user_data.get('current_gender'):
        gender_options = {"мужская обувь": "gender_male", "женская обувь": "gender_female"}
        matches = difflib.get_close_matches(user_text_lower, list(gender_options.keys()), n=1, cutoff=0.4)
        if matches:
            simulated_query = SimulatedQuery(update.message, gender_options[matches[0]])
            await handle_inline_click(update, context, external_query=simulated_query)
            return True

    # 2. ЭТАП: Выбор общей категории
    if "выберите общую категорию обуви" in last_bot_msg or (context.user_data.get('current_gender') and not context.user_data.get('current_category')):
        gender = context.user_data.get('current_gender', "Мужская обувь")
        categories = list(CATALOG.get(gender, {}).keys())
        matches = difflib.get_close_matches(user_text_lower, [c.lower() for c in categories], n=1, cutoff=0.4)
        if matches:
            chosen_cat = categories[[c.lower() for c in categories].index(matches[0])]
            simulated_query = SimulatedQuery(update.message, f"cat_{chosen_cat}")
            await handle_inline_click(update, context, external_query=simulated_query)
            return True

    # 3. ЭТАП: Выбор подкатегории (типа обуви)
    if "уточните тип обуви" in last_bot_msg or (context.user_data.get('current_category') and not context.user_data.get('shoes_type')):
        gender = context.user_data.get('current_gender', "Мужская обувь")
        category = context.user_data.get('current_category', "")
        subcategories = CATALOG.get(gender, {}).get(category, [])
        matches = difflib.get_close_matches(user_text_lower, [s.lower() for s in subcategories], n=1, cutoff=0.4)
        if matches:
            chosen_sub = subcategories[[s.lower() for s in subcategories].index(matches[0])]
            simulated_query = SimulatedQuery(update.message, f"sub_{chosen_sub}")
            await handle_inline_click(update, context, external_query=simulated_query)
            return True

    # 4. ЭТАП: Выбор бренда
    if "какой бренд предпочитаете" in last_bot_msg or (context.user_data.get('shoes_type') and not context.user_data.get('brand')):
        if any(ph in user_text_lower for ph in ["все бренды", "показать все бренды", "любой бренд", "все равно"]):
            simulated_query = SimulatedQuery(update.message, "brand_Any")
            await handle_inline_click(update, context, external_query=simulated_query)
            return True

        brand_input = user_text_lower
        matched_brand = None
        for key, val in BRANDS.items():
            if key in brand_input or brand_input in key:
                matched_brand = key
                break
        if matched_brand:
            simulated_query = SimulatedQuery(update.message, f"brand_{matched_brand}")
            await handle_inline_click(update, context, external_query=simulated_query)
            return True

    # 5. ЭТАП: Выбор конкретной модели или размера
    if "какая модель вам нравится" in last_bot_msg or "выберите доступный размер" in last_bot_msg or "не удалось распознать номер модели" in last_bot_msg:
        processed_text = user_text_lower
        
        # ОБРАБОТКА ОТКАЗА: Если пользователь говорит "никакая", "ничего не нравится" и т.д.
        rejection_phrases = ["никакая", "ни одна", "ничего", "не нравится", "нет", "отмена", "никакой"]
        if any(phrase in processed_text for phrase in rejection_phrases) and "размер" not in last_bot_msg:
            # Имитируем нажатие кнопки "Нет, не нравится" (shoes_no)
            simulated_query = SimulatedQuery(update.message, "shoes_no")
            await handle_inline_click(update, context, external_query=simulated_query)
            return True

        # Переводим текстовые числительные в цифры
        for word, num in TEXT_NUMBERS.items():
            processed_text = re.sub(rf'\b{word}\b', num, processed_text)

        digits = re.findall(r'\d+', processed_text)
        
        if digits:
            digit_val = int(digits[0])
            if "размер" in last_bot_msg:
                await update.message.reply_text(f"Выбран числовой размер: {digit_val}. Проверяю доступность...")
                await update.message.reply_text("Пожалуйста, нажмите на инлайн-кнопку с нужным размером для подтверждения брони.")
                return True
            else:
                last_page_ids = context.user_data.get('last_page_shoe_ids', [])
                target_idx = digit_val - 1
                if 0 <= target_idx < len(last_page_ids):
                    target_id = last_page_ids[target_idx]
                    simulated_query = SimulatedQuery(update.message, f"select_shoe_{target_id}")
                    await handle_inline_click(update, context, external_query=simulated_query)
                    return True
                else:
                    response = f"Модели под номером {digit_val} нет на экране. Пожалуйста, назовите номер из доступных."
                    context.user_data['last_bot_message'] = response
                    await update.message.reply_text(response)
                    return True
        else:
            response = "Не удалось распознать номер модели. Пожалуйста, назовите только номер (например: «Один» или «Номер 1») либо скажите «Никакая»."
            context.user_data['last_bot_message'] = response
            await update.message.reply_text(response)
            return True


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = context.user_data.pop('voice_text_override', update.message.text)
    user_id = update.effective_user.id
    user_text_lower = user_text.lower().strip()

    is_searching_shoes = any(k in context.user_data for k in ['current_gender', 'current_category', 'shoes_type', 'brand'])
    last_bot_msg = context.user_data.get('last_bot_message', '')
    last_bot_msg_lower = last_bot_msg.lower()
    
    is_bot_waiting_shoe_param = any(phrase in last_bot_msg_lower for phrase in [
        "ассортимент вас интересует", "категорию обуви", "уточните тип обуви", "какой бренд предпочитаете", "какая модель вам нравится", "выберите доступный размер", "не удалось распознать номер модели"
    ])

    if is_searching_shoes or is_bot_waiting_shoe_param or context.user_data.get('awaiting_price_text'):
        if context.user_data.get('is_voice_session'):
            context.user_data['suppress_tts'] = True

        is_user_saying_brand = any(key in user_text_lower for key in BRANDS.keys())
        is_asking_all_brands = any(ph in user_text_lower for ph in ["все бренды", "показать все бренды", "любой бренд"])
        
        if context.user_data.get('awaiting_price_text') and not is_user_saying_brand and not is_asking_all_brands and not any(g in user_text_lower for g in ["мужская", "женская"]):
            if "любой" in user_text_lower or "любая" in user_text_lower or "все равно" in user_text_lower:
                context.user_data['max_price'] = float('inf')
                context.user_data['awaiting_price_text'] = False
                context.user_data['current_page'] = 0
                await process_final_search(update.message, context)
                return

            max_price = parse_price(user_text)
            if max_price is None:
                response = "Не понял сумму. Введите числом (напр. 15000) или скажите «Любой бюджет»."
                await update.message.reply_text(response, reply_markup=get_main_keyboard())
                return
                
            context.user_data['max_price'] = max_price
            context.user_data['awaiting_price_text'] = False
            context.user_data['current_page'] = 0
            await process_final_search(update.message, context)
            return

        was_processed = await handle_shoe_selection_by_text(update, context, user_text)
        if was_processed:
            return

    if "в главное меню" in user_text_lower or user_text_lower == "/start":
        context.user_data.clear()
        response = "Вы вернулись в главное меню. Чем займемся?"
        await update.message.reply_text("Очищаю меню...", reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text(response, reply_markup=get_start_inline())
        database.save_dialog(user_id, user_text, response)
        return

    if any(w in user_text_lower for w in ["спорт", "волейбол", "футбол", "бег"]):
        context.user_data['last_topic'] = 'sports'
    elif any(w in user_text_lower for w in ["кино", "фильм", "сериал"]):
        context.user_data['last_topic'] = 'movies'

    context.user_data['msg_count'] = context.user_data.get('msg_count', 0) + 1
    msg_count = context.user_data['msg_count']
    current_topic = context.user_data.get('last_topic', 'general')

    should_show_ad = False
    if not any(word in user_text_lower for word in ["нет", "не хочу", "не надо"]):
        if (msg_count >= 3 and current_topic == 'sports') or (msg_count >= 6):
            should_show_ad = True
            context.user_data['msg_count'] = 0  

    intent, response = process_message(user_text, allow_ad=should_show_ad, topic=current_topic, last_bot_msg=last_bot_msg)

    buying_phrases = ["хочу купить", "купить обувь", "купить кроссовки", "подбор обуви", "выбрать обувь"]
    if intent == "buy_shoes" or any(phrase in user_text_lower for phrase in buying_phrases):
        context.user_data.clear()
        response = "О, подбор обуви — это по моей части! 👟 Какой ассортимент Вас интересует?"
        context.user_data['last_bot_message'] = response
        await update.message.reply_text("Перехожу к подбору...", reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text(response, reply_markup=get_gender_inline())
        database.save_dialog(user_id, user_text, "Начал подбор обуви")
        return

    if response:
        context.user_data['last_bot_message'] = response
        await update.message.reply_text(response, reply_markup=get_main_keyboard())
        database.save_dialog(user_id, user_text, response)
        return

    fallback_response = "Интересно, расскажи подробнее!"
    context.user_data['last_bot_message'] = fallback_response
    await update.message.reply_text(fallback_response, reply_markup=get_main_keyboard())
    database.save_dialog(user_id, user_text, "Не понял")
    
    
async def handle_inline_click(update: Update, context: ContextTypes.DEFAULT_TYPE, external_query=None):
    query = external_query if external_query is not None else update.callback_query
    if external_query is None:
        await query.answer()
    
    data = query.data

    if data == "menu_main":
        context.user_data.clear()
        response = "Вы вернулись в главное меню. Чем займемся?"
        context.user_data['last_bot_message'] = response
        await query.message.reply_text(response, reply_markup=ReplyKeyboardRemove())
        await query.message.reply_text("Выберите действие:", reply_markup=get_start_inline())
        return

    if data == "start_selection":
        context.user_data.clear()
        response = "Какой ассортимент Вас интересует?"
        context.user_data['last_bot_message'] = response
        await query.message.reply_text("Переходим к подбору:", reply_markup=get_main_keyboard())
        await query.message.reply_text(response, reply_markup=get_gender_inline())
        return
    
    if data.startswith("gender_"):
        gender_map = {"gender_male": "Мужская обувь", "gender_female": "Женская обувь"}
        context.user_data['current_gender'] = gender_map[data]
        response = f"Раздел: '{gender_map[data]}'. Выберите общую категорию обуви:"
        context.user_data['last_bot_message'] = response
        if external_query: await query.message.reply_text(response, reply_markup=get_categories_inline(gender_map[data]))
        else: await query.edit_message_text(response, reply_markup=get_categories_inline(gender_map[data]))
        return

    if data == "show_all_gender_shoes":
        context.user_data['shoes_type'] = "all_gender"
        context.user_data['brand'] = "Any"
        response = "Вы выбрали весь ассортимент раздела. На какой максимальный бюджет рассчитываете?\n\nОтправьте сумму текстом или выберите кнопку:"
        context.user_data['last_bot_message'] = response
        context.user_data['awaiting_price_text'] = True
        if external_query: await query.message.reply_text(response, reply_markup=get_price_inline())
        else: await query.edit_message_text(response, reply_markup=get_price_inline())
        return

    if data == "back_to_gender":
        context.user_data.pop('current_gender', None)
        context.user_data.pop('current_category', None)
        response = "Какой ассортимент Вас интересует?"
        context.user_data['last_bot_message'] = response
        await query.edit_message_text(response, reply_markup=get_gender_inline())
        return

    if data.startswith("cat_"):
        category = data.replace("cat_", "")
        context.user_data['current_category'] = category
        gender = context.user_data.get('current_gender')
        response = f"Категория '{category}'. Теперь уточните тип обуви, который вы ищете:"
        context.user_data['last_bot_message'] = response
        if external_query: await query.message.reply_text(response, reply_markup=get_subcategories_inline(gender, category))
        else: await query.edit_message_text(response, reply_markup=get_subcategories_inline(gender, category))
        return

    if data == "show_all_category_types":
        context.user_data['shoes_type'] = "all_category"
        context.user_data['brand'] = "Any"
        response = f"Вы выбрали показ всех типов категории '{context.user_data.get('current_category')}'. На какой максимальный бюджет рассчитываете?\n\nОтправьте сумму текстом или выберите кнопку:"
        context.user_data['last_bot_message'] = response
        context.user_data['awaiting_price_text'] = True
        if external_query: await query.message.reply_text(response, reply_markup=get_price_inline())
        else: await query.edit_message_text(response, reply_markup=get_price_inline())
        return

    if data == "back_to_cat":
        context.user_data.pop('current_category', None)
        context.user_data.pop('shoes_type', None)
        gender = context.user_data.get('current_gender')
        response = f"Раздел: '{gender}'. Выберите общую категорию обуви:"
        context.user_data['last_bot_message'] = response
        await query.edit_message_text(response, reply_markup=get_categories_inline(gender))
        return

    if data.startswith("sub_"):
        sub = data.replace("sub_", "").lower().strip()
        context.user_data['shoes_type'] = sub
        gender = context.user_data.get('current_gender')
        
        available_brands = database.get_available_brands_for_type(sub, gender)
        if not available_brands:
            response = f"К сожалению, моделей '{sub.capitalize()}' сейчас нет в базе. Выберите другой тип:"
            context.user_data['last_bot_message'] = response
            category = context.user_data.get('current_category')
            if external_query: await query.message.reply_text(response, reply_markup=get_subcategories_inline(gender, category))
            else: await query.edit_message_text(response, reply_markup=get_subcategories_inline(gender, category))
            return
            
        response = f"Ищем {sub}. Какой бренд предпочитаете?"
        context.user_data['last_bot_message'] = response
        if external_query: await query.message.reply_text(response, reply_markup=get_brands_inline(available_brands))
        else: await query.edit_message_text(response, reply_markup=get_brands_inline(available_brands))
        return

    if data == "back_to_sub":
        context.user_data.pop('shoes_type', None)
        context.user_data.pop('brand', None)
        gender = context.user_data.get('current_gender')
        category = context.user_data.get('current_category')
        response = f"Категория '{category}'. Теперь уточните тип обуви:"
        context.user_data['last_bot_message'] = response
        await query.edit_message_text(response, reply_markup=get_subcategories_inline(gender, category))
        return

    if data.startswith("brand_"):
        brand = data.replace("brand_", "")
        context.user_data['brand'] = brand
        response = f"Выбран бренд: {brand if brand != 'Any' else 'Любой'}.\nНа какой максимальный бюджет рассчитываете?\n\nВы можете нажать кнопку ниже или просто отправить сумму текстом в чат (например, 15000):"
        context.user_data['last_bot_message'] = response
        context.user_data['awaiting_price_text'] = True 
        if external_query: await query.message.reply_text(response, reply_markup=get_price_inline())
        else: await query.edit_message_text(response, reply_markup=get_price_inline())
        return

    if data == "back_to_brand":
        context.user_data['awaiting_price_text'] = False
        shoes_type = context.user_data.get('shoes_type')
        gender = context.user_data.get('current_gender')
        
        # Если был выбран весь ассортимент пола (Мужская/Женская обувь)
        if shoes_type == "all_gender":
            context.user_data.pop('brand', None)
            context.user_data.pop('shoes_type', None)
            response = "Давайте вернемся к выбору ассортимента:"
            context.user_data['last_bot_message'] = response
            await query.edit_message_text(response, reply_markup=get_gender_inline())
            return
            
        # Если был выбран показ всех типов внутри конкретной категории (например, все типы в Туфлях и балетках)
        elif shoes_type == "all_category":
            context.user_data.pop('brand', None)
            context.user_data.pop('shoes_type', None)
            category = context.user_data.get('current_category')
            response = f"Категория '{category}'. Теперь уточните тип обуви, который вы ищете:"
            context.user_data['last_bot_message'] = response
            await query.edit_message_text(response, reply_markup=get_subcategories_inline(gender, category))
            return
            
        # Обычный возврат к брендам, если искали конкретный тип обуви
        context.user_data.pop('brand', None)
        available_brands = database.get_available_brands_for_type(shoes_type, gender)
        response = f"Ищем {shoes_type.lower()}. Какой бренд предпочитаете?"
        context.user_data['last_bot_message'] = response
        await query.edit_message_text(response, reply_markup=get_brands_inline(available_brands))
        return

    if data == "price_any":
        context.user_data['max_price'] = float('inf')
        context.user_data['awaiting_price_text'] = False
        context.user_data['current_page'] = 0
        await process_final_search(query.message, context, edit_mode=not bool(external_query))
        return
    
    if data == "reject_price":
        context.user_data['awaiting_price_text'] = True
        response = "Хорошо, давайте изменим бюджет. На какую максимальную сумму рассчитываете?"
        context.user_data['last_bot_message'] = response
        await query.message.reply_text(response, reply_markup=get_price_inline())
        return

    if data == "page_next":
        context.user_data['current_page'] = context.user_data.get('current_page', 0) + 1
        await process_final_search(query.message, context, edit_mode=True)
        return

    if data == "page_prev":
        context.user_data['current_page'] = max(0, context.user_data.get('current_page', 0) - 1)
        await process_final_search(query.message, context, edit_mode=True)
        return

    if data == "shoes_yes":
        response = "Замечательно! 🎉 Вы сделали отличный выбор. Для оформления заказа перейдите по ссылкам у товаров."
        context.user_data.clear()
        context.user_data['last_bot_message'] = response
        await query.message.reply_text(response, reply_markup=get_start_inline())
        return

    if data == "shoes_no":
        shoes_type = context.user_data.get('shoes_type', 'обувь')
        if shoes_type == "all_gender": shoes_type = "весь ассортимент"
        elif shoes_type == "all_category": shoes_type = "вся категория"
        response = f"Принял! Модели '{shoes_type.capitalize()}' не подошли. Что мы изменим?"
        context.user_data['last_bot_message'] = response
        await query.message.reply_text(response, reply_markup=get_rejection_inline())
        return

    if data == "reject_brand":
        context.user_data['awaiting_price_text'] = False
        shoes_type = context.user_data.get('shoes_type')
        gender = context.user_data.get('current_gender')
        available_brands = database.get_available_brands_for_type(shoes_type, gender)
        response = f"Давайте выберем другой бренд для подкатегории '{shoes_type.capitalize()}':"
        context.user_data['last_bot_message'] = response
        await query.message.reply_text(response, reply_markup=get_brands_inline(available_brands))
        return

    if data == "reject_cat":
        context.user_data.clear()
        response = "Давайте начнем сначала. Какой ассортимент Вас интересует?"
        context.user_data['last_bot_message'] = response
        await query.message.reply_text(response, reply_markup=get_gender_inline())
        return
    
    if data == "start_chat":
        response = "С удовольствием поболтаю! Расскажи, как твои дела?"
        context.user_data['last_bot_message'] = response
        await query.message.reply_text(response, reply_markup=get_main_keyboard())
        return

    if data.startswith("select_shoe_"):
        shoe_id = int(data.split("_")[2])
        sizes = database.get_sizes_for_shoe(shoe_id)
        if not sizes:
            response = "К сожалению, этого товара временно нет в наличии."
            context.user_data['last_bot_message'] = response
            await query.message.reply_text(response, reply_markup=get_rejection_inline())
            return
            
        keyboard = []
        for size in sizes:
            fmt_size = format_size(size)
            keyboard.append([InlineKeyboardButton(f"Размер {fmt_size}", callback_data=f"select_size_{shoe_id}_{fmt_size}")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад к моделям", callback_data="shoes_no")])
        
        markup = InlineKeyboardMarkup(keyboard)
        response = "Выберите доступный размер этой модели:"
        context.user_data['last_bot_message'] = response
        if external_query:
            await query.message.reply_text(response, reply_markup=markup)
        else:
            await query.message.reply_text(response, reply_markup=markup)
        return

    if data.startswith("select_size_"):
        parts = data.split("_")
        shoe_id = int(parts[2])
        chosen_size = parts[3]
        product_url = database.get_shoe_url(shoe_id)
        clean_url = product_url.split('?')[0] if product_url else ""
        
        response = f"Отличный выбор! Размер {chosen_size} успешно забронирован за Вами. 🎉\n\nЧтобы завершить оформление, [нажмите здесь]({clean_url})"
        context.user_data.clear()
        context.user_data['last_bot_message'] = response
        await query.message.reply_text(response, reply_markup=get_start_inline(), parse_mode="Markdown")
        return


async def process_final_search(message_obj, context, edit_mode=False):
    if 'sent_message_ids' in context.user_data:
        for msg_id in context.user_data['sent_message_ids']:
            try: await context.bot.delete_message(chat_id=message_obj.chat_id, message_id=msg_id)
            except: pass
        context.user_data['sent_message_ids'] = []
    else:
        context.user_data['sent_message_ids'] = []

    if edit_mode:
        try: await message_obj.delete()
        except: pass

    shoes_type = context.user_data.get('shoes_type')
    brand_filter = context.user_data.get('brand')
    max_price = context.user_data.get('max_price')
    gender_filter = context.user_data.get('current_gender')
    current_page = context.user_data.get('current_page', 0)
    
    if shoes_type == "all_gender":
        db_search_type = []
        categories = CATALOG.get(gender_filter, {})
        for cat, subs in categories.items(): db_search_type.extend(subs)
    elif shoes_type == "all_category":
        category = context.user_data.get('current_category')
        db_search_type = CATALOG.get(gender_filter, {}).get(category, [])
    else:
        db_search_type = shoes_type

    unique_shoes = database.search_shoes(db_search_type, brand_filter, max_price, gender_filter)
    total_shoes = len(unique_shoes)

    if not unique_shoes:
        response = "К сожалению, не нашёл обуви по Вашим критериям. 😔"
        context.user_data['last_bot_message'] = response
        msg = await context.bot.send_message(chat_id=message_obj.chat_id, text=response, reply_markup=get_failure_inline())
        context.user_data['sent_message_ids'].append(msg.message_id)
        return

    ITEMS_PER_PAGE = 5
    start_idx = current_page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_shoes = unique_shoes[start_idx:end_idx]

    context.user_data['last_page_shoe_ids'] = [shoe['id'] for shoe in page_shoes]

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
        photo_msg = await context.bot.send_photo(chat_id=message_obj.chat_id, photo=shoe['image_url'], caption=caption)
        context.user_data['sent_message_ids'].append(photo_msg.message_id)

    buttons_row = []
    for index, shoe in enumerate(page_shoes):
        global_index = start_idx + index + 1
        buttons_row.append(InlineKeyboardButton(f"№ {global_index}", callback_data=f"select_shoe_{shoe['id']}"))

    keyboard_structure = [buttons_row]
    nav_buttons = []
    if current_page > 0: nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data="page_prev"))
    if end_idx < total_shoes: nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data="page_next"))
    if nav_buttons: keyboard_structure.append(nav_buttons)

    keyboard_structure.append([InlineKeyboardButton("Нет, не нравится ⬅️", callback_data="shoes_no")])
    inline_keyboard = InlineKeyboardMarkup(keyboard_structure)
    
    page_text = f"Показаны модели {start_idx + 1}-{min(end_idx, total_shoes)} из {total_shoes}. Какая модель вам нравится?"
    context.user_data['last_bot_message'] = page_text
    action_msg = await context.bot.send_message(chat_id=message_obj.chat_id, text=page_text, reply_markup=inline_keyboard)
    context.user_data['sent_message_ids'].append(action_msg.message_id)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from voice_utils import transcribe_voice, text_to_voice
    user_id = update.effective_user.id
    voice = update.message.voice
    status_msg = await update.message.reply_text("🎧 Слушаю и распознаю ваш голос...")
    
    voice_dir = "temp_voice"
    if not os.path.exists(voice_dir): 
        os.makedirs(voice_dir)
        
    ogg_input_path = None
    ogg_output_path = None
    
    try:
        ogg_input_path = os.path.join(voice_dir, f"voice_{user_id}_{voice.file_unique_id}.ogg")
        ogg_output_path = os.path.join(voice_dir, f"response_{user_id}_{voice.file_unique_id}.ogg")
        
        file = await context.bot.get_file(voice.file_id)
        await file.download_to_drive(ogg_input_path)
        transcribed_text = transcribe_voice(ogg_input_path)
        
        if not transcribed_text or "Ошибка" in transcribed_text or "Не удалось распознать" in transcribed_text:
            await status_msg.edit_text("❌ Не удалось разобрать слова. Попробуйте сказать чётче.")
            return
            
        await status_msg.delete()
        await update.message.reply_text(f"🎤 _Вы сказали:_ \"{transcribed_text}\"", parse_mode="Markdown")
        
        context.user_data['voice_text_override'] = transcribed_text
        context.user_data['is_voice_session'] = True  
        await handle_message(update, context)
        
        if context.user_data.get('suppress_tts'): 
            return
            
        bot_text_answer = context.user_data.get('last_bot_response', None)
        if bot_text_answer:
            voice_response = text_to_voice(bot_text_answer, output_path=ogg_output_path)
            if voice_response and os.path.exists(voice_response):
                with open(voice_response, 'rb') as voice_file:
                    await update.message.reply_voice(voice=voice_file, caption="👟 Ответ shoe_bot")
            else:
                await update.message.reply_text(bot_text_answer)
                
    except Exception as e:
        logger.error(f"Ошибка во время обработки голосового сообщения: {e}")
        try:
            await update.message.reply_text("Произошла ошибка при обработке голосового ответа.")
        except:
            pass
    finally:
        context.user_data.pop('is_voice_session', None)
        context.user_data.pop('last_bot_response', None)
        context.user_data.pop('suppress_tts', None)
        
        for path in [ogg_input_path, ogg_output_path]:
            if path and os.path.exists(path):
                try: 
                    os.remove(path)
                except Exception as e:
                    logger.error(f"Не удалось очистить файл {path}: {e}")

def main():
    clear_temp_voice_dir()

    request_config = HTTPXRequest(proxy=None, connect_timeout=30.0, read_timeout=30.0)
    app = Application.builder().token(TOKEN).request(request_config).build()    
    
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error(msg="Ошибка во время работы:", exc_info=context.error)

    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_inline_click))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    print("🚀 Бот полностью обновлен! Перехваты стейтов устранены.")
    app.run_polling()

if __name__ == '__main__':
    main()