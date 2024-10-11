from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import threading
import pandas as pd
import asyncio
import yaml
from pathlib import Path



THIS_FOLDER = Path(__file__).parent.resolve()
config_path = THIS_FOLDER / "config.yml"
# Load configuration from file config.yml
with open(config_path, 'r') as config_file:
    config = yaml.safe_load(config_file)

# Configure Telegram bot with token
telegram_token = config['tg_token']
telegram_myid = config['tg_myid']


# Global shared (between Lichess and Telegram Bots) functions
def load_global_db(search_for='', game_for='', action='', add_value=0):
    """
    This csv file will be shared between Lichess and Telegram Bots to set params
    Load the param(s) you are setting
    :param search_for: str to tell what column to access
    :param game_for: value to access if a particular opponent or game to set params
    :param action: set or get
    :param add_value: value to be set
    :return: DataFrame to access modified params
    """
    # Set level from Telegram db
    level_csv = THIS_FOLDER / "database/Stockfish_level.csv"
    df_level = pd.read_csv(level_csv)
    if action == 'get':
        set_level = None
        if game_for == 'global':
            df_level = df_level[df_level['Game'] == 'global']
            if search_for == 'level' and len(df_level) == 1:
                set_level = df_level['Level'][0]
                return set_level
    elif action == 'set':
        if game_for == 'global':
            df_level.loc[df_level['Game'] == 'global', 'Level'] = add_value
            df_level.to_csv(level_csv)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show welcome message and save new user after telling story, char settings and account details
    :params: update - context
    :variables: keyboard - user
    :Dataframe: df_users
    """
    user = update.effective_user
    await update.message.reply_text("Welcome! I'm Zoe, the Lichess Chess Bot!")
    await update.message.reply_text("Type /menu to see the list of functions or /cancel to come back here")
    await menu(update, context)


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show every commands in a inline menu
    """
    user = update.effective_user
    await update.message.reply_text(
        "Here's the list of my functions, divided per categories! Click one and i'll explain everything it does (more to come!)!")

    keyboard = [
        [
            InlineKeyboardButton("🧑‍🎤 User Profile", callback_data='menu_start')
        ],
        [
            InlineKeyboardButton("💰 Earn coins", callback_data='menu_earn_coins'),
        ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("What do you want to do?", reply_markup=reply_markup)


async def answers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Pre-made answers
    """
    global check, text_received
    user = update.effective_user
    text_received = update.message.text
    try:
        if user.id == telegram_myid:
            # Search comand
            if text_received.startswith('set_level'):
                if text_received[-2].startswith('0'):
                    set_value = int(text_received[-1])
                    load_global_db('level', 'global', 'set', set_value)
                else:
                    set_value = int(text_received[-2:])
                    load_global_db('level', 'global', 'set', set_value)
                value_setted = load_global_db('level', 'global', 'get', 0)
                await update.message.reply_text(f"Level setted: {value_setted}")
    except:
        await update.message.reply_text("Wrong value for level")


def send_message_to_telegram(telegram_token, message):
    bot = Bot(token=telegram_token)
    asyncio.run(bot.send_message(chat_id=telegram_myid, text=message))


def activate_bot():
    # Load Application
    application = Application.builder().token(telegram_token).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('menu', menu))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answers))

    print('Bot Telegram activated..')
    application.run_polling()



