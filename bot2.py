import logging
import csv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, ConversationHandler, CallbackQueryHandler
import datetime

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


RESULTS_FILE = "results.csv"

# State definitions for top-level conversation
SELECTING_TEST = 1
SELECTING_QUESTIONS = 2

# Constants for the tests
TESTS = {
    "Beck's depression test": "Beck's_depress.tsv",
    "Beck's anxiety test": "Beck's_anxiety.tsv",
    "Post-Traumatic PCL-5 test": "post_Traumatic_PCL-5.tsv",
    "Social Phobia SPIN test": "social_Phobia_SPIN.tsv"
}

QUESTIONS_FILES = {
    "Beck's depression test": "Beck's_depress.tsv",
    "Beck's anxiety test": "Beck's_anxiety.tsv",
    "Post-Traumatic PCL-5 test": "post_Traumatic_PCL-5.tsv",
    "Social Phobia SPIN test": "social_Phobia_SPIN.tsv"
}

# A dictionary containing the number of questions for each test
QUESTIONS_COUNT = {
    "Beck's depression test": 21,
    "Beck's anxiety test": 10,
    "Post-Traumatic PCL-5 test": 15,
    "Social Phobia SPIN test": 8
}

# A dictionary containing the questions and options read from the Beck's_depress.tsv file
# questions = {}


