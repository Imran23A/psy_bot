import logging
import csv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, ConversationHandler, CallbackQueryHandler
import warnings
import datetime  # Import the datetime module to fix the E0602 error
# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)
logger = logging.getLogger(__name__)

# State definitions for top-level conversation
SELECTING_QUESTIONS = 0

# Constants for this example
START_EXAM = "start_exam"
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
            [InlineKeyboardButton("Start Test", callback_data=START_EXAM)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text("Hello! I'm your depression test bot. How can I assist you?", reply_markup=reply_markup)
    else:
        # User in the middle of a test, immediately restart the test without any notification
        read_questions_from_file()
        user_data['current_question'] = 1
        user_data['answers'] = {}
        next_question(update, _)

    return SELECTING_QUESTIONS


def start_exam(update: Update, _: CallbackContext):
    user_id = update.effective_user.id
    user_data = _.user_data.setdefault(user_id, {})

    # Start a new test
    read_questions_from_file()
    user_data['current_question'] = 1  # Start from the first question
    user_data['answers'] = {}  # Initialize or reset answers dictionary
    next_question(update, _)

    return SELECTING_QUESTIONS


def next_question(update: Update, _: CallbackContext):
    user_id = update.effective_user.id
    user_data = _.user_data.get(user_id)
    if not user_data:
        return

    current_question_number = user_data.get('current_question')
    if not current_question_number or current_question_number > QUESTIONS_PER_TEST:
        # End of the exam, show results
        show_results(update, _)
        return ConversationHandler.END

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
        show_results(update, _)
        return ConversationHandler.END

    chosen_option = int(query.data)
    user_data['answers'][question_number] = chosen_option
    user_data['current_question'] += 1

    return next_question(update, _)


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

    update.effective_message.reply_text(f"Test completed! Your results: {result}")

    # Save results in CSV file
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(RESULTS_FILE, 'a', newline='') as csvfile:
        fieldnames = ['user_id', 'timestamp', 'result']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow({'user_id': user_id, 'timestamp': timestamp, 'result': total_score})

def cancel(update: Update, _: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    query.message.reply_text("You have canceled the operation.")

    return ConversationHandler.END


def main():
    # Create the Updater and pass it your bot's token
    with open("token.txt", "r") as file:
        token = file.read().strip()

    updater = Updater(token, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with the state SELECTING_QUESTIONS
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECTING_QUESTIONS: [
                CallbackQueryHandler(start_exam, pattern='^' + str(START_EXAM) + '$'),
                CallbackQueryHandler(handle_answer, pattern='^[0-3]$'),
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conversation_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT, SIGTERM, or SIGABRT
    updater.idle()


if __name__ == '__main__':
    main()