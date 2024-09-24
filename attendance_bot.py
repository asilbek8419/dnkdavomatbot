import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters
import pandas as pd
from datetime import datetime
import pytz
from tabulate import tabulate  # Для форматирования таблицы


# Загружаем переменные окружения из .env файла
load_dotenv()

# Читаем токен бота из .env
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Ваш ID для уведомлений
YOUR_CHAT_ID = 72215648  # Замените на ваш реальный chat_id

# Инициализация таблицы посещений
attendance = pd.DataFrame(columns=['Employee', 'Check-in Time', 'Status', 'Reason', 'Delay (minutes)'])

# Клавиатура с кнопками "Check-in" и "Late"
main_keyboard = ReplyKeyboardMarkup(
    [[KeyboardButton("Check-in"), KeyboardButton("Late")]],
    resize_keyboard=True,
    one_time_keyboard=True
)

# Функция для старта бота
async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    start_keyboard = ReplyKeyboardMarkup([[KeyboardButton("Start")]], resize_keyboard=True)
    
    await update.message.reply_text(
        f'Привет, {user.username}! Нажми кнопку "Start", чтобы продолжить.',
        reply_markup=start_keyboard
    )

# Обработчик нажатия на кнопку "Start"
async def handle_start_button(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f'{user.username}, выберите действие:',
        reply_markup=main_keyboard
    )

# Установите временную зону Ташкента
TASHKENT_TZ = pytz.timezone('Asia/Tashkent')

# Функция для отметки прибытия
async def checkin(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    now = datetime.now(TASHKENT_TZ)
    attendance.loc[len(attendance)] = [user.username, now, 'Во время', '', 0]
    await update.message.reply_text(f'{user.username}, вы отметились в {now.strftime("%Y-%m-%d %H:%M:%S")}')

# Функция для отметки опоздания
async def late(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    await update.message.reply_text(f'{user.username}, введите причину опоздания и количество минут (например: "Пробка 15").')

# Обработчик для ввода причины опоздания и количества минут
async def handle_late_response(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    try:
        message_text = update.message.text
        reason, delay = message_text.rsplit(' ', 1)
        delay = int(delay)
        now = datetime.now(TASHKENT_TZ)  # Используем ту же временную зону
        attendance.loc[len(attendance)] = [user.username, now, 'Опоздание', reason, delay]
        
        await update.message.reply_text(f'{user.username}, вы отметили опоздание в {now.strftime("%Y-%m-%d %H:%M:%S")}. Причина: {reason}, Опоздание: {delay} минут.')
        
        # Отправка уведомления вам в Telegram
        await context.bot.send_message(chat_id=YOUR_CHAT_ID, 
                                       text=f'{user.username} отметил опоздание в {now.strftime("%Y-%m-%d %H:%M:%S")}. Причина: {reason}, Опоздание: {delay} минут.')
    except ValueError:
        await update.message.reply_text('Ошибка. Убедитесь, что вы ввели причину и количество минут корректно, например: "Пробка 15".')

# Функция для получения таблицы за текущий день
async def get_today_table(update: Update, context: CallbackContext) -> None:
    now = datetime.now()
    today = now.date()
    
    # Фильтрация записей по текущей дате
    today_attendance = attendance[attendance['Check-in Time'].dt.date == today]
    
    if today_attendance.empty:
        await update.message.reply_text("Сегодня нет записей о посещении.")
    else:
        # Форматируем таблицу для красивого вывода
        today_attendance.columns = ['Сотрудник', 'Время отметки', 'Статус', 'Причина', 'Опоздание (минуты)']
        formatted_table = tabulate(today_attendance, headers='keys', tablefmt='grid', showindex=False)
        await update.message.reply_text(f"Посещения за сегодня:\n\n```{formatted_table}```", parse_mode='Markdown')

# Функция для получения всей таблицы посещений
async def get_table(update: Update, context: CallbackContext) -> None:
    if attendance.empty:
        await update.message.reply_text("Данные о посещениях отсутствуют.")
    else:
        # Форматируем таблицу для красивого вывода
        attendance.columns = ['Сотрудник', 'Время отметки', 'Статус', 'Причина', 'Опоздание (минуты)']
        formatted_table = tabulate(attendance, headers='keys', tablefmt='grid', showindex=False)
        await update.message.reply_text(f"Все посещения:\n\n```{formatted_table}```", parse_mode='Markdown')

# Функция для очистки данных посещений
async def clear_attendance(update: Update, context: CallbackContext) -> None:
    global attendance  # Указываем, что будем изменять глобальную переменную
    attendance = pd.DataFrame(columns=['Сотрудник', 'Время отметки', 'Статус', 'Причина', 'Опоздание (минуты)'])
    await update.message.reply_text("Все данные посещений были успешно очищены.")

# Основная функция для запуска бота
def main() -> None:
    # Убедитесь, что токен успешно загружен из .env
    if TELEGRAM_TOKEN is None:
        raise ValueError("Токен Telegram не найден. Убедитесь, что файл .env правильно настроен.")

    # Инициализация бота
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("get_today_table", get_today_table))
    application.add_handler(CommandHandler("get_table", get_table))
    application.add_handler(CommandHandler("clear", clear_attendance))  # Команда для очистки данных

    # Обработка кнопок
    application.add_handler(MessageHandler(filters.Regex("Start"), handle_start_button))  # Обработка нажатия на кнопку "Start"
    application.add_handler(MessageHandler(filters.Regex("Check-in"), checkin))  # Обработка нажатия на кнопку "Check-in"
    application.add_handler(MessageHandler(filters.Regex("Late"), late))  # Обработка нажатия на кнопку "Late"
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_late_response))  # Обработка текста для причины опоздания

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
