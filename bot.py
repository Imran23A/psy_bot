from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Set up the logging module to see logs from the Telegram library.
import logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Replace 'YOUR_BOT_TOKEN' with the token you obtained from BotFather.
TOKEN = '5743367242:AAFi5ntJ-4bgwp5uV4Rc4qhUMmWe6ODxDAQ'
updater = Updater(TOKEN, use_context=True)
dispatcher = updater.dispatcher

def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    update.message.reply_text(f"Hello {user.first_name}! I am Psy_exam_bot, your emotional and mental health examiner. Send /help to see the available commands.")

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text("Here are the available commands:\n"
                              "/start - Start the bot and get a greeting.\n"
                              "/help - Get help and see the available commands.")

def handle_message(update: Update, context: CallbackContext):
    user = update.message.from_user
    update.message.reply_text("Welcome! Let's start the emotional and mental health examination.\n"
                              "Please answer the following questions:\n"
                              "1. How are you feeling today?\n"
                              "2. On a scale of 1 to 10, how happy are you?\n"
                              "3. How would you rate your stress level right now?")

# Add the command and message handlers to the dispatcher.
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_command))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

def main():
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
