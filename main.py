import random
import sqlite3
import re
from telebot import TeleBot, types
from telebot.util import quick_markup
from datetime import datetime

BOT_TOKEN = '8512433616:AAH7L3bI0Tgj4Pn3H7mkn_1omg9Dj_5pJTk' #бот токен
ADMIN_ID = 7501355771#админ айди
CHANNEL_ID = -1002934522777 #айди канала
CHANNEL_LINK = 'https://t.me/+bHWt__ebsy1hMzQ6' #ссылка на канал
DEFAULT_RANDOM_RANGE = (20000, 50000)
USERS_PER_PAGE = 15
SUGGESTIONS_PER_PAGE = 5

bot = TeleBot(BOT_TOKEN)

def init_db():
    conn = sqlite3.connect('gift.db', check_same_thread=False)
    cursor = conn.cursor()

   
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stats (
        user_id INTEGER PRIMARY KEY,
        search_count INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS suggestions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        url TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS gifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        url_template TEXT NOT NULL,
        random_range TEXT DEFAULT '20000-50000',
        added_by INTEGER,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(added_by) REFERENCES users(user_id)
    )
    ''')

    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False

def extract_random_range(text):
    match = re.search(r'\{(\d+)-(\d+)\}', text)
    if match:
        return (int(match.group(1)), int(match.group(2)))
    return None

def format_link_template(url):
    if '{random}' not in url:
        if url.endswith('-'):
            return url + '{random}'
        return url + '-{random}'
    return url

def create_main_menu(user_id):
    buttons = {
        '🎁 Начать поиск NFT': {'callback_data': 'start_search'},
        '💡 Предложить NFT': {'callback_data': 'suggest_gift'},
        '📊 Моя статистика': {'callback_data': 'my_stats'}
    }
    if user_id == ADMIN_ID:
        buttons['👑 Админ панель'] = {'callback_data': 'admin_panel'}
    return quick_markup(buttons, row_width=1)

def create_back_button(target):
    return quick_markup({'🔙 Назад': {'callback_data': target}}, row_width=1)

def create_admin_menu():
    return quick_markup({
        '📢 Рассылка': {'callback_data': 'start_broadcast'},
        '👥 Пользователи': {'callback_data': 'show_users_1'},
        '🎁 Подарки': {'callback_data': 'manage_gifts'},
        '📥 Предложения': {'callback_data': 'show_suggestions_1'},
        '📊 Статистика': {'callback_data': 'stats'},
        '🚪 В главное меню': {'callback_data': 'main_menu'}
    }, row_width=2)

def create_gifts_menu():
    cursor.execute('SELECT name FROM gifts WHERE status="active" ORDER BY name')
    gifts = [gift[0] for gift in cursor.fetchall()]
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    
    for i in range(0, len(gifts), 2):
        if i+1 < len(gifts):
            buttons.append(types.InlineKeyboardButton(f"🎁 {gifts[i]}", callback_data=f"select_gift_{gifts[i]}"))
            buttons.append(types.InlineKeyboardButton(f"🎁 {gifts[i+1]}", callback_data=f"select_gift_{gifts[i+1]}"))
        else:
            buttons.append(types.InlineKeyboardButton(f"🎁 {gifts[i]}", callback_data=f"select_gift_{gifts[i]}"))
    
    for i in range(0, len(buttons), 2):
        if i+1 < len(buttons):
            markup.row(buttons[i], buttons[i+1])
        else:
            markup.add(buttons[i])
    
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="main_menu"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user = message.from_user
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)',
                  (user.id, user.username, user.first_name, user.last_name))
    cursor.execute('INSERT OR IGNORE INTO stats (user_id) VALUES (?)', (user.id,))
    conn.commit()

    if not is_subscribed(user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Подписаться на канал", url=CHANNEL_LINK))
        markup.add(types.InlineKeyboardButton("✅ Проверить подписку", callback_data="check_subscription"))
        
        bot.send_message(
            message.chat.id,
            f"✨ Добро пожаловать, {user.first_name}!\n\n"
            "🚀 Для доступа к NFT Gift Parser необходимо подписаться на наш канал\n\n"
            "📚 Здесь вы найдете:\n"
            "• Уникальные NFT подарки 🎁\n"
            "• Автоматическую генерацию ссылок 🔗\n"
            "• Возможность предложить свои NFT 💡",
            reply_markup=markup
        )
        return

    bot.send_message(
        message.chat.id,
        f"🎉 Добро пожаловать в NFT Gift Parser, {user.first_name}!\n\n"
        "✨ Я помогу вам находить уникальные NFT-подарки\n\n"
        "🔍 <b>Возможности:</b>\n"
        "• Поиск рандомных NFT 🎲\n"
        "• Генерация уникальных ссылок 🔗\n"
        "• Предложение своих NFT 💡\n"
        "• Отслеживание статистики 📊",
        parse_mode='HTML',
        reply_markup=create_main_menu(user.id)
    )

@bot.callback_query_handler(func=lambda call: call.data == 'check_subscription')
def check_subscription(call):
    if is_subscribed(call.from_user.id):
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="✅ Отлично! Вы подписаны на канал!\n\n"
                 "🚀 Теперь вам доступны все функции бота для поиска NFT подарков!",
            reply_markup=create_main_menu(call.from_user.id)
        )
    else:
        bot.answer_callback_query(call.id, "❌ Вы еще не подписаны на канал!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == 'my_stats')
def my_stats(call):
    user_id = call.from_user.id
    cursor.execute('SELECT search_count FROM stats WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    search_count = result[0] if result else 0
    
    cursor.execute('SELECT COUNT(*) FROM suggestions WHERE user_id = ? AND status = "approved"', (user_id,))
    approved_suggestions = cursor.fetchone()[0]
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"📊 <b>Ваша статистика</b>\n\n"
             f"🔍 Поисков выполнено: {search_count}\n"
             f"✅ Одобренных предложений: {approved_suggestions}\n"
             f"🎯 Уровень активности: {'⭐' * min(5, search_count // 10 + 1)}\n\n"
             f"💡 Продолжайте искать и предлагать новые NFT!",
        parse_mode='HTML',
        reply_markup=create_back_button('main_menu')
    )

@bot.callback_query_handler(func=lambda call: call.data == 'suggest_gift')
def suggest_gift(call):
    if not is_subscribed(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Подпишитесь на канал для доступа!", show_alert=True)
        return

    msg = bot.send_message(
        call.message.chat.id,
        "💡 <b>Предложить новый NFT</b>\n\n"
        "📝 Отправьте данные в любом удобном формате:\n\n"
        "• <b>Просто ссылка:</b>\n"
        "https://t.me/nft/EvilEye-37540\n\n"
        "• <b>Название + ссылка:</b>\n"
        "EvilEye https://t.me/nft/EvilEye-37540\n\n"
        "• <b>С диапазоном:</b>\n"
        "EvilEye https://t.me/nft/EvilEye- {10000-50000}\n\n"
        "🚫 Можно добавить только один NFT за раз",
        parse_mode='HTML',
        reply_markup=create_back_button('main_menu')
    )
    bot.register_next_step_handler(msg, process_suggestion)

def process_suggestion(message):
    user = message.from_user
    text = message.text.strip()
    
    if text.lower() in ['/start', '/cancel', 'отмена']:
        bot.send_message(message.chat.id, "❌ Отменено", reply_markup=create_main_menu(user.id))
        return
    
    
    name = "Без названия"
    url = text
    random_range = None
    
   
    range_match = re.search(r'\{(\d+)-(\d+)\}', text)
    if range_match:
        random_range = f"{range_match.group(1)}-{range_match.group(2)}"
        text = re.sub(r'\s*\{\d+-\d+\}\s*', '', text)
    
    
    url_match = re.search(r'(https?://\S+)', text)
    if url_match:
        url = url_match.group(1)
        # Извлекаем название из оставшегося текста или из ссылки
        remaining_text = text.replace(url, '').strip()
        if remaining_text:
            name = remaining_text
        else:
            
            name = url.split('/')[-1].split('-')[0] if '/' in url else "Без названия"
    
    # Форматируем URL
    if '{random}' not in url:
        url = format_link_template(url)
    
    try:
        cursor.execute(
            'INSERT INTO suggestions (user_id, name, url) VALUES (?, ?, ?)',
            (user.id, name, url)
        )
        conn.commit()
        
        
        admin_text = (
            "🆕 <b>Новое предложение NFT</b>\n\n"
            f"👤 От: @{user.username if user.username else user.id}\n"
            f"🎁 Название: {name}\n"
            f"🔗 Ссылка: {url}\n"
            f"📅 Время: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        
        bot.send_message(ADMIN_ID, admin_text, parse_mode='HTML')
        
        bot.send_message(
            message.chat.id,
            "✅ <b>Ваше предложение отправлено!</b>\n\n"
            f"🎁 <b>Название:</b> {name}\n"
            f"🔗 <b>Ссылка:</b> {url}\n\n"
            "⏳ Ожидайте проверки администратором",
            parse_mode='HTML',
            reply_markup=create_main_menu(user.id)
        )
    except Exception as e:
        print(f"Ошибка обработки предложения: {e}")
        bot.send_message(
            message.chat.id,
            "❌ Произошла ошибка при обработке предложения. Пожалуйста, попробуйте еще раз.",
            reply_markup=create_main_menu(user.id)
        )

@bot.callback_query_handler(func=lambda call: call.data == 'start_search')
def show_gifts(call):
    if not is_subscribed(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Подпишитесь на канал для доступа!", show_alert=True)
        return

    cursor.execute('SELECT COUNT(*) FROM gifts WHERE status="active"')
    count = cursor.fetchone()[0]
    
    if count == 0:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="📦 <b>Доступные NFT-подарки</b>\n\n"
                 "😔 Пока нет доступных подарков\n\n"
                 "💡 Вы можете предложить свой NFT первым!",
            parse_mode='HTML',
            reply_markup=create_back_button('main_menu')
        )
        return

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"📦 <b>Доступные NFT-подарки</b>\n\n"
             f"🎯 Выберите NFT для поиска:\n"
             f"📊 Всего доступно: {count} подарков",
        parse_mode='HTML',
        reply_markup=create_gifts_menu()
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('select_gift_'))
def select_gift(call):
    if not is_subscribed(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Подпишитесь на канал для доступа!", show_alert=True)
        return

    gift_name = call.data.split('_')[-1]
    cursor.execute('SELECT url_template, random_range FROM gifts WHERE name = ? AND status="active"', (gift_name,))
    gift = cursor.fetchone()
    
    if gift:
        start, end = map(int, gift[1].split('-'))
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('🎲 Сгенерировать ссылки', callback_data=f'generate_{gift_name}'))
        markup.add(types.InlineKeyboardButton('📋 Главное меню', callback_data='main_menu'))
        markup.add(types.InlineKeyboardButton('🔙 Назад к подаркам', callback_data='start_search'))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"🎁 <b>Выбран NFT:</b> {gift_name}\n\n"
                 f"🔢 <b>Диапазон ID:</b> {gift[1]}\n"
                 f"📊 <b>Возможных комбинаций:</b> {end - start + 1:,}\n\n"
                 f"🚀 Нажмите кнопку ниже для генерации случайных ссылок",
            parse_mode='HTML',
            reply_markup=markup
        )
    else:
        bot.answer_callback_query(call.id, "❌ NFT не найден!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith('generate_'))
def generate_links(call):
    if not is_subscribed(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Подпишитесь на канал для доступа!", show_alert=True)
        return

    gift_name = call.data.split('_')[-1]
    cursor.execute('SELECT url_template, random_range FROM gifts WHERE name = ? AND status="active"', (gift_name,))
    gift = cursor.fetchone()
    
    if gift:
        cursor.execute('UPDATE stats SET search_count = search_count + 1 WHERE user_id = ?', (call.from_user.id,))
        conn.commit()
        
        start, end = map(int, gift[1].split('-'))
        links = []
        
        for _ in range(30):
            random_num = random.randint(start, end)
            link = gift[0].replace('{random}', str(random_num))
            links.append(f"🎯 {random_num} - {link}")
        
        result = f"🎁 <b>Сгенерированные ссылки для {gift_name}:</b>\n\n" + "\n".join(links)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('🔄 Сгенерировать ещё', callback_data=f'generate_{gift_name}'))
        markup.add(types.InlineKeyboardButton('📋 Главное меню', callback_data='main_menu'))
        markup.add(types.InlineKeyboardButton('🔙 Назад к NFT', callback_data=f'select_gift_{gift_name}'))
        
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=result,
                parse_mode='HTML',
                reply_markup=markup
            )
        except:
            bot.send_message(
                call.message.chat.id,
                result,
                parse_mode='HTML',
                reply_markup=markup
            )
    else:
        bot.answer_callback_query(call.id, "❌ NFT не найден!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == 'admin_panel')
def admin_panel(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ У вас нет доступа!", show_alert=True)
        return

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="👑 <b>Админ-панель</b>\n\n"
             "⚙️ Управление ботом и мониторинг статистики",
        parse_mode='HTML',
        reply_markup=create_admin_menu()
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('show_users_'))
def show_users(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ У вас нет доступа!", show_alert=True)
        return

    page = int(call.data.split('_')[-1])
    offset = (page - 1) * USERS_PER_PAGE
    
    cursor.execute('''
        SELECT u.user_id, u.username, u.first_name, s.search_count 
        FROM users u LEFT JOIN stats s ON u.user_id = s.user_id
        ORDER BY s.search_count DESC
        LIMIT ? OFFSET ?
    ''', (USERS_PER_PAGE, offset))
    
    users = cursor.fetchall()
    total_users = cursor.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for i, user in enumerate(users, start=1):
        user_id, username, first_name, search_count = user
        num = (page-1)*USERS_PER_PAGE + i
        text = f"{num}. {first_name or ('@' + username) if username else 'Без имени'}"
        if search_count:
            text += f" ({search_count}🔍)"
        markup.add(types.InlineKeyboardButton(text, callback_data=f"user_{user_id}"))
    
    pagination_buttons = []
    if page > 1:
        pagination_buttons.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"show_users_{page-1}"))
    if offset + USERS_PER_PAGE < total_users:
        pagination_buttons.append(types.InlineKeyboardButton("Вперед ➡️", callback_data=f"show_users_{page+1}"))
    
    if pagination_buttons:
        markup.row(*pagination_buttons)
    
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_panel"))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"👥 <b>Пользователи</b> (Страница {page})\n\n"
             f"📊 Всего пользователей: {total_users}",
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('user_'))
def show_user_info(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ У вас нет доступа!", show_alert=True)
        return

    user_id = int(call.data.split('_')[-1])
    cursor.execute('''
        SELECT u.username, u.first_name, u.last_name, u.registered_at, s.search_count
        FROM users u LEFT JOIN stats s ON u.user_id = s.user_id
        WHERE u.user_id = ?
    ''', (user_id,))
    user = cursor.fetchone()
    
    if user:
        username, first_name, last_name, registered_at, search_count = user
        text = (
            f"👤 <b>Информация о пользователе</b>\n\n"
            f"🆔 <b>ID:</b> {user_id}\n"
            f"👤 <b>Имя:</b> {first_name or 'Не указано'}\n"
            f"📛 <b>Фамилия:</b> {last_name or 'Не указана'}\n"
            f"🔗 <b>Юзернейм:</b> @{username or 'Не указан'}\n"
            f"📅 <b>Дата регистрации:</b> {registered_at}\n"
            f"🔍 <b>Поисков NFT:</b> {search_count or 0}\n"
            f"⭐ <b>Активность:</b> {'⭐' * min(5, (search_count or 0) // 10 + 1)}"
        )
        
        bot.send_message(call.message.chat.id, text, parse_mode='HTML')
    else:
        bot.answer_callback_query(call.id, "❌ Пользователь не найден!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == 'manage_gifts')
def manage_gifts(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ У вас нет доступа!", show_alert=True)
        return

    cursor.execute('SELECT COUNT(*) FROM gifts WHERE status="active"')
    count = cursor.fetchone()[0]
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton('➕ Добавить NFT', callback_data='add_gifts'))
    markup.add(types.InlineKeyboardButton('➖ Удалить NFT', callback_data='delete_gifts_menu'))
    markup.add(types.InlineKeyboardButton('📋 Список NFT', callback_data='list_gifts'))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_panel"))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"🎁 <b>Управление NFT</b>\n\n"
             f"📊 Активных NFT: {count}",
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == 'list_gifts')
def list_gifts(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ У вас нет доступа!", show_alert=True)
        return

    cursor.execute('SELECT name, url_template, random_range FROM gifts WHERE status="active" ORDER BY name')
    gifts = cursor.fetchall()
    
    if not gifts:
        bot.answer_callback_query(call.id, "❌ Нет активных NFT!", show_alert=True)
        return
    
    text = "📋 <b>Список активных NFT:</b>\n\n"
    for i, (name, url, range_) in enumerate(gifts, 1):
        text += f"{i}. <b>{name}</b>\n   🔗 {url}\n   📊 {range_}\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == 'add_gifts')
def add_gifts(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ У вас нет доступа!", show_alert=True)
        return

    msg = bot.send_message(
        call.message.chat.id,
        "📝 <b>Добавление NFT</b>\n\n"
        "Отправьте данные в любом формате:\n\n"
        "• <b>Просто ссылка:</b>\n"
        "https://t.me/nft/MyNFT-\n\n"
        "• <b>Название + ссылка:</b>\n"
        "MyNFT https://t.me/nft/MyNFT-\n\n"
        "• <b>С диапазоном:</b>\n"
        "MyNFT https://t.me/nft/MyNFT- {10000-50000}\n\n"
        "• <b>Несколько NFT:</b>\n"
        "NFT1 https://t.me/nft/NFT1-\n"
        "NFT2 https://t.me/nft/NFT2- {20000-60000}",
        parse_mode='HTML',
        reply_markup=create_back_button('manage_gifts')
    )
    bot.register_next_step_handler(msg, process_gifts_input)

def process_gifts_input(message):
    if message.from_user.id != ADMIN_ID:
        return

    if message.text.lower() in ['/cancel', 'отмена']:
        bot.send_message(message.chat.id, "❌ Отменено", reply_markup=create_admin_menu())
        return

    text = message.text.strip()
    lines = text.split('\n')
    added_count = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        try:
            
            name = "Без названия"
            url = line
            random_range = f"{DEFAULT_RANDOM_RANGE[0]}-{DEFAULT_RANDOM_RANGE[1]}"
            
           
            range_match = re.search(r'\{(\d+)-(\d+)\}', line)
            if range_match:
                random_range = f"{range_match.group(1)}-{range_match.group(2)}"
                line = re.sub(r'\s*\{\d+-\d+\}\s*', '', line)
            
            
            url_match = re.search(r'(https?://\S+)', line)
            if url_match:
                url = url_match.group(1)
                # Извлекаем название из оставшегося текста
                remaining_text = line.replace(url, '').strip()
                if remaining_text:
                    name = remaining_text
                else:
                    
                    name = url.split('/')[-1].split('-')[0] if '/' in url else "Без названия"
            
           
            url = format_link_template(url)
            
            # Добавляем в базу
            cursor.execute(
                'INSERT OR IGNORE INTO gifts (name, url_template, random_range, added_by) VALUES (?, ?, ?, ?)',
                (name, url, random_range, message.from_user.id)
            )
            conn.commit()
            if cursor.rowcount > 0:
                added_count += 1
                
        except Exception as e:
            print(f"Ошибка обработки NFT: {e}")
            continue
    
    bot.send_message(
        message.chat.id,
        f"✅ Успешно добавлено {added_count} NFT!",
        reply_markup=create_admin_menu()
    )

@bot.callback_query_handler(func=lambda call: call.data == 'delete_gifts_menu')
def delete_gifts_menu(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ У вас нет доступа!", show_alert=True)
        return

    cursor.execute('SELECT name FROM gifts WHERE status="active" ORDER BY name')
    gifts = [gift[0] for gift in cursor.fetchall()]
    
    if not gifts:
        bot.answer_callback_query(call.id, "❌ Нет активных NFT!", show_alert=True)
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    
    for gift in gifts:
        buttons.append(types.InlineKeyboardButton(f"❌ {gift}", callback_data=f"delete_gift_{gift}"))
    
    for i in range(0, len(buttons), 2):
        if i+1 < len(buttons):
            markup.row(buttons[i], buttons[i+1])
        else:
            markup.add(buttons[i])
    
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="manage_gifts"))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🗑️ <b>Выберите NFT для удаления:</b>",
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_gift_'))
def delete_gift(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ У вас нет доступа!", show_alert=True)
        return

    gift_name = call.data.split('_')[-1]
    cursor.execute('UPDATE gifts SET status="deleted" WHERE name = ?', (gift_name,))
    conn.commit()
    
    bot.answer_callback_query(call.id, f"✅ NFT {gift_name} удалён!")
    delete_gifts_menu(call)

@bot.callback_query_handler(func=lambda call: call.data.startswith('show_suggestions_'))
def show_suggestions(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ У вас нет доступа!", show_alert=True)
        return

    page = int(call.data.split('_')[-1])
    offset = (page - 1) * SUGGESTIONS_PER_PAGE
    
    cursor.execute('''
        SELECT s.id, u.user_id, u.username, s.name, s.url, s.status, s.created_at
        FROM suggestions s JOIN users u ON s.user_id = u.user_id
        WHERE s.status = 'pending'
        ORDER BY s.created_at DESC
        LIMIT ? OFFSET ?
    ''', (SUGGESTIONS_PER_PAGE, offset))
    
    suggestions = cursor.fetchall()
    total_pending = cursor.execute('SELECT COUNT(*) FROM suggestions WHERE status="pending"').fetchone()[0]
    
    if not suggestions:
        bot.answer_callback_query(call.id, "✅ Нет ожидающих предложений!", show_alert=True)
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for i, (s_id, user_id, username, name, url, status, created_at) in enumerate(suggestions, start=1):
        num = (page-1)*SUGGESTIONS_PER_PAGE + i
        user = f"@{username}" if username else f"ID:{user_id}"
        date = created_at.split()[0] if created_at else "N/A"
        button_text = f"{num}. {name[:15]}{'...' if len(name) > 15 else ''} ({user}) [{date}]"
        markup.add(types.InlineKeyboardButton(button_text, callback_data=f"suggestion_{s_id}"))
    
    pagination_buttons = []
    if page > 1:
        pagination_buttons.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"show_suggestions_{page-1}"))
    if offset + SUGGESTIONS_PER_PAGE < total_pending:
        pagination_buttons.append(types.InlineKeyboardButton("Вперед ➡️", callback_data=f"show_suggestions_{page+1}"))
    
    if pagination_buttons:
        markup.row(*pagination_buttons)
    
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_panel"))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"📥 <b>Предложения NFT</b> (Страница {page})\n\n"
             f"⏳ Ожидающих: {total_pending}",
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('suggestion_'))
def show_suggestion(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ У вас нет доступа!", show_alert=True)
        return

    s_id = int(call.data.split('_')[-1])
    cursor.execute('''
        SELECT s.name, s.url, u.username, u.user_id, s.created_at
        FROM suggestions s JOIN users u ON s.user_id = u.user_id
        WHERE s.id = ?
    ''', (s_id,))
    suggestion = cursor.fetchone()
    
    if suggestion:
        name, url, username, user_id, created_at = suggestion
        user = f"@{username}" if username else f"ID:{user_id}"
        date = created_at if created_at else "N/A"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('✅ Одобрить', callback_data=f'approve_{s_id}'))
        markup.add(types.InlineKeyboardButton('❌ Отклонить', callback_data=f'reject_{s_id}'))
        markup.add(types.InlineKeyboardButton('🔙 Назад', callback_data='show_suggestions_1'))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"📨 <b>Предложение #{s_id}</b>\n\n"
                 f"👤 <b>От:</b> {user}\n"
                 f"📅 <b>Дата:</b> {date}\n"
                 f"🎁 <b>Название:</b> {name}\n"
                 f"🔗 <b>Ссылка:</b> {url}",
            parse_mode='HTML',
            reply_markup=markup
        )
    else:
        bot.answer_callback_query(call.id, "❌ Предложение не найдено!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_'))
def approve_suggestion(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ У вас нет доступа!", show_alert=True)
        return

    s_id = int(call.data.split('_')[-1])
    cursor.execute('SELECT name, url, user_id FROM suggestions WHERE id = ?', (s_id,))
    suggestion = cursor.fetchone()
    
    if suggestion:
        name, url, user_id = suggestion
        random_range = f"{DEFAULT_RANDOM_RANGE[0]}-{DEFAULT_RANDOM_RANGE[1]}"
        
       
        cursor.execute(
            'INSERT OR IGNORE INTO gifts (name, url_template, random_range, added_by) VALUES (?, ?, ?, ?)',
            (name, url, random_range, user_id)
        )
        

        cursor.execute('UPDATE suggestions SET status="approved" WHERE id = ?', (s_id,))
        conn.commit()
        
       
        try:
            bot.send_message(
                user_id,
                f"🎉 <b>Ваше предложение одобрено!</b>\n\n"
                f"🎁 <b>NFT:</b> {name}\n"
                f"🔗 <b>Ссылка:</b> {url}\n\n"
                "💫 Теперь ваш NFT доступен для поиска всем пользователям!",
                parse_mode='HTML'
            )
        except:
            pass
        
        bot.answer_callback_query(call.id, "✅ Предложение одобрено!")
        show_suggestions_1(call)
    else:
        bot.answer_callback_query(call.id, "❌ Предложение не найдено!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_'))
def reject_suggestion(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ У вас нет доступа!", show_alert=True)
        return

    s_id = int(call.data.split('_')[-1])
    cursor.execute('SELECT user_id, name FROM suggestions WHERE id = ?', (s_id,))
    suggestion = cursor.fetchone()
    
    if suggestion:
        user_id, name = suggestion
        cursor.execute('UPDATE suggestions SET status="rejected" WHERE id = ?', (s_id,))
        conn.commit()
        
        # Уведомляем пользователя
        try:
            bot.send_message(
                user_id,
                f"❌ <b>Ваше предложение отклонено</b>\n\n"
                f"🎁 <b>NFT:</b> {name}\n\n"
                "📝 Возможные причины:\n"
                "• NFT уже существует в базе\n"
                "• Неверный формат ссылки\n"
                "• Нарушение правил\n\n"
                "💡 Вы можете предложить другой NFT",
                parse_mode='HTML'
            )
        except:
            pass
        
        bot.answer_callback_query(call.id, "❌ Предложение отклонено!")
        show_suggestions_1(call)
    else:
        bot.answer_callback_query(call.id, "❌ Предложение не найдено!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == 'stats')
def show_stats(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ У вас нет доступа!", show_alert=True)
        return

    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM gifts WHERE status="active"')
    active_gifts = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(search_count) FROM stats')
    total_searches = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) FROM suggestions WHERE status="pending"')
    pending_suggestions = cursor.fetchone()[0]
    
    text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 <b>Всего пользователей:</b> {total_users}\n"
        f"🎁 <b>Активных NFT:</b> {active_gifts}\n"
        f"🔍 <b>Всего поисков:</b> {total_searches}\n"
        f"📥 <b>Ожидающих предложений:</b> {pending_suggestions}\n\n"
        f"🚀 <b>Активность:</b> {'🔥' * min(5, total_searches // 100 + 1)}"
    )
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        parse_mode='HTML',
        reply_markup=create_back_button('admin_panel')
    )

@bot.callback_query_handler(func=lambda call: call.data == 'main_menu')
def main_menu(call):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🎉 Добро пожаловать в NFT Gift Parser!\n\n"
             "✨ Я помогу вам находить уникальные NFT-подарки\n\n"
             "🔍 <b>Возможности:</b>\n"
             "• Поиск рандомных NFT 🎲\n"
             "• Генерация уникальных ссылок 🔗\n"
             "• Предложение своих NFT 💡\n"
             "• Отслеживание статистики 📊",
        parse_mode='HTML',
        reply_markup=create_main_menu(call.from_user.id)
    )

@bot.callback_query_handler(func=lambda call: call.data == 'start_broadcast')
def start_broadcast(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ У вас нет доступа!", show_alert=True)
        return

    msg = bot.send_message(
        call.message.chat.id,
        "📢 <b>Рассылка сообщения</b>\n\n"
        "Отправьте сообщение для рассылки всем пользователям:",
        parse_mode='HTML',
        reply_markup=create_back_button('admin_panel')
    )
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    success = 0
    failed = 0
    
    for user_id, in users:
        try:
            bot.copy_message(user_id, message.chat.id, message.message_id)
            success += 1
        except:
            failed += 1
    
    bot.send_message(
        message.chat.id,
        f"📊 <b>Результаты рассылки:</b>\n\n"
        f"✅ Успешно: {success}\n"
        f"❌ Не удалось: {failed}\n"
        f"📈 Охват: {success/(success+failed)*100:.1f}%",
        parse_mode='HTML',
        reply_markup=create_admin_menu()
    )

if __name__ == '__main__':
    print("🚀 NFT Gift Parser запущен!")
    bot.infinity_polling()
