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
    :param search_for: str to tell what column to access (Level, Think or Wait_Api)
    :param game_for: value to access if a particular opponent or game to set params
    :param action: set or get
    :param add_value: value to be set
    :return: DataFrame to access modified params
    """
    # Set level from Telegram db
    global_csv = THIS_FOLDER / "database/Set_Stockfish.csv"
    df_global = pd.read_csv(global_csv)
    if action == 'get':
        if game_for == 'global':
            df_global = df_global[df_global['Game'] == game_for]
            if search_for == 'level' and len(df_global) == 1:
                return df_global['Level'][0]
            elif search_for == 'think' and len(df_global) == 1:
                return df_global['Think'][0]
            elif search_for == 'hash' and len(df_global) == 1:
                return df_global['Hash'][0]
            elif search_for == 'depth' and len(df_global) == 1:
                return df_global['Depth'][0]
            elif search_for == 'thread' and len(df_global) == 1:
                return df_global['Thread'][0]
            elif search_for == 'wait_api' and len(df_global) == 1:
                set_wait = df_global['Wait_Api'][0]
                return set_wait
    elif action == 'set':
        if game_for == 'global':
            if search_for == 'level':
                df_global.loc[df_global['Game'] == game_for, 'Level'] = add_value
                df_global.to_csv(global_csv)
            elif search_for == 'think':
                df_global.loc[df_global['Game'] == game_for, 'Think'] = add_value
                df_global.to_csv(global_csv)
            elif search_for == 'hash':
                df_global.loc[df_global['Game'] == game_for, 'Hash'] = add_value
                df_global.to_csv(global_csv)
            elif search_for == 'depth':
                df_global.loc[df_global['Game'] == game_for, 'Depth'] = add_value
                df_global.to_csv(global_csv)
            elif search_for == 'thread':
                df_global.loc[df_global['Game'] == game_for, 'Thread'] = add_value
                df_global.to_csv(global_csv)
            elif search_for == 'wait_api':
                df_global.loc[df_global['Game'] == game_for, 'Wait_Api'] = add_value
                df_global.to_csv(global_csv)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show welcome message and save new user after telling story, char settings and account details
    :params: update - context
    :variables: keyboard - user
    :Dataframe: df_users
    """
    user = update.effective_user
    await update.message.reply_text("Welcome! I'm Zoe, the Lichess Chess Bot!")
    await update.message.reply_text("You can check my website: https://chessbotzoe.pythonanywhere.com/")
    await update.message.reply_text("Type /menu to see the list of functions")
    await menu(update, context)


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show every command in an inline menu
    """
    user = update.effective_user
    await update.message.reply_text("Here's the list of my functions!")

    keyboard = [
        [
            InlineKeyboardButton("🚀 Stockfish engine for playing", callback_data='start'),
            InlineKeyboardButton("👀 Equilize my level with yours", callback_data='start'),
        ],
        [
            InlineKeyboardButton("🤖 Gemma2b AI for chat", callback_data='start'),
            InlineKeyboardButton("👨‍🏫 Human Opening moves", callback_data='start'),
        ],
        [
            InlineKeyboardButton("📮 Telegram Bot for info", callback_data='start'),
            InlineKeyboardButton("🌐 Bot website", callback_data='start'),
        ],
        [
            InlineKeyboardButton("..many more to come..", callback_data='start'),
        ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("(Work In Progress..)", reply_markup=reply_markup)


async def answers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Pre-made answers
    """
    global check, text_received
    user = update.effective_user
    text_received = update.message.text
    try:
        if user.id == telegram_myid:
            # Set Level
            if text_received.startswith('set_level'):
                if text_received[-2].startswith('0'):
                    set_value = int(text_received[-1])
                    load_global_db('level', 'global', 'set', set_value)
                else:
                    set_value = int(text_received[-2:])
                    load_global_db('level', 'global', 'set', set_value)
                value_setted = load_global_db('level', 'global', 'get', 0)
                await update.message.reply_text(f"Level setted: {value_setted}")
            # Set Thinking Time
            elif text_received.startswith('set_thinking'):
                set_think = int(text_received[12:])
                load_global_db('think', 'global', 'set', set_think)
                value_setted = load_global_db('think', 'global', 'get', 0)
                await update.message.reply_text(f"Thinking setted: {value_setted}s")
            # Set Hash Memory
            elif text_received.startswith('set_hash'):
                set_hash = int(text_received[8:])
                load_global_db('hash', 'global', 'set', set_hash)
                value_setted = load_global_db('hash', 'global', 'get', 0)
                await update.message.reply_text(f"Hash Memory setted: {value_setted}s")
            # Set Depth Moves
            elif text_received.startswith('set_depth'):
                set_depth = int(text_received[9:])
                load_global_db('depth', 'global', 'set', set_depth)
                value_setted = load_global_db('depth', 'global', 'get', 0)
                await update.message.reply_text(f"Depth moves setted: {value_setted}s")
            # Set Threads Number
            elif text_received.startswith('set_thread'):
                set_thread = int(text_received[10:])
                load_global_db('thread', 'global', 'set', set_thread)
                value_setted = load_global_db('thread', 'global', 'get', 0)
                await update.message.reply_text(f"Threads number setted: {value_setted}s")
            # Set Api Waiting Time (time.sleep)
            elif text_received.startswith('set_wait_api'):
                set_wait = int(text_received[12:])
                load_global_db('wait_api', 'global', 'set', set_wait)
                value_setted = load_global_db('wait_api', 'global', 'get', 0)
                await update.message.reply_text(f"Wait Api setted: {value_setted}s")
    except:
        await update.message.reply_text("Wrong value for setting..")


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



