import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, CallbackQueryHandler, filters
import speech_recognition as sr
from pydub import AudioSegment
import openai
import sqlite3
import os
import configparser
import sys
import whisper

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Установите уровень логирования для httpx на WARNING, чтобы скрыть информационные сообщения
logging.getLogger("httpx").setLevel(logging.WARNING)

# Загрузка конфигурации
config = configparser.ConfigParser()
config.read('config.ini')

# Получение токенов из конфигурации
TELEGRAM_BOT_TOKEN = config['DEFAULT']['TELEGRAM_BOT_TOKEN']
OPENAI_API_KEY = config['DEFAULT']['OPENAI_API_KEY']

# Инициализация базы данных
conn = sqlite3.connect('messages.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS messages
             (date TEXT, author TEXT, summary TEXT, processed_text TEXT, read_status INTEGER)''')
conn.commit()

# Set the path to the ffmpeg executable
AudioSegment.converter = r"C:\Users\ser\AppData\Local\ffmpegio\ffmpeg-downloader\ffmpeg\bin\ffmpeg.exe"

# Check for -test and -local parameters
is_test_mode = '-test' in sys.argv
is_local_mode = '-local' in sys.argv

# Функция для транскрипции аудио с использованием Whisper
def transcribe_audio(file_path):
    try:
        logging.info(f"Начало транскрипции аудио с Whisper: {file_path}")
        model_name = "base" if is_test_mode else "large"  # Используем базовую модель в тестовом режиме
        model = whisper.load_model(model_name)  # Use the appropriate model
        result = model.transcribe(file_path)
        text = result['text']
        logging.info("Транскрипция с Whisper завершена успешно.")
        return text
    except Exception as e:
        logging.error(f"Ошибка транскрипции аудио с Whisper: {e}")
        return ""

# Функция для обработки текста AI
def process_text(text):
    try:
        openai.api_key = OPENAI_API_KEY
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Use a supported model
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Summarize the following text into bullet points and clean it up:\n\n{text}"}
            ]
        )
        summary = response.choices[0].message['content'].strip()
        return summary, text  # Возвращаем краткий пересказ и очищенный текст
    except Exception as e:
        logging.error(f"Ошибка обработки текста AI: {e}")
        return "", text

# Обработчик команды /start
def start(update: Update, context: CallbackContext) -> None:
    keyboard = [[InlineKeyboardButton("Получить непрочитанные сообщения", callback_data='get_unread')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Привет! Я ваш бот для обработки голосовых сообщений.', reply_markup=reply_markup)

# Function to split a message into chunks
def split_message(message, max_length=4096):
    return [message[i:i + max_length] for i in range(0, len(message), max_length)]

# Обработчик нажатия кнопки
async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()  # Используем await

    if query.data == 'get_unread':
        c.execute("SELECT * FROM messages WHERE read_status=0 ORDER BY date ASC")
        messages = c.fetchall()
        if messages:
            for message in messages:
                full_message = f"Автор: {message[1]}\nКраткий пересказ: {message[2]}\nОбработанный текст: {message[3]}"
                # Split the message if it's too long
                message_chunks = split_message(full_message)
                all_sent = True  # Флаг для проверки успешности отправки всех частей сообщения
                for chunk in message_chunks:
                    try:
                        await query.message.reply_text(chunk)  # Используем await
                    except Exception as e:
                        logging.error(f"Ошибка отправки сообщения: {e}")
                        all_sent = False
                        break
                if all_sent:
                    c.execute("UPDATE messages SET read_status=1 WHERE date= ?", (message[0],))
            conn.commit()
        else:
            await query.message.reply_text("Нет непрочитанных сообщений.")  # Используем await

# Обработчик новых сообщений
async def handle_message(update: Update, context: CallbackContext) -> None:
    voice = update.message.voice
    if voice:
        # Скачиваем аудиофайл
        file = await context.bot.get_file(voice.file_id)  # Используем await
        file_path = "voice.ogg"
        await file.download_to_drive(file_path)  # Используем правильный метод для загрузки

        # Транскрибируем аудио
        text = transcribe_audio(file_path)

        if is_local_mode:
            # В локальном режиме используем транскрипцию как обработанный текст
            summary = "<none>"
            processed_text = text
        else:
            # Обрабатываем текст через OpenAI
            summary, processed_text = process_text(text)

        # Сохраняем в базу данных
        c.execute("INSERT INTO messages (date, author, summary, processed_text, read_status) VALUES (?, ?, ?, ?, ?)",
                  (update.message.date, update.message.from_user.username, summary, processed_text, 0))
        conn.commit()

        await update.message.reply_text("Сообщение обработано и сохранено в базе данных.")  # Используем await

        # Удаляем временные файлы, если не в режиме тестирования
        if not is_test_mode:
            if os.path.exists(file_path):
                os.remove(file_path)

def main():
    # Create a Bot instance
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    # Initialize the Application with the Bot instance
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.VOICE, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main() 