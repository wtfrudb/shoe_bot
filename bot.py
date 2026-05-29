import logging
import sqlite3
import random
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from nlp_utils import process_message, get_intent
from price_utils import parse_price, get_shoes_by_filters
from telegram.request import HTTPXRequest

TOKEN = "8321615785:AAGZNYwUQyeyWiPeslWq50EDcvvH9n0G4-Y"

# Глобальные константы для брендов
BRANDS = {
    'nike': 'Nike', 'найк': 'Nike', 'найки': 'Nike',
    'adidas': 'Adidas', 'адидас': 'Adidas',
    'puma': 'Puma', 'пума': 'Puma',
    'reebok': 'Reebok', 'рибок': 'Reebok', 'рибук': 'Reebok'
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def save_dialog(user_id, user_msg, bot_msg):
    # Подключаемся к ПРАВИЛЬНОЙ базе данных
    conn = sqlite3.connect('shoe_shop.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO conversations (user_id, user_message, bot_answer) VALUES (?, ?, ?)", 
                (str(user_id), user_msg, bot_msg))
    conn.commit()
    conn.close()

def search_shoes(shoes_type=None, brand=None, max_price=None):
    # Подключаемся к ПРАВИЛЬНОЙ базе данных
    conn = sqlite3.connect('shoe_shop.db')
    cur = conn.cursor()
    
    query = "SELECT name, price, price_text, description, shoes_type, brand, url FROM shoes WHERE 1=1"
    params = []
    
    if shoes_type:
        query += " AND LOWER(shoes_type) = ?"
        params.append(shoes_type.lower())
    
    if brand:
        query += " AND LOWER(brand) = ?"
        params.append(brand.lower())
    
    if max_price is not None:
        query += " AND price <= ?"
        params.append(max_price)
    
    query += " ORDER BY RANDOM() LIMIT 3"
    
    try:
        cur.execute(query, params)
        shoes = cur.fetchall()
    except sqlite3.OperationalError:
        logger.error("Таблица shoes не найдена в БД!")
        shoes = []
    
    conn.close()
    return shoes

def format_shoes_list(shoes_list):
    if not shoes_list:
        return None
    
    result = "Нашел для Вас отличные варианты: 🛍\n\n"
    for item in shoes_list:
        result += f"• **{item[0]}**\n  Бренд: {item[5]}\n  Стоимость: {item[2]}\n  Описание: {item[3]}\n  Ссылка: {item[6]}\n\n"
    return result

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Привет! Я бот-помощник магазина обуви. 👟\n\n"
        "Можете просто поболтать со мной — я с радостью поддержу разговор.\n"
        "А когда решите обновить гардероб — помогу подобрать идеальную пару!\n\n"
        "Просто напишите 'Хочу купить обувь' или спросите 'Что ты умеешь?'"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = update.effective_user.id
    user_text_lower = user_text.lower()
    
    if 'msg_count' not in context.user_data:
        context.user_data['msg_count'] = 0
        context.user_data['ad_triggered'] = False

    # 1. ОБРАБОТКА СТРОГОГО ОТКАЗА ПОЛЬЗОВАТЕЛЯ
    rejection_words = ["не нужно", "не нужна", "не хочу", "нет", "ничего", "не интересует", "отмена", "отстань", "хватить"]
    # Исключение, если пользователь отвечает "нет" на вопрос "Понравился ли вариант?"
    if any(word in user_text_lower for word in rejection_words) and not context.user_data.get('waiting_for_shoes_answer'):
        context.user_data.clear()
        response = random.choice([
            "Хорошо, без проблем! Больше не предлагаю. Давай просто поболтаем. Какую музыку любишь слушать?",
            "Понял-принял, закрыли тему покупок. 😊 Как вообще неделя проходит?",
            "Без проблем, не навязываюсь. Расскажи лучше, любишь ли ты смотреть сериалы?"
        ])
        await update.message.reply_text(response)
        save_dialog(user_id, user_text, response)
        return

    # 2. ПЕРЕХВАТ ШАГОВ ПОДБОРА ОБУВИ
    if context.user_data.get('awaiting_type'):
        await handle_shoes_type(update, context, user_text)
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

    # Увеличиваем шаг разговора для нативной рекламы
    context.user_data['msg_count'] += 1
    
    should_advertise = False
    if context.user_data['msg_count'] == 3 and not context.user_data['ad_triggered']:
        should_advertise = True
        context.user_data['ad_triggered'] = True

    intent, auto_response = process_message(user_text, allow_ad=should_advertise)
    
    if intent == "buy_shoes" or "купить обувь" in user_text_lower or "подбор" in user_text_lower:
        response = "О, подбор обуви — это по моей части! 👟 Что именно ищете: кроссовки, кеды, туфли или ботинки?"
        context.user_data['awaiting_type'] = True
    elif should_advertise:
        response = auto_response
        context.user_data['awaiting_type'] = True 
    else:
        response = auto_response if auto_response else "Интересно! Расскажи подробнее?"

    await update.message.reply_text(response)
    save_dialog(user_id, user_text, response)

async def handle_shoes_type(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str):
    user_text_lower = user_text.lower()
    
    type_map = {
        'кроссовки': 'кроссовки', 'кроссы': 'кроссовки', 'sneakers': 'кроссовки',
        'кеды': 'кеды', 'shoes': 'кеды',
        'туфли': 'туфли', 'лоферы': 'туфли', 'каблуки': 'туфли',
        'ботинки': 'ботинки', 'сапоги': 'ботинки', 'челси': 'ботинки'
    }
    
    shoes_type = None
    for key, value in type_map.items():
        if key in user_text_lower:
            shoes_type = value
            break
            
    if shoes_type:
        context.user_data['shoes_type'] = shoes_type
        context.user_data['awaiting_type'] = False
        context.user_data['awaiting_brand'] = True
        response = f"Понял, ищем {shoes_type}. Какой бренд предпочитаете?\n\nДоступные бренды:\n• Nike\n• Adidas\n• Puma\n• Reebok\n• Любой бренд"
        await update.message.reply_text(response)
        save_dialog(update.effective_user.id, user_text, response)
        return
    
    response = "Пожалуйста, уточните тип обуви: кроссовки, кеды, туфли или ботинки?"
    await update.message.reply_text(response)

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
        context.user_data['brand'] = brand if brand != "Любой" else "Любой"
        context.user_data['awaiting_brand'] = False
        context.user_data['awaiting_price'] = True
        
        response = f"Отлично, бренд: {brand}. На какой максимальный бюджет в рублях рассчитываете?\n(например: 15000, до 12000, любой)"
        await update.message.reply_text(response)
        save_dialog(update.effective_user.id, user_text, response)
        return
        
    response = "Пожалуйста, выберите бренд из списка (Nike, Adidas, Puma, Reebok) или напишите 'Любой'."
    await update.message.reply_text(response)

async def handle_price(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str):
    max_price = parse_price(user_text)
    
    if max_price is None:
        await update.message.reply_text("Не совсем понял сумму бюджета. Напишите, пожалуйста, числом (например, 15000 или 'любой').")
        return
        
    context.user_data['max_price'] = max_price
    context.user_data['awaiting_price'] = False
    
    # Запускаем поиск в БД
    brand_filter = context.user_data.get('brand')
    if brand_filter == "Любой":
        brand_filter = None
        
    shoes_list = search_shoes(
        context.user_data.get('shoes_type'),
        brand_filter,
        max_price
    )
    
    if shoes_list:
        response = format_shoes_list(shoes_list)
        response += "Вам нравится какой-нибудь вариант? (Да / Нет)"
        context.user_data['waiting_for_shoes_answer'] = True 
    else:
        response = "К сожалению, не нашёл обуви по Вашим критериям в базе.\n\nНапишите 'Хочу купить обувь', чтобы изменить параметры поиска!"
        context.user_data.clear()
        
    await update.message.reply_text(response)
    save_dialog(update.effective_user.id, user_text, response)

async def handle_answer_after_shoes(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str):
    user_text_lower = user_text.lower()
    intent = get_intent(user_text)
    
    if intent == "yes" or user_text_lower in ["да", "давай", "давайте", "хорошо", "ага", "конечно", "нравится"]:
        response = "Замечательно! 🎉 Вы сделали отличный выбор. Для оформления заказа перейдите по ссылке товара.\n\nЧем ещё я могу Вам помочь?"
        context.user_data.clear()  
    elif intent == "no" or user_text_lower in ["нет", "не", "не нравится"]:
        response = "Понял Вас. Давайте попробуем заново. Напишите 'Хочу купить обувь', чтобы изменить параметры поиска."
        context.user_data.clear()
    else:
        response = "Если захотите посмотреть другие модели — просто напишите 'Хочу купить обувь'."
        context.user_data.clear()
        
    await update.message.reply_text(response)
    save_dialog(update.effective_user.id, user_text, response)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from voice_utils import transcribe_voice, text_to_voice
    
    user_id = update.effective_user.id
    voice = update.message.voice
    
    await update.message.reply_text("Распознаю голос, подождите, пожалуйста...")
    
    file = await context.bot.get_file(voice.file_id)
    ogg_path = f"voice_{user_id}_{voice.file_unique_id}.ogg"
    await file.download_to_drive(ogg_path)
    
    transcribed_text = transcribe_voice(ogg_path)
    
    if not transcribed_text or "Не удалось" in transcribed_text or "Ошибка" in transcribed_text:
        await update.message.reply_text("Не удалось распознать речь. Попробуйте написать текстом или сказать чётче.")
        return
        
    await update.message.reply_text(f"Вы сказали: {transcribed_text}")
    
    # Подменяем текстовый ввод расшифрованным текстом и направляем в основной обработчик
    update.message.text = transcribed_text
    await handle_message(update, context)

def main():
    request_config = HTTPXRequest(proxy=None)
    app = Application.builder().token(TOKEN).request(request_config).build()    
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    print("🚀 Обувной ИИ-Бот успешно запущен!")
    app.run_polling()

if __name__ == '__main__':
    main()