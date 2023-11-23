from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, ConversationHandler, CallbackQueryHandler
import logging
import csv
from datetime import datetime

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define conversation states
SELECTING_TEST, SHOW_QUESTION = range(2)

def start(update: Update, context: CallbackContext) -> int:
    # Send message with four inline buttons for the tests
    keyboard = [
        [InlineKeyboardButton("тест депрессии Бека", callback_data='beck_depression')],
        [InlineKeyboardButton("тест тревожности Бека", callback_data='beck_anxiety')],
        [InlineKeyboardButton("тест ПТСР", callback_data='ptsd')],
        [InlineKeyboardButton("тест социальных фобий", callback_data='social_phobia')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Ensure that the message is always sent as a new message to keep the menu visible
    update.message.reply_text('Выберите тест:', reply_markup=reply_markup)
    # Clear any existing conversation data to reset the state
    context.user_data.clear()
    return SELECTING_TEST

def send_menu(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("тест депрессии Бека", callback_data='beck_depression')],
        [InlineKeyboardButton("тест тревожности Бека", callback_data='beck_anxiety')],
        [InlineKeyboardButton("тест ПТСР", callback_data='ptsd')],
        [InlineKeyboardButton("тест социальных фобий", callback_data='social_phobia')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Выберите тест:', reply_markup=reply_markup)    

def delete_previous_questions(update: Update, context: CallbackContext):
    """Deletes previously sent test questions."""
    chat_id = update.effective_chat.id
    question_message_id = context.user_data.get('question_message_id')

    if question_message_id:
        try:
            context.bot.delete_message(chat_id=chat_id, message_id=question_message_id)
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
        context.user_data.pop('question_message_id', None)

def test_selection(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    # Delete any previous test question messages
    delete_previous_questions(update, context)

    # Clear previous data if any
    context.user_data.clear()

    # Load the selected test questions
    test_files = {
        'beck_depression': 'Becks_depress.tsv',
        'beck_anxiety': 'Becks_anxiety.tsv',
        'ptsd': 'post_Traumatic_PCL-5.tsv',
        'social_phobia': 'social_Phobia_SPIN.tsv'
    }
    context.user_data['questions'] = load_test_questions(test_files[query.data])
    context.user_data['current_question'] = 0
    context.user_data['test_name'] = query.data

    # Send the first question
    return show_question(update, context)

def load_test_questions(filename):
    questions = {}
    with open(filename, 'r', encoding='utf-8') as file:
        for line in file:
            parts = line.strip().split('\t')
            question_num_and_text = parts[0]
            options = parts[1:]
            questions[question_num_and_text] = options
    return questions

def end_test(update: Update, context: CallbackContext):
    # Calculate the test results
    total_score = calculate_results(context.user_data)

    # Record the test result in the CSV file
    test_name = context.user_data['test_name']
    user_id = update.effective_user.id
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open('results.csv', 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([user_id, test_name, timestamp, total_score])

    # Send the results to the user
    result_message = f"Your results for {test_name}: {total_score}"
    if update.callback_query:
        update.callback_query.edit_message_text(text=result_message)
    else:
        update.message.reply_text(result_message)

    # Clear user data for a new test
    context.user_data.clear()

    # Return to the main menu
    return SELECTING_TEST

def show_question(update: Update, context: CallbackContext) -> int:
    current_question_index = context.user_data['current_question']
    questions = context.user_data['questions']
    question_items = list(questions.items())

    if current_question_index < len(question_items):
        question_text, options = question_items[current_question_index]
        keyboard = [[InlineKeyboardButton(option, callback_data=str(index))] for index, option in enumerate(options)]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # If this is the first question, send a new message
        if current_question_index == 0:
            sent_message = context.bot.send_message(chat_id=update.effective_chat.id, text=question_text, reply_markup=reply_markup)
            # Store the message ID for editing later
            context.user_data['question_message_id'] = sent_message.message_id
        else:
            # Edit the existing message for subsequent questions
            message_id = context.user_data.get('question_message_id')
            context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=message_id, text=question_text, reply_markup=reply_markup)

        return SHOW_QUESTION
    else:
        # End of test, handle accordingly
        return end_test(update, context)


def calculate_results(user_data):
    answers = user_data.get('answers', {})
    valid_answers = [int(v) for v in answers.values() if v.isdigit()]
    total_score = sum(valid_answers)
    return total_score

def save_results(user_id, test_name, results):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open('results.csv', 'a', newline='') as csvfile:
        result_writer = csv.writer(csvfile, delimiter=',')
        result_writer.writerow([user_id, test_name, timestamp, results])

def handle_answer(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    # Check if the callback data is for an answer or test selection
    if query.data.isdigit():
        # Handle answer selection
        current_question_index = context.user_data['current_question']
        context.user_data.setdefault('answers', {})[current_question_index] = query.data

        # Increment the question index and show next question
        context.user_data['current_question'] += 1
        return show_question(update, context)
    else:
        # Handle test selection
        return test_selection(update, context)

def cancel_handler(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Test cancelled. Type /start to begin again.')
    context.user_data.clear()
    return ConversationHandler.END

def main() -> None:
    with open("token.txt", "r") as file:
        token = file.read().strip()

    updater = Updater(token)

    dispatcher = updater.dispatcher

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECTING_TEST: [CallbackQueryHandler(test_selection)],
            SHOW_QUESTION: [CallbackQueryHandler(handle_answer)],
        },
        fallbacks=[CommandHandler('cancel', cancel_handler)],
        allow_reentry=True  # Allow re-entering the same state
    )

    dispatcher.add_handler(conversation_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()