import logging
import csv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, ConversationHandler, CallbackQueryHandler
import datetime

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# State definitions for top-level conversation
SELECTING_QUESTIONS = 1

# Constants for this example
QUESTIONS_FILE = "questions.tsv"
RESULTS_FILE = "results.csv"
QUESTIONS_PER_TEST = 21

# A dictionary containing the questions and options read from the questions.tsv file
questions = {}


def read_questions_from_file():
    try:
        with open(QUESTIONS_FILE, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            for line in lines:
                data = line.strip().split('\t')
                if len(data) == 5:
                    question = data[0]
                    options = data[1:]
                    questions[question] = options
    except FileNotFoundError:
        raise Exception(f"Failed to read questions from the file '{QUESTIONS_FILE}'. Make sure it exists.")
    return questions


def start(update: Update, _: CallbackContext) -> int:
    user_id = update.effective_user.id
    user_data = _.user_data.setdefault(user_id, {})

    # Check if the user is new or in the middle of a test
    if 'current_question' not in user_data:
        # New user, show the "Start Test" button
        keyboard = [
            [InlineKeyboardButton("Start Test", callback_data='start_test')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text("Hello! I'm your depression test bot. How can I assist you?", reply_markup=reply_markup)
    else:
        # User in the middle of a test, ask if they want to cancel the ongoing test
        keyboard = [
            [InlineKeyboardButton("Cancel Current Test", callback_data='cancel_test')],
            [InlineKeyboardButton("Start New Test", callback_data='start_test')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text("You have an ongoing test. Do you want to cancel it and start a new test?",
                                  reply_markup=reply_markup)

    return SELECTING_QUESTIONS


def delete_message(update: Update, message_id: int):
    try:
        update.effective_chat.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
    except Exception as e:
        logger.warning(f"Failed to delete message {message_id}: {e}")


def start_test_button(update: Update, _: CallbackContext):
    # Handle the "Start Test" button press
    return start_exam(update, _)
    


def handle_start_test_command(update: Update, _: CallbackContext):
    # Trigger the start_exam function when the /start_test command is used
    return start_exam(update, _)


def start_exam(update: Update, _: CallbackContext):
    user_id = update.effective_user.id
    user_data = _.user_data.setdefault(user_id, {})

    # Check if the user is already in the middle of a test
    if 'current_question' in user_data:
        # Delete the previous test messages
        previous_message_id = user_data.get('previous_message')
        if previous_message_id:
            delete_message(update, previous_message_id)

        # Clear ongoing test data to start a new one
        user_data.clear()

    # Start a new test
    read_questions_from_file()
    user_data['current_question'] = 1  # Start from the first question
    user_data['answers'] = {}  # Initialize or reset answers dictionary

    # Generate and send the first question
    send_question(update, _)

    return SELECTING_QUESTIONS


def send_question(update: Update, _: CallbackContext):
    user_id = update.effective_user.id
    user_data = _.user_data.get(user_id)
    if not user_data:
        return

    current_question_number = user_data.get('current_question')
    if not current_question_number or current_question_number > QUESTIONS_PER_TEST:
        # Test is completed, show results as a "fake" last question
        show_results(update, _)
        return SELECTING_QUESTIONS

    question = list(questions.keys())[current_question_number - 1]
    options = questions[question]

    keyboard = []
    for idx, option in enumerate(options):
        keyboard.append([InlineKeyboardButton(option, callback_data=str(idx))])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # If there's a previous message, edit it, otherwise send a new one
    previous_message_id = user_data.get('previous_message')
    if previous_message_id:
        update.callback_query.edit_message_text(
            text=question,
            reply_markup=reply_markup
        )
    else:
        message = update.effective_message.reply_text(question, reply_markup=reply_markup)
        user_data['previous_message'] = message.message_id


def handle_answer(update: Update, _: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    user_id = update.effective_user.id
    user_data = _.user_data.get(user_id)
    if not user_data:
        return ConversationHandler.END

    question_number = user_data.get('current_question')
    if not question_number or question_number > QUESTIONS_PER_TEST:
        # Should not happen, but just in case
        show_results(update, _)
        return SELECTING_QUESTIONS

    chosen_option = int(query.data)
    user_data['answers'][question_number] = chosen_option
    user_data['current_question'] += 1

    # Send the next question
    send_question(update, _)

    return SELECTING_QUESTIONS


def show_results(update: Update, _: CallbackContext):
    user_id = update.effective_user.id
    user_data = _.user_data.get(user_id)
    if not user_data:
        return

    answers = user_data.get('answers', {})
    total_score = sum(answers.values())

    result = ""
    if total_score <= 9:
        result = "You have no depressive symptoms."
    elif 10 <= total_score <= 15:
        result = "You may have mild depression (subdepression)."
    elif 16 <= total_score <= 19:
        result = "You have moderate depression."
    elif 20 <= total_score <= 29:
        result = "You have severe depression (moderate severity)."
    else:
        result = "You have severe depression."

    # Save results in CSV file
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(RESULTS_FILE, 'a', newline='') as csvfile:
        fieldnames = ['user_id', 'timestamp', 'result']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow({'user_id': user_id, 'timestamp': timestamp, 'result': total_score})

    # If there was a previous message, edit it with the results, otherwise send a new message
    previous_message_id = user_data.get('previous_message')
    if previous_message_id:
        update.callback_query.edit_message_text(
            text=f"Test completed! Your results: {result}",
            reply_markup=None  # Remove the "Cancel" button from the message
        )
    else:
        update.effective_message.reply_text(f"Test completed! Your results: {result}")

    # Clear user data after showing results
    user_data.clear()


def main():
    # Create the Updater and pass it your bot's token
    with open("token.txt", "r") as file:
        token = file.read().strip()

    updater = Updater(token, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with the state SELECTING_QUESTIONS
    conversation_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
        ],
        states={
            SELECTING_QUESTIONS: [
                CallbackQueryHandler(start_test_button, pattern='^start_test$'),  # Handle the button press
                CallbackQueryHandler(handle_answer, pattern='^[0-3]$'),
            ],
        },
        fallbacks=[]
    )

    # Add a handler for the /start_test command
    dp.add_handler(CommandHandler('start_test', handle_start_test_command))

    dp.add_handler(conversation_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT, SIGTERM, or SIGABRT
    updater.idle()

if __name__ == '__main__':
    main()
