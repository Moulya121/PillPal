from typing import Final
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from pymongo import MongoClient
import schedule
import time
import asyncio
import threading
import re  # Import regular expressions
import openai

#ai connector

openai.api_key = "openai-api-key"


# Initialize a message history list to store conversation context
message_history = [
    {
        "role": "system",
        "content": (
            "I'll assist you with reminders about your tablets. Please provide me with the tablet name, the time for the daily reminder in 24-hour format (HH:MM), and the duration in days. If you have any questions about tablets or need general help, feel free to ask!."
        ),
    }
]


def get_medical_assistant_response(user_query):
    # Add the user's query to the conversation history
    message_history.append({"role": "user", "content": user_query})

    # Get the assistant's response
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=message_history,
        temperature=0.7,
        max_tokens=2048,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )

    # Append the assistant's response to the conversation history
    assistant_reply = response.choices[0].message.content
    message_history.append({"role": "assistant", "content": assistant_reply})

    # Return the assistant's response
    return assistant_reply

# Prompt AI to generate a diet plan
def get_diet_plan_suggestion(disease):
    prompt = f"Suggest a healthy diet plan for managing {disease}."
    message_history.append({"role": "user", "content": prompt})

    # AI response
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=message_history,
        temperature=0.7,
        max_tokens=2048,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    
    # Append response and return diet suggestion
    diet_suggestion = response.choices[0].message.content
    message_history.append({"role": "assistant", "content": diet_suggestion})
    return diet_suggestion

# Prompt AI to generate a diet plan
def get_exercise_plan_suggestion(disease):
    prompt = f"Suggest some of the workout and yoga asanas for managing {disease} and the desciption should be precise."
    message_history.append({"role": "user", "content": prompt})

    # AI response
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=message_history,
        temperature=0.7,
        max_tokens=2048,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    
    # Append response and return diet suggestion
    exercise_suggestion = response.choices[0].message.content
    message_history.append({"role": "assistant", "content": exercise_suggestion})
    return exercise_suggestion


# Constants
TOKEN: Final = '7590081620:AAFC0yCoTLCvuSP09aukUwqv7QEi-qh_9uY'
BOT_USERNAME: Final = '@MyPillPalBot'

