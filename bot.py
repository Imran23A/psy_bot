import logging
import csv
from telegram import Update, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler, CallbackQueryHandler
import warnings
import datetime

warnings.filterwarnings("ignore", "If 'per_message=False', 'CallbackQueryHandler' will not be", UserWarning)
# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)
logger = logging.getLogger(__name__)

# State definitions for top-level conversation
SELECTING_ACTION, SELECTING_QUESTIONS = map(chr, range(2))

# State definitions for second-level conversation
ANSWERING = map(chr, range(2, 5))  # Exclusive because the top-level conversation has priority

# Different constants for this example
START_EXAM = "start_exam"
RESET_EXAM = "reset_exam"
HELP = "help"
WATCH_RESULTS = "watch_results"

# A dictionary containing the questions and options read from the questions.tsv file
questions = {}


def read_questions_from_file():
    try:
        with open('questions.tsv', 'r', encoding='utf-8') as file:
            lines = file.readlines()
            for line in lines:
                data = line.strip().split('\t')
                if len(data) == 5:
                    question = data[0]
                    options = data[1:]
                    questions[question] = options
    except FileNotFoundError:
        raise Exception("Failed to read questions from the file. Make sure 'questions.tsv' exists.")
    return questions


def start(update: Update, _: CallbackContext) -> int:
    keyboard = [
        [InlineKeyboardButton("Start Test", callback_data=START_EXAM)],
        [InlineKeyboardButton("Reset Test", callback_data=RESET_EXAM)],
        [InlineKeyboardButton("Help", callback_data=HELP)],
        [InlineKeyboardButton("Watch Results", callback_data=WATCH_RESULTS)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text("Hello! I'm your depression test bot. How can I assist you?", reply_markup=reply_markup)

    return SELECTING_ACTION


def handle_action(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    action = query.data
    if action == START_EXAM:
        read_questions_from_file()
        start_exam(update, context)
        return SELECTING_QUESTIONS
    elif action == RESET_EXAM:
        reset_exam(update, context)
        return SELECTING_ACTION
    elif action == HELP:
        show_help(update, context)
        return SELECTING_ACTION
    elif action == WATCH_RESULTS:
        watch_results(update, context)
        return SELECTING_ACTION
    else:
        # In case of unexpected callback data
        return SELECTING_ACTION

def start_exam(update: Update, query: CallbackContext):
    user_id = update.effective_user.id
    user_data = query.user_data.setdefault(user_id, {})
    user_data['current_question'] = 1  # Start from the first question
    user_data['answers'] = {}  # Initialize or reset answers dictionary

    next_question(update, query)

def reset_exam(update: Update, query):
    user_id = update.effective_user.id
    user_data = query.message.bot_data.get(user_id)
    if user_data:
        user_data['current_question'] = 1
        user_data['answers'] = {}
    query.message.reply_text("Test has been reset. You can start again by choosing 'Start Test'.")


def show_help(update: Update, query):
    query.message.reply_text(
        "This is a depression test bot. You can take the test by choosing 'Start Test'. "
        "You will be presented with 21 questions, each with 4 options to choose from. "
        "Simply click on the option that best reflects your current state of mind. "
        "After completing the test, you can choose 'Watch Results' to see your test results."
    )


def next_question(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data = context.user_data.get(user_id)
    if not user_data:
        return

    current_question_number = user_data.get('current_question')
    if not current_question_number or current_question_number > len(questions):
        # End of the exam, show results
        show_results(update, context)
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
        context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=previous_message_id,
            text=question,
            reply_markup=reply_markup
        )
    else:
        message = update.effective_message.reply_text(question, reply_markup=reply_markup)
        user_data['previous_message'] = message.message_id

def handle_answer(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    user_id = update.effective_user.id
    user_data = context.user_data.get(user_id)
    if not user_data:
        return ConversationHandler.END

    question_number = user_data.get('current_question')
    if not question_number or question_number > len(questions):
        show_results(update, context)
        return ConversationHandler.END

    chosen_option = int(query.data)
    user_data['answers'][question_number] = chosen_option
    user_data['current_question'] += 1

    return next_question(update, context)

def show_results(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data = context.user_data.get(user_id)
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

    context.bot.send_message(chat_id=update.effective_chat.id, text=f"Test completed! Your results: {result}")

    # Save results in CSV file
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open('results.csv', 'a', newline='') as csvfile:
        fieldnames = ['user_id', 'timestamp', 'result']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow({'user_id': user_id, 'timestamp': timestamp, 'result': total_score})

def watch_results(update: Update, query):
    user_id = update.effective_user.id
    user_data = query.message.bot_data.get(user_id)
    if not user_data:
        return

    # Calculate and show the latest results
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

    query.message.reply_text(f"Your latest test results: {result}")


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

    # Add conversation handler with the states SELECTING_ACTION and SELECTING_QUESTIONS
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECTING_ACTION: [
                CallbackQueryHandler(handle_action, pattern='^' + str(START_EXAM) + '$'),
                CallbackQueryHandler(handle_action, pattern='^' + str(RESET_EXAM) + '$'),
                CallbackQueryHandler(handle_action, pattern='^' + str(HELP) + '$'),
                CallbackQueryHandler(handle_action, pattern='^' + str(WATCH_RESULTS) + '$'),
            ],
            SELECTING_QUESTIONS: [
                CallbackQueryHandler(handle_answer, pattern='^[0-3]$'),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conversation_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT
    updater.idle()


if __name__ == '__main__':
    main()