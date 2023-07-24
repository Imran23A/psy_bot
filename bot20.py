import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, Filters

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)
logger = logging.getLogger(__name__)

# Your bot's token (replace with your actual token)
BOT_TOKEN = '6089879592:AAGZr41ROtAtSuz2t8hu66Hrdnevr28w15w'

# Function to handle the /start command
async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    await update.message.reply_html(
        f"Hello, {user.first_name}!\n"
        "Welcome to your bot.\n"
        "You can start interacting with the bot now."
    )

# Function to handle text messages from the user
async def handle_text_message(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    text = update.message.text
    await update.message.reply_html(
        f"Hi, {user.first_name}!\n"
        f"You sent: {text}"
    )

def main():
    # Create the Updater and pass it your bot's token
    updater = Updater(BOT_TOKEN)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add command handler for the /start command
    dp.add_handler(CommandHandler("start", start))

    # Add message handler for text messages
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text_message))

    # Start the Bot
    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT, SIGTERM, or SIGABRT
    updater.idle()

if __name__ == '__main__':
    main()
