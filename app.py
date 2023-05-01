import logging
import os
import pprint
import json

import cloudlanguagetools
import cloudlanguagetools.constants
import cloudlanguagetools.languages
import cloudlanguagetools.servicemanager


import logging
# configure basic logging with file, line numbers and timestamps
def configure_logging():
    logger = logging.getLogger()
    while logger.hasHandlers():
        logger.removeHandler(logger.handlers[0])
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
configure_logging()
logger = logging.getLogger(__name__)


# docs
# https://github.com/python-telegram-bot/python-telegram-bot
# https://github.com/python-telegram-bot/python-telegram-bot/wiki/Extensions---Your-first-Bot

import telegram

from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes

clt_manager = cloudlanguagetools.servicemanager.ServiceManager()
clt_manager.configure_default()

LANGUAGE_DATA_CACHE_PATH = '.cache/language_data_v1.json'

# write clt_language_data to .cache/language_data_v1.json
def cache_clt_language_data_json():
    logger.info('caching clt_language_data to .cache/language_data_v1.json')
    clt_language_data = clt_manager.get_language_data()
    with open('.cache/language_data_v1.json', 'w') as outfile:
        json.dump(clt_language_data, outfile, indent=4)
# load LANGUAGE_DATA_CACHE_PATH
def load_language_data():
    logger.info('loading clt_language_data from .cache/language_data_v1.json')
    with open(LANGUAGE_DATA_CACHE_PATH) as json_file:
        return json.load(json_file)

CLT_DATA_LOAD_FROM_CACHE = True
if CLT_DATA_LOAD_FROM_CACHE:
    clt_language_data = load_language_data()
else:
    clt_language_data = cache_clt_language_data_json()

# pprint.pprint(clt_language_data)


logger = logging.getLogger()
while logger.hasHandlers():
    logger.removeHandler(logger.handlers[0])
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


TOKEN = os.environ['TELEGRAM_BOT_TOKEN']


def get_default_transliteration(language):
    transliteration_candidates = [x for x in clt_language_data['transliteration_options'] if x['language_code'] == language.name]
    if language in [cloudlanguagetools.languages.Language.zh_cn,
        cloudlanguagetools.languages.Language.zh_tw,
        cloudlanguagetools.languages.Language.zh_tw,
        cloudlanguagetools.languages.Language.zh_lit,
        cloudlanguagetools.languages.Language.yue]:
        pprint.pprint(transliteration_candidates)
        transliteration_candidates = [x for x in transliteration_candidates 
            if x['service'] == cloudlanguagetools.constants.Service.MandarinCantonese.name 
            and x['transliteration_key']['spaces'] == False
            and x['transliteration_key']['tone_numbers'] == False]
    return transliteration_candidates[0]


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

    # transliterate
    # look for transliterations
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.constants.ChatAction.TYPING )
    transliteration_option = get_default_transliteration(detected_language)
    transliteration = clt_manager.get_transliteration(input_text, transliteration_option['service'], transliteration_option['transliteration_key'])
    await context.bot.send_message(chat_id=update.effective_chat.id, text=transliteration)



if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)
    application.add_handler(echo_handler)
    
    application.run_polling()