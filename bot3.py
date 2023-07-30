import logging
import csv
import datetime
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, ConversationHandler, CallbackQueryHandler

# Import scoring functions from scoring.py
from scoring import score_becks_depression, score_becks_anxiety, score_pcl5

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for the states of the conversation
SELECTING_TEST, SELECTING_QUESTIONS = range(2)

# Constants for the tests and their respective files
TESTS = {
    "Beck's depression test": "Beck's_depress.tsv",
    "Beck's anxiety test": "Beck's_anxiety.tsv",
    "Post-Traumatic PCL-5 test": "post_Traumatic_PCL-5.tsv",
}

# Dictionary containing the number of questions for each test
QUESTIONS_COUNT = {
    "Beck's depression test": 21,
    "Beck's anxiety test": 21,
    "Post-Traumatic PCL-5 test": 20,
}

# Dictionary to store questions and options for each test
QUESTIONS = {}

def read_questions_from_file(file_path):
    with open(file_path, mode='r', encoding='utf-8') as tsv_file:
        tsv_reader = csv.reader(tsv_file, delimiter='\t')
        questions = {}
        is_header_row = True
        for row in tsv_reader:
            if is_header_row:
                is_header_row = False
                continue

            question_number_str = re.sub(r'\D', '', row[0])  # Extract the numeric part from the first column
            try:
                question_number = int(question_number_str)
            except ValueError:
                # Skip rows that don't have a valid integer question number
                continue

            question = row[0][len(question_number_str):].strip()  # Remove the numeric part to get the question
            options = row[1:]
            questions[question_number] = {"question": question, "options": options}
        return questions

def start(update: Update, _: CallbackContext) -> int:
    keyboard = [
        [InlineKeyboardButton(test_name, callback_data=test_name)] for test_name in TESTS.keys()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Выберите тест для прохождения:", reply_markup=reply_markup)
    return SELECTING_TEST

def choosing_test(update: Update, _: CallbackContext) -> int:
    logger.info("Choosing test...")
    query = update.callback_query
    test_name = query.data

    # Clear any previous test data
    user_id = update.effective_user.id
    _.user_data[user_id] = {}

    # Read questions and options from the TSV file
    file_path = TESTS.get(test_name)
    if file_path:
        questions = read_questions_from_file(file_path)
        _.user_data[user_id]["questions"] = questions
        _.user_data[user_id]["current_question_number"] = 1
        _.user_data[user_id]["test_name"] = test_name

        # Send the first question to the user
        send_question(update, _)

        logger.info("Test chosen successfully.")
        return SELECTING_QUESTIONS
    else:
        query.message.reply_text("Тест не найден. Пожалуйста, выберите тест из списка.")
        return SELECTING_TEST

# Add conversation handler to handle the different states of the conversation
conversation_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        SELECTING_TEST: [CallbackQueryHandler(choosing_test)],
        SELECTING_QUESTIONS: [
            CallbackQueryHandler(handle_answer, pattern='^[0-9]+$'),
        ],
    },
    fallbacks=[],
)

def send_question(update: Update, _: CallbackContext) -> None:
    user_id = update.effective_user.id
    user_data = _.user_data.get(user_id)
    if not user_data:
        return

    current_question_number = user_data.get("current_question_number")
    questions = user_data.get("questions")
    test_name = user_data.get("test_name")
    questions_count = QUESTIONS_COUNT.get(test_name)

    if not current_question_number or not questions:
        return

    if current_question_number > questions_count:
        query = update.callback_query
        query.edit_message_text("Тест завершен. Спасибо за участие!")
        return

    question_data = questions.get(current_question_number)
    if not question_data:
        return

    question = question_data["question"]
    options = question_data["options"]

    keyboard = [
        [InlineKeyboardButton(option, callback_data=str(idx))] for idx, option in enumerate(options)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    query.edit_message_text(text=question, reply_markup=reply_markup)

def handle_answer(update: Update, _: CallbackContext) -> None:
    logger.info("Handling answer...")
    user_id = update.effective_user.id
    user_data = _.user_data.get(user_id)
    if not user_data:
        return

    current_question_number = user_data.get("current_question_number")
    questions_count = QUESTIONS_COUNT.get(user_data.get("test_name"))
    if not current_question_number or current_question_number > questions_count:
        return

    chosen_option = int(update.callback_query.data)
    user_data["answers"] = user_data.get("answers", {})
    user_data["answers"][current_question_number] = chosen_option

    current_question_number += 1
    user_data["current_question_number"] = current_question_number

    _.user_data[user_id] = user_data
    send_question(update, _)
    logger.info("Answer handled successfully.")


def show_results(update: Update, _: CallbackContext) -> None:
    user_id = update.effective_user.id
    user_data = _.user_data.get(user_id)
    if not user_data:
        return

    test_name = user_data.get("test_name")
    answers = user_data.get("answers", {})
    questions = user_data.get("questions")
    questions_count = QUESTIONS_COUNT.get(test_name)

    if not test_name or not questions:
        return

    total_score = sum(answers.get(q, 0) for q in range(1, questions_count + 1))
    result = ""

    if test_name == "Beck's depression test":
        result = score_becks_depression(total_score)
    elif test_name == "Beck's anxiety test":
        result = score_becks_anxiety(total_score)
    elif test_name == "Post-Traumatic PCL-5 test":
        result = score_pcl5(total_score)

    message = (
        f"Вы прошли тест ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), "
        f"ваш результат по тесту '{test_name}': {total_score}. {result}"
    )
    update.message.reply_text(message)

def main():
    # Create the Updater and pass it your bot's token
    with open("token.txt", "r") as file:
        token = file.read().strip()

    updater = Updater(token, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler to handle the different states of the conversation
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECTING_TEST: [CallbackQueryHandler(choosing_test)],
            SELECTING_QUESTIONS: [
                CallbackQueryHandler(handle_answer, pattern='^[0-9]+$'),
            ],
        },
        fallbacks=[],
    )

    dp.add_handler(conversation_handler)

    # Add handler to show the results
    dp.add_handler(CommandHandler('results', show_results))

    # Start the Bot
    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT, SIGTERM, or SIGABRT
    updater.idle()

if __name__ == '__main__':
    main()