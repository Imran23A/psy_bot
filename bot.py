from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Set up the logging module to see logs from the Telegram library.
import logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Replace 'YOUR_BOT_TOKEN' with the token you obtained from BotFather.
TOKEN = '5743367242:AAFi5ntJ-4bgwp5uV4Rc4qhUMmWe6ODxDAQ'
updater = Updater(TOKEN, use_context=True)
dispatcher = updater.dispatcher

# Dictionary to store user responses
user_responses = {}

def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    user_id = user.id

    # Initialize user's examination responses
    user_responses[user_id] = {}

    update.message.reply_text(f"Hello {user.first_name}! I am Psy_exam_bot, your emotional and mental health examiner. Send /help to see the available commands.")

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text("Here are the available commands:\n"
                              "/start - Start the bot and get a greeting.\n"
                              "/help - Get help and see the available commands.\n"
                              "/reset - Reset the examination and start over.")

def handle_message(update: Update, context: CallbackContext):
    user = update.message.from_user
    user_id = user.id

    # Get the number of questions answered
    num_questions_answered = len(user_responses[user_id])

    # List of questions to ask the user
    questions = [
        "1. How are you feeling today?",
        "2. On a scale of 1 to 10, how happy are you?",
        "3. How would you rate your stress level right now?",
    ]

    if num_questions_answered < len(questions):
        # Ask the next question
        update.message.reply_text(questions[num_questions_answered])
    else:
        # If all questions answered, thank the user
        update.message.reply_text("Thank you for completing the examination! Your responses have been recorded.")

def process_response(update: Update, context: CallbackContext):
    user = update.message.from_user
    user_id = user.id

    # Get the number of questions answered
    num_questions_answered = len(user_responses[user_id])

    # List of questions to ask the user
    questions = [
        "1. How are you feeling today?",
        "2. On a scale of 1 to 10, how happy are you?",
        "3. How would you rate your stress level right now?",
    ]

    # Store the user's response to the corresponding question
    user_responses[user_id][num_questions_answered + 1] = update.message.text

    # Check if all questions have been answered
    if num_questions_answered + 1 < len(questions):
        # Ask the next question
        update.message.reply_text(questions[num_questions_answered + 1])
    else:
        # If all questions answered, thank the user
        update.message.reply_text("Thank you for completing the examination! Your responses have been recorded.")

def reset(update: Update, context: CallbackContext):
    user = update.message.from_user
    user_id = user.id

    # Reset user's examination responses
    user_responses[user_id] = {}
    update.message.reply_text("Examination reset. Please answer the first question: How are you feeling today?")

# Add the command and message handlers to the dispatcher.
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_command))
dispatcher.add_handler(CommandHandler("reset", reset))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, process_response))

def main():
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
    