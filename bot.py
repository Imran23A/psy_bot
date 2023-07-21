from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import csv

# Set up the logging module to see logs from the Telegram library.
import logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Replace 'YOUR_BOT_TOKEN' with the token you obtained from BotFather.
TOKEN = '5743367242:AAFi5ntJ-4bgwp5uV4Rc4qhUMmWe6ODxDAQ'
updater = Updater(TOKEN, use_context=True)
dispatcher = updater.dispatcher

# Function to read questions and options from the questions.txt file
def read_questions_from_file(filename='questions.txt'):
    with open(filename, 'r') as file:
        lines = file.read().splitlines()

    questions = []
    current_question = None
    for line in lines:
        line = line.strip()
        if line.isdigit():
            # Start of a new question
            if current_question is not None:
                questions.append(current_question)
            current_question = {'question': line, 'options': []}
        elif line:
            # Option for the current question
            if current_question is not None:
                current_question['options'].append(line)
    if current_question is not None:
        questions.append(current_question)

    return questions

# Function to save user responses to a CSV file
def save_user_responses_to_csv(user_responses, filename='user_responses.csv'):
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['user_id'] + [f'Question{i+1}' for i in range(len(user_responses[0]['responses']))]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for user_data in user_responses:
            writer.writerow(user_data)

# Dictionary to store user responses
user_responses = []

def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    user_id = user.id

    # Check if the user has already started the examination
    if any(user_data['user_id'] == user_id for user_data in user_responses):
        update.message.reply_text("You have already started the examination. Use /reset to start over.")
        return

    # Load questions from the questions.txt file
    questions = read_questions_from_file()

    if not questions:
        update.message.reply_text("Sorry, there are no questions available at the moment.")
        return

    # Add user to user_responses with empty responses
    user_data = {
        'user_id': user_id,
        'responses': [None] * len(questions)
    }
    user_responses.append(user_data)

    # Ask the first question
    question = questions[0]
    options = "\n".join([f"{index}. {option}" for index, option in enumerate(question['options'])])
    update.message.reply_text(f"{question['question']}\n{options}")

def process_response(update: Update, context: CallbackContext):
    user = update.message.from_user
    user_id = user.id

    # Check if the user has started the examination
    user_data = next((data for data in user_responses if data['user_id'] == user_id), None)
    if user_data is None:
        update.message.reply_text("Please use the /start_exam command to begin the examination.")
        return

    # Load questions from the questions.txt file
    questions = read_questions_from_file()

    if not questions:
        update.message.reply_text("Sorry, there are no questions available at the moment.")
        return

    # Get the user's current question index
    current_question_index = user_data['responses'].count(None)

    # Check if the user's response is a valid option
    try:
        response_option = int(update.message.text)
    except ValueError:
        update.message.reply_text("Invalid option. Please choose a number corresponding to the options.")
        return

    question = questions[current_question_index]
    num_options = len(question['options'])

    if 0 <= response_option < num_options:
        # Store the user's response for the current question
        user_data['responses'][current_question_index] = question['options'][response_option]
        # Move to the next question or complete the examination
        if current_question_index + 1 < len(questions):
            next_question = questions[current_question_index + 1]
            options = "\n".join([f"{index}. {option}" for index, option in enumerate(next_question['options'])])
            update.message.reply_text(f"{next_question['question']}\n{options}")
        else:
            update.message.reply_text("Thank you for completing the examination! Your responses have been recorded.")
            # Save the user's responses to a CSV file
            save_user_responses_to_csv(user_responses)
            # Remove the user_data from user_responses to indicate the examination is completed
            user_responses.remove(user_data)
    else:
        update.message.reply_text("Invalid option. Please choose a number corresponding to the options.")

def reset(update: Update, context: CallbackContext):
    user = update.message.from_user
    user_id = user.id

    # Check if the user has started the examination
    user_data = next((data for data in user_responses if data['user_id'] == user_id), None)
    if user_data is None:
        update.message.reply_text("Please use the /start_exam command to begin the examination.")
        return

    # Reset the user's responses
    user_data['responses'] = [None] * len(user_data['responses'])
    update.message.reply_text("Examination reset. Please answer the first question.")

# Add the command and message handlers to the dispatcher.
dispatcher.add_handler(CommandHandler("start_exam", start))
dispatcher.add_handler(CommandHandler("reset", reset))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, process_response))

def main():
    updater.start_polling()

    try:
        # Keep the program running to handle signals (e.g., SIGINT, SIGTERM)
        updater.idle()
    finally:
        # Save user responses to a CSV file before exiting
        save_user_responses_to_csv(user_responses)

if __name__ == '__main__':
    main()