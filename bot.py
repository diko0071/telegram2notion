from telegram.ext import Updater, CommandHandler
from telegram_handler import message_handler
from dotenv import load_dotenv
import os

load_dotenv()

def start(update, context):
    update.message.reply_text('Hey! I\'m a bot that can help you to manage task for you.')

def main():
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    if not TELEGRAM_TOKEN:
        print("Error: TELEGRAM_TOKEN is not set.")
        return
    
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(message_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