def read_questions_from_file(test_name: str):
    filename = QUESTIONS_FILES.get(test_name)
    if filename is None:
        raise Exception(f"Invalid test name '{test_name}'.")

    try:
        with open(filename, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            questions = {}  # Initialize 'questions' for each test separately
            for line in lines:
                data = line.strip().split('\t')
                if len(data) == 5:
                    question = data[0]
                    options = data[1:]
                    questions[question] = options
    except FileNotFoundError:
        raise Exception(f"Failed to read questions from the file '{filename}'. Make sure it exists.")
    return questions, QUESTIONS_COUNT.get(test_name, 0)


def start(update: Update, _: CallbackContext) -> int:
    user_id = update.effective_user.id
    user_data = _.user_data.setdefault(user_id, {})

    # Check if the user is new or in the middle of a test
    if 'current_question' not in user_data:
        # New user, show the list of available tests
        keyboard = [
            [InlineKeyboardButton(test_name, callback_data=f'start_test_{test}')] for test, test_name in TESTS.items()
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text("Привет! Выберите тест для прохождения:", reply_markup=reply_markup)
        return SELECTING_QUESTIONS  # Move to the SELECTING_QUESTIONS state
    else:
        # User in the middle of a test, ask if they want to cancel the ongoing test
        keyboard = [
            [InlineKeyboardButton("Отменить тест", callback_data='cancel_test')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Since you don't want to show any message when the user taps the button, you can simply edit the previous message
        # with the new keyboard, instead of sending a new message.
        update.callback_query.edit_message_text(
            text="Вы уже проходите тест. Хотите ли вы отменить текущий тест и выбрать новый?",
            reply_markup=reply_markup
        )
        return SELECTING_QUESTIONS  # Move to the SELECTING_QUESTIONS state



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
    user_id = update.effective_user.id
    user_data = _.user_data.setdefault(user_id, {})
    
    # Check if the /start_test command is invoked directly or through a callback query
    if update.callback_query:
        query = update.callback_query
        test_name = query.data.split('_')[-1]  # Extract the test name from the callback data
    else:
        # If the command is invoked directly, the test_name will be passed as the command argument
        test_name = _.args[0] if _.args else None

    if not test_name:
        # Test name is not provided, show an error message
        update.message.reply_text("Please provide a valid test name after the /start_test command.")
        return

    # Clear ongoing test data to start a new one
    user_data.clear()
    
    questions, questions_count = read_questions_from_file(test_name)
    user_data['current_question'] = 1  # Start from the first question
    user_data['test_name'] = test_name  # Store the test name in user data
    user_data['questions_count'] = questions_count  # Store the number of questions for the test
    user_data['answers'] = {}  # Initialize or reset answers dictionary
    user_data['questions'] = questions  # Store the questions in user data

    # Generate and send the first question
    send_question(update, _, test_name)

    return SELECTING_QUESTIONS

def start_exam(update: Update, _: CallbackContext):
    query = update.callback_query
    test_name = query.data.split('_')[-1]  # Extract the test name from the callback data
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
    questions, questions_count = read_questions_from_file(test_name)
    user_data['current_question'] = 1  # Start from the first question
    user_data['test_name'] = test_name  # Store the test name in user data
    user_data['questions_count'] = questions_count  # Store the number of questions for the test
    user_data['answers'] = {}  # Initialize or reset answers dictionary
    user_data['questions'] = questions  # Store the questions in user data

    # Generate and send the first question
    send_question(update, _, test_name)

    return SELECTING_QUESTIONS

def send_question(update: Update, _: CallbackContext, test_name: str):
    user_id = update.effective_user.id
    user_data = _.user_data.get(user_id)
    if not user_data:
        return

    current_question_number = user_data.get('current_question')
    questions_count = user_data.get('questions_count', 0)
    questions = user_data.get('questions')  # Retrieve the questions from user data

    if not current_question_number or current_question_number > questions_count:
        # Test is completed, show results as a "fake" last question
        show_results(update, _, test_name)
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
    questions_count = QUESTIONS_COUNT.get(user_data.get('test_name', ''), 0)
    
    if not question_number or question_number > questions_count:
        # Should not happen, but just in case
        show_results(update, _, user_data.get('test_name', ''))
        return SELECTING_QUESTIONS

    chosen_option = int(query.data)
    user_data['answers'][question_number] = chosen_option
    user_data['current_question'] += 1

    # Send the next question
    send_question(update, _, user_data.get('test_name', ''))

    return SELECTING_QUESTIONS


def show_results(update: Update, _: CallbackContext, test_name: str) -> None:
    user_id = update.effective_user.id
    user_data = _.user_data.get(user_id)
    if not user_data:
        return

    questions_count = user_data.get('questions_count', 0)
    answers = user_data.get('answers', {})

    # Calculate the total score based on the number of questions in the selected test
    total_score = sum(answers.get(q, 0) for q in range(1, questions_count + 1))

    test_name = user_data.get('current_test', '')
    result = ""

    if test_name == "тест депрессии Бека":
        if total_score <= 10:
            result = "отсутствуют или не выражены симптомы депрессии."
        elif 11 <= total_score <= 16:
            result = "имеются нарушения настроения."
        elif 17 <= total_score <= 20:
            result = "есть симптомы на границе клинической депрессии."
        elif 21 <= total_score <= 30:
            result = "есть симптомы которые свидетельствуют или могут привести к умеренной депрессии."
        elif 31 <= total_score <= 40:
            result = "имеются серьезные нарушения настроения либо выраженная депрессия."
        else:
            result = "есть симптомы серьезной депрессии."

    elif test_name == "тест тревожности Бека":
        # Define the scoring scale for the Beck's anxiety test
        # You can replace these values with the correct scoring scale
        if total_score <= 7:
            result = "минимальный уровень тревожности."
        elif 8 <= total_score <= 15:
            result = "легкая тревожность и беспокойство."
        elif 16 <= total_score <= 25:
            result = "умеренная тревожность."
        else:
            result = "сильная тревога."

    elif test_name == "тест симптомов ПТСР":
        # Define the scoring scale for the PCL-5 test (Post-Traumatic Stress Disorder Checklist for DSM-5)
        # You can replace these values with the correct scoring scale
        if total_score <= 20:
            result = "отсутствуют или не выражены симптомы ПТСР."
        elif 21 <= total_score <= 35:
            result = "имеются легкие симптомы ПТСР."
        elif 36 <= total_score <= 50:
            result = "есть умеренные симптомы ПТСР."
        elif 51 <= total_score <= 65:
            result = "есть симптомы ПТСР средней тяжести."
        elif 66 <= total_score <= 80:
            result = "есть серьезные симптомы ПТСР."
        else:
            result = "есть симптомы тяжелого ПТСР."

    elif test_name == "тест социальных фобий":
        # Define the scoring scale for the SPIN test (Social Phobia Inventory)
        # You can replace these values with the correct scoring scale
        if total_score <= 10:
            result = "отсутствует или не выражены симптомы социальной фобии."
        elif 11 <= total_score <= 20:
            result = "имеются легкие симптомы социальной фобии."
        elif 21 <= total_score <= 30:
            result = "есть умеренные симптомы социальной фобии."
        elif 31 <= total_score <= 40:
            result = "есть симптомы социальной фобии средней тяжести."
        elif 41 <= total_score <= 50:
            result = "есть серьезные симптомы социальной фобии."
        else:
            result = "есть симптомы тяжелой социальной фобии."

    # Add similar elif blocks for other tests as needed

    # Save results in CSV file
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(RESULTS_FILE, 'a', newline='') as csvfile:
        fieldnames = ['user_id', 'timestamp', 'test_name', 'result', 'answers']  # Add 'test_name' to the header
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Convert answers dictionary to a comma-separated string
        answers_str = ",".join([str(answers[q]) for q in sorted(answers.keys())])

        writer.writerow({'user_id': user_id, 'timestamp': timestamp, 'test_name': test_name, 'result': total_score, 'answers': answers_str})

    # Compose the message with the test results
    message = (
        f"Вы прошли тест ({timestamp}), судя по вашим ответам ваш результат по тесту '{test_name}': {total_score}." 
        f"Вероятно у вас {result}"
    )

    # If there was a previous message, edit it with the results, otherwise send a new message
    previous_message_id = user_data.get('previous_message')
    if previous_message_id:
        update.callback_query.edit_message_text(
            text=message,
            reply_markup=None  # Remove the "Cancel" button from the message
        )
    else:
        update.effective_message.reply_text(message)

    # Clear user data after showing results
    user_data.clear()

    # Save results in CSV file
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(RESULTS_FILE, 'a', newline='') as csvfile:
        fieldnames = ['user_id', 'timestamp', 'test_name', 'result', 'answers']  # Add 'test_name' to the header
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Convert answers dictionary to a comma-separated string
        answers_str = ",".join([str(answers[q]) for q in sorted(answers.keys())])

        writer.writerow({'user_id': user_id, 'timestamp': timestamp, 'test_name': test_name, 'result': total_score, 'answers': answers_str})

    # Compose the message with the test results
    message = (
        f"Вы прошли тест ({timestamp}), судя по вашим ответам ваш результат по тесту '{test_name}': {total_score} . "
        f"Вероятнее всего у вас {result}"
    )

    # If there was a previous message, edit it with the results, otherwise send a new message
    previous_message_id = user_data.get('previous_message')
    if previous_message_id:
        update.callback_query.edit_message_text(
            text=message,
            reply_markup=None  # Remove the "Cancel" button from the message
        )
    else:
        update.effective_message.reply_text(message)

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
                CallbackQueryHandler(start_test_button, pattern='^start_'),
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
