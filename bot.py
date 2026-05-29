import logging
import sqlite3
import random
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from nlp_utils import process_message
from price_utils import parse_price
from telegram.request import HTTPXRequest

TOKEN = "8321615785:AAGZNYwUQyeyWiPeslWq50EDcvvH9n0G4-Y"

# Глобальные константы для брендов (замена локаций)
BRANDS = {
    'nike': 'Nike', 'найк': 'Nike', 'найки': 'Nike',
    'adidas': 'Adidas', 'адидас': 'Adidas',
    'puma': 'Puma', 'пума': 'Puma',
    'reebok': 'Reebok', 'рибок': 'Reebok', 'рибук': 'Reebok'
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def save_dialog(user_id, user_msg, bot_msg):
    conn = sqlite3.connect('realty_bot.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO conversations (user_id, user_message, bot_answer) VALUES (?, ?, ?)", 
                (str(user_id), user_msg, bot_msg))
    conn.commit()
    conn.close()

def search_shoes(shoes_type=None, brand=None, max_price=None):
    conn = sqlite3.connect('realty_bot.db')
    cur = conn.cursor()
    
    query = "SELECT name, price, price_text, description, shoes_type, brand, url FROM shoes WHERE 1=1"
    params = []
    
    if shoes_type:
        query += " AND shoes_type = ?"
        params.append(shoes_type)
    
    if brand:
        query += " AND brand = ?"
        params.append(brand)
    
    if max_price is not None:
        query += " AND price <= ?"
        params.append(max_price)
    
    query += " ORDER BY RANDOM() LIMIT 3"
    
    try:
        cur.execute(query, params)
        shoes = cur.fetchall()
    except sqlite3.OperationalError:
        logger.error("Таблица shoes не найдена в БД! Вывод тестовых данных.")
        shoes = [("Тестовые Кроссовки Nike Air", 8990, "8 990 руб.", "Удобные кроссовки на каждый день", "кроссовки", "Nike", "https://example.com")]
    
    conn.close()
    return shoes

def format_shoes_list(shoes_list):
    if not shoes_list:
        return None
    
    result = "Нашел для Вас отличные варианты: 🛍\n\n"
    for item in shoes_list:
        result += f"• {item[0]}\n  Бренд: {item[5]}\n  Стоимость: {item[2]}\n  Описание: {item[3]}\n  Ссылка: {item[6]}\n\n"
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
    intent, auto_response = process_message(user_text)
    
    logger.info(f"User {user_id}: {user_text} -> Intent: {intent}")
    
    # Перехват шагов опросника (состояния последовательного подбора)
    if context.user_data.get('waiting_for_shoes_answer'):
        await handle_answer_after_shoes(update, context, user_text, intent)
        return
    
    if context.user_data.get('awaiting_type'):
        await handle_shoes_type(update, context, user_text, intent)
        return
    
    if context.user_data.get('awaiting_brand'):
        await handle_brand(update, context, user_text, intent)
        return
    
    if context.user_data.get('awaiting_price'):
        await handle_price(update, context, user_text, intent)
        return
    
    # Логика ветвления по бизнес-интентам верхнего уровня
    if intent in ["buy_shoes", "buy_house"]:
        response = "Отлично! Давайте подберём идеальную обувь. 👟👠\n\nКакой тип Вас интересует?\n(кроссовки, кеды, туфли, ботинки)"
        context.user_data['awaiting_type'] = True
    
    elif intent == "yes" or user_text.lower() in ["да", "давай", "давайте", "хорошо", "ага", "конечно"]:
        response = "Замечательно! Давайте выберем обувь.\n\nЧто ищете: кроссовки, кеды, туфли или ботинки?"
        context.user_data['awaiting_type'] = True
    
    elif intent == "no" or user_text.lower() in ["нет", "не", "не надо", "не хочу"]:
        response = "Хорошо, понял. Если передумаете или решите обновить гардероб — обращайтесь!"
        context.user_data.clear()
    
    elif auto_response:
        response = auto_response
        
    else:
        response = "Я пока только учусь понимать такие фразы. Но я спец в обуви! Хотите посмотреть модели? Напишите 'Хочу купить обувь'."
    
    await update.message.reply_text(response)
    save_dialog(user_id, user_text, response)

async def handle_shoes_type(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str, intent: str):
    user_text_lower = user_text.lower()
    
    type_map = {
        'кроссовки': 'кроссовки', 'кроссы': 'кроссовки', 'sneakers': 'кроссовки',
        'кеды': 'кеды', 'кеды': 'кеды',
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

async def handle_brand(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str, intent: str):
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
        context.user_data['brand'] = brand if brand != "Любой" else None
        context.user_data['awaiting_brand'] = False
        context.user_data['awaiting_price'] = True
        
        response = f"Отлично, бренд: {brand}. На какой максимальный бюджет в рублях рассчитываете?\n(например: 5000, до 12000, любой)"
        await update.message.reply_text(response)
        save_dialog(update.effective_user.id, user_text, response)
        return
        
    response = "Пожалуйста, выберите бренд из списка (Nike, Adidas, Puma, Reebok) или напишите 'Любой'."
    await update.message.reply_text(response)

async def handle_price(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str, intent: str):
    user_text_lower = user_text.lower()
    max_price = None
    
    if intent == 'any_budget' or 'любой' in user_text_lower or 'не важно' in user_text_lower:
        max_price = None
    else:
        # Ищем обычные числа в сообщении для бюджета в рублях
        numbers = re.findall(r'\d+', user_text_lower.replace(' ', ''))
        if numbers:
            max_price = float(numbers[0])
            
    context.user_data['max_price'] = max_price
    context.user_data['awaiting_price'] = False
    
    # Запускаем поиск в БД
    shoes_list = search_shoes(
        context.user_data.get('shoes_type'),
        context.user_data.get('brand'),
        max_price
    )
    
    if shoes_list:
        response = format_shoes_list(shoes_list)
        response += "Вам нравится какой-нибудь вариант?"
        context.user_data['waiting_for_shoes_answer'] = True 
        context.user_data['last_shoes'] = shoes_list
    else:
        response = "К сожалению, не нашёл обуви по Вашим точным критериям.\n\nПоказать другие модели? (изменим бренд или бюджет)\n\nИли напишите 'Хочу купить обувь', чтобы начать новый поиск."
        context.user_data.clear()
        
    await update.message.reply_text(response)
    save_dialog(update.effective_user.id, user_text, response)

async def handle_answer_after_shoes(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str, intent: str):
    user_text_lower = user_text.lower()
    
    if intent == "yes" or user_text_lower in ["да", "давай", "давайте", "хорошо", "ага", "конечно", "устроит", "нравится"]:
        response = "Замечательно! 🎉 Будем рады видеть Вас снова. По всем вопросам оформления заказа обращайтесь к менеджеру.\n\nЧем ещё я могу Вам помочь?"
        context.user_data.clear()  
    elif intent == "no" or user_text_lower in ["нет", "не", "не нравится", "не устроит"]:
        response = "Понял Вас. Давайте попробуем изменить параметры поиска (тип обуви, бренд или цену).\n\nНапишите 'Хочу купить обувь', чтобы начать заново."
        context.user_data.clear()
    else:
        response = "Рад был помочь! Если захотите посмотреть другие модели — просто напишите 'Хочу купить обувь'."
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
    intent, auto_response = process_message(transcribed_text)
    
    # Голосовой перехват шагов
    if context.user_data.get('awaiting_type'):
        await handle_shoes_type(update, context, transcribed_text, intent)
        if context.user_data.get('awaiting_brand'):
            answer_text = "Понял. Теперь скажите, какой бренд ищете: Nike, Adidas, Puma, Reebok или любой?"
            voice_path = text_to_voice(answer_text)
            if voice_path: await update.message.reply_voice(voice=open(voice_path, 'rb'))
        return
        
    elif context.user_data.get('awaiting_brand'):
        await handle_brand(update, context, transcribed_text, intent)
        if context.user_data.get('awaiting_price'):
            answer_text = "Отлично! Назовите ваш максимальный бюджет в рублях."
            voice_path = text_to_voice(answer_text)
            if voice_path: await update.message.reply_voice(voice=open(voice_path, 'rb'))
        return
        
    elif context.user_data.get('awaiting_price'):
        await handle_price(update, context, transcribed_text, intent)
        return   

    # Стартовые голосовые триггеры
    if "обув" in transcribed_text or "купить" in transcribed_text or intent in ["buy_shoes", "buy_house"]:
        answer_text = "Понял вас! Давайте подберём обувь. Скажите, какой тип вас интересует: кроссовки, кеды, туфли или ботинки?"
        context.user_data['awaiting_type'] = True
    elif intent == "yes" or "да" in transcribed_text.lower():
        answer_text = "Отлично! Какой тип обуви вас интересует: кроссовки, кеды, туфли или ботинки?"
        context.user_data['awaiting_type'] = True
    else:
        answer_text = auto_response if auto_response else "Понял. Если хотите подобрать обувь, просто скажите 'Хочу купить обувь'."
        
    voice_path = text_to_voice(answer_text)
    if voice_path:
        await update.message.reply_voice(voice=open(voice_path, 'rb'))
    save_dialog(user_id, f"[VOICE] {transcribed_text}", answer_text)

def main():
    request_config = HTTPXRequest(proxy=None)
    app = Application.builder().token(TOKEN).request(request_config).build()    
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    print("Бот запущен!")
    app.run_polling()

if __name__ == '__main__':
    main()