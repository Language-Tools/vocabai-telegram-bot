import logging
import os
import cloudlanguagetools
import cloudlanguagetools.constants
import cloudlanguagetools.servicemanager


# docs
# https://github.com/python-telegram-bot/python-telegram-bot
# https://github.com/python-telegram-bot/python-telegram-bot/wiki/Extensions---Your-first-Bot

import telegram

from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes

clt_manager = cloudlanguagetools.servicemanager.ServiceManager()
clt_manager.configure_default()

logger = logging.getLogger()
while logger.hasHandlers():
    logger.removeHandler(logger.handlers[0])
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


TOKEN = os.environ['TELEGRAM_BOT_TOKEN']


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # detect language
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.constants.ChatAction.TYPING )
    input_text = update.message.text
    detected_language = clt_manager.detect_language([input_text])
    output = f'[{input_text}] detected language is: {detected_language}'
    await context.bot.send_message(chat_id=update.effective_chat.id, text=output)
    # translate
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.constants.ChatAction.TYPING )
    translation, tokens = clt_manager.openai_single_prompt(f'translate to English: {input_text}')
    await context.bot.send_message(chat_id=update.effective_chat.id, text=translation)

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)
    application.add_handler(echo_handler)
    
    application.run_polling()