# MongoDB setup
client = MongoClient('mongodb+srv://unicornsinpajamas:UNIPJ5678##@cluster0.c16al.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client['pill_pal_bot']
user_collection = db['PillPal_users']
schedule_collection = db['schedules']

# State management
USER_INFO_STATE = {}
USER_SCHEDULE_STATE = {}
USER_UPDATE_STATE = {}

# Regular expression for tablet format
TABLET_FORMAT_REGEX = re.compile(r'^[A-Za-z0-9\s]+ \d+mg$')  # Matches "tablet name tablet mg"

# Function to check reminders
def check_reminders():
    current_time = time.strftime('%H:%M')
    reminders = schedule_collection.find({"reminder_time": current_time})

    for reminder in reminders:
        chat_id = reminder["chat_id"]
        message = f"Time to take your tablet ⏰: {reminder['tablet_name']}!"
        asyncio.run(app.bot.send_message(chat_id=chat_id, text=message))

# Schedule runner in a separate thread
def run_schedule():
    schedule.every(1).minutes.do(check_reminders)
    while True:
        schedule.run_pending()
        time.sleep(1)

# Run the scheduler thread
scheduler_thread = threading.Thread(target=run_schedule, daemon=True)
scheduler_thread.start()

# Start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat.id
    existing_user = user_collection.find_one({"chat_id": user_id})
    
    if existing_user:
        keyboard = [
            [InlineKeyboardButton("Ongoing Schedule", callback_data='ongoing_schedule')],
            [InlineKeyboardButton("New Schedule", callback_data='new_schedule')],
            [InlineKeyboardButton("Any Questions buddy?😄", callback_data='any_questions')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"Hello {existing_user['name']}, what do you want to do today?", reply_markup=reply_markup)
    else:
        USER_INFO_STATE[user_id] = {'state': 'new_user_full_name'}
        await update.message.reply_text('Hey PillPal here👋!\n Lets get you set up. Just drop your full name below,\n and we’ll get started on making life a little easier!!')

# Button callback handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.message.chat.id

    if query.data == 'ongoing_schedule':
        schedules = schedule_collection.find({"chat_id": user_id})
        user_schedules = list(schedules)
        if user_schedules:
            schedule_details = "\n".join([f"Tablet: {schedule['tablet_name']}, Time: {schedule['reminder_time']}, Duration: {schedule['duration']} hours, Disease : {schedule['disease']}" for schedule in user_schedules])
            await query.edit_message_text(f"📅 Here’s a look at your ongoing schedules! Let’s keep you on track with everything you need!\n{schedule_details}")
        else:
            await query.edit_message_text("No ongoing schedules found. Do you want to schedule a new one?")
            keyboard = [[InlineKeyboardButton("Yes", callback_data='schedule_new')],
                        [InlineKeyboardButton("No", callback_data='no_schedule')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("Would you like to schedule a new one?", reply_markup=reply_markup)
        
        keyboard = [
            [InlineKeyboardButton("Update prescription", callback_data='modify_prescription')],
            [InlineKeyboardButton("Diet plan 😋", callback_data='create_deit')],
            [InlineKeyboardButton("Exercise options 💪", callback_data='excercise_plan')],
            [InlineKeyboardButton("Both 💪😋", callback_data='both1')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Updation on ongoing schedules", reply_markup=reply_markup)

    elif query.data == 'new_schedule':
        USER_SCHEDULE_STATE[user_id] = {'state': 'tablet_name'}
        await query.edit_message_text("Please enter the tablet name (in the format 'tablet name tablet mg', e.g., 'Paracetamol 500mg') for the new schedule:")

    elif query.data == 'schedule_new':
        USER_SCHEDULE_STATE[user_id] = {'state': 'tablet_name'}
        await query.edit_message_text("Please enter the tablet name (in the format 'tablet name tablet mg', e.g., 'Paracetamol 500mg') for the new schedule:")
    
    elif query.data == 'any_questions':
        await query.edit_message_text('Got any questions? Just type them out below—Im here to help!😊')

    elif query.data == 'no_schedule':
        await query.edit_message_text("Alright! Just give me a shout if you need anything else! PillPal is your's!😃")
    
    elif query.data == 'create_deit':
        # Fetch the latest disease information from the user's schedule
        await query.edit_message_text("wait a moment i will provide the details....")
        latest_schedule = schedule_collection.find_one({"chat_id": user_id}, sort=[('_id', -1)])
        
        if latest_schedule:
            disease = latest_schedule['disease']
            diet_suggestion = get_diet_plan_suggestion(disease)  # Call AI function for diet suggestion
            await query.edit_message_text(f"Suggested diet plan for {disease}:\n{diet_suggestion}")
        else:
            await query.edit_message_text("Oops😕! No info on your condition yet buddy. Let’s set up a schedule first!")
    
    elif query.data == 'excercise_plan':
        # Fetch the latest disease information from the user's schedule
        await query.edit_message_text("wait a moment i will provide the details....")
        latest_schedule = schedule_collection.find_one({"chat_id": user_id}, sort=[('_id', -1)])
        
        if latest_schedule:
            disease = latest_schedule['disease']
            exercise_suggestion = get_exercise_plan_suggestion(disease)  # Call AI function for diet suggestion
            await query.edit_message_text(f"Suggested exercise plan for {disease}:\n{exercise_suggestion}")
        else:
            await query.edit_message_text("Oops😕! No info on your condition yet buddy. Let’s set up a schedule first!")
    elif query.data == 'modify_prescription':
        USER_UPDATE_STATE[user_id] = {'state': 'tablet_name'}
        await query.edit_message_text("Please enter the tablet name you want to update:")

# Handling user messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat.id
    text = update.message.text

    if user_id in USER_UPDATE_STATE:
        update_state = USER_UPDATE_STATE[user_id]

        if update_state['state'] == 'tablet_name':
            # Validate tablet name format
            if TABLET_FORMAT_REGEX.match(text):
                USER_UPDATE_STATE[user_id] = {'state': 'update_choice', 'tablet_name': text}
                await update.message.reply_text("Thanks! What do you want to update? (Reply with 'time' or 'duration'):")
            else:
                await update.message.reply_text("Please enter the tablet name in the correct format (e.g., 'Paracetamol 500mg').")
            return

        elif update_state['state'] == 'update_choice':
            if text.lower() == 'time':
                USER_UPDATE_STATE[user_id] = {'state': 'new_time', 'tablet_name': update_state['tablet_name']}
                await update.message.reply_text("Please enter the new reminder time (in HH:MM format):")
            elif text.lower() == 'duration':
                USER_UPDATE_STATE[user_id] = {'state': 'new_duration', 'tablet_name': update_state['tablet_name']}
                await update.message.reply_text("Please enter the new duration (in hours):")
            else:
                await update.message.reply_text("Invalid choice. Please reply with 'time' or 'duration'.")
            return

        elif update_state['state'] == 'new_time':
            new_time = text
            # Update the database with the new time
            schedule_collection.update_one(
                {'tablet_name': update_state['tablet_name'], 'chat_id': user_id},
                {'$set': {'reminder_time': new_time}}
            )
            await update.message.reply_text(f"Updated the reminder time for {update_state['tablet_name']} to {new_time}.")
            USER_UPDATE_STATE.pop(user_id)  # Clear state
            return

        elif update_state['state'] == 'new_duration':
            new_duration = text
            # Update the database with the new duration
            schedule_collection.update_one(
                {'tablet_name': update_state['tablet_name'], 'chat_id': user_id},
                {'$set': {'duration': new_duration}}
            )
            await update.message.reply_text(f"Updated the duration for {update_state['tablet_name']} to {new_duration} hours.")
            USER_UPDATE_STATE.pop(user_id)  # Clear state
            return

    
    if user_id in USER_INFO_STATE:
        state_info = USER_INFO_STATE[user_id]
        if state_info['state'] == 'new_user_full_name':
            USER_INFO_STATE[user_id] = {'state': 'new_user_age', 'full_name': text}
            await update.message.reply_text("Great!👍 Now just need your age to set things up.")
        
        elif state_info['state'] == 'new_user_age':
            try:
                age = int(text)
                user_info = {'chat_id': user_id, 'name': state_info['full_name'], 'age': age}
                user_collection.insert_one(user_info)
                USER_INFO_STATE.pop(user_id)
                await update.message.reply_text(f"Thank you! {user_info['name']} (Age: {user_info['age']}) has been added to the database.")
            except ValueError:
                await update.message.reply_text("Oops😕! Please enter a valid age as a number.")
        return

    if user_id in USER_SCHEDULE_STATE:
        schedule_state = USER_SCHEDULE_STATE[user_id]

        if schedule_state['state'] == 'tablet_name':
            # Validate tablet name format
            if TABLET_FORMAT_REGEX.match(text):
                USER_SCHEDULE_STATE[user_id] = {'state': 'reminder_time', 'tablet_name': text}
                await update.message.reply_text("Thanks! Now, please enter the reminder time ⏰(in HH:MM format, e.g., 14:00 for 2 PM):")
            else:
                await update.message.reply_text("Please enter the tablet name in the correct format (e.g., 'Paracetamol 500mg').")
            return

        elif schedule_state['state'] == 'reminder_time':
            reminder_time = text
            USER_SCHEDULE_STATE[user_id] = {'state': 'duration', 'tablet_name': schedule_state['tablet_name'], 'reminder_time': reminder_time}
            await update.message.reply_text("cool😎🌈! Now, please enter the duration for the schedule (in hours, e.g., 1 for 1 day):")
            return

        elif schedule_state['state'] == 'duration':
            try:
                duration = float(text)
                if duration <= 0:
                    raise ValueError("Duration must be a positive number")
                USER_SCHEDULE_STATE[user_id] = {'state': 'disease', 'tablet_name': schedule_state['tablet_name'], 'reminder_time': schedule_state['reminder_time'], 'duration': duration}
                await update.message.reply_text("Please enter the disease or condition this tablet is for:")
            except ValueError:
                await update.message.reply_text("Please enter a valid number for the duration (e.g., 1 or 1.5 for 1 hour or 1 hour 30 minutes).")
            return

        elif schedule_state['state'] == 'disease':
            disease = text
            USER_SCHEDULE_STATE[user_id] = {'tablet_name': schedule_state['tablet_name'], 'reminder_time': schedule_state['reminder_time'], 'duration': schedule_state['duration'], 'disease': disease}

            # Insert schedule information into the database
            schedule_info = {
                'chat_id': user_id,
                'tablet_name': schedule_state['tablet_name'],
                'reminder_time': schedule_state['reminder_time'],
                'duration': schedule_state['duration'],
                'disease': disease
            }
            schedule_collection.insert_one(schedule_info)
            USER_SCHEDULE_STATE.pop(user_id)

            # Ask if user wants to improve prescription in a healthier way
            keyboard = [
                [InlineKeyboardButton("Diet Plans", callback_data='create_deit')],
                [InlineKeyboardButton("Exercise Options", callback_data='exercise_options')],
                [InlineKeyboardButton("Both", callback_data='both')],
                [InlineKeyboardButton("None", callback_data='none')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("🌟 Are you interested in enhancing your prescription with some healthy lifestyle tips?\nLet’s explore ways to feel even better together!💪✨", reply_markup=reply_markup)
            return

    ai_response = get_medical_assistant_response(text)
    await update.message.reply_text(ai_response)

# Help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✨ This is your custom command to get all the help you need! Just let me know what you're looking for, and I'll do my best to assist you. Whether it’s medication reminders, healthy tips, or anything else, I’m here for you! 💖")

# Custom command
async def custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('💪 Your health is your greatest asset! Every small step you take today leads to a stronger, brighter tomorrow. Keep going—your future self will thank you! 🌟')

# Error handler
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')

if __name__ == '__main__':
    print('Starting bot...')
    app = Application.builder().token(TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('custom', custom_command))

    # Button callback handler
    app.add_handler(CallbackQueryHandler(button_callback))

    # Message handler for text
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Error handler
    app.add_error_handler(error)

    # Start polling
    print('Polling...')
    app.run_polling(poll_interval=3)
