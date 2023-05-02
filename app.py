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
# https://docs.python-telegram-bot.org/en/stable/
# https://github.com/python-telegram-bot/python-telegram-bot/wiki/Extensions---Your-first-Bot
# bot api features:
# https://core.telegram.org/bots/features#what-features-do-bots-have

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

NATIVE_LANGUAGE = cloudlanguagetools.languages.Language.en

# conversation states
USER_INPUT, CHANGE_LANGUAGE = range(2)


def get_default_transliteration(language):
    transliteration_candidates = [x for x in clt_language_data['transliteration_options'] if x['language_code'] == language.name]
    if language in [cloudlanguagetools.languages.Language.zh_cn,
        cloudlanguagetools.languages.Language.zh_tw,
        cloudlanguagetools.languages.Language.zh_tw,
        cloudlanguagetools.languages.Language.zh_lit,
        cloudlanguagetools.languages.Language.yue]:
        # pprint.pprint(transliteration_candidates)
        transliteration_candidates = [x for x in transliteration_candidates 
            if x['service'] == cloudlanguagetools.constants.Service.MandarinCantonese.name 
            and x['transliteration_key']['spaces'] == False
            and x['transliteration_key']['tone_numbers'] == False]
    return transliteration_candidates[0]


# pick the default translation option, if DeepL service is available, use it
def get_default_translation_service(from_language, to_language):
    from_language_entries = [x for x in clt_language_data['translation_options'] if x['language_code'] == from_language.name]
    to_language_entries = [x for x in clt_language_data['translation_options'] if x['language_code'] == to_language.name]
    # get the keys for 'service' which are common between from_language_entries and to_language_entries
    from_service_keys = [x['service'] for x in from_language_entries]
    to_service_keys = [x['service'] for x in to_language_entries]
    common_service_keys = list(set(from_service_keys) & set(to_service_keys))
    translation_services = {}
    for service in common_service_keys:
        from_entry = [x for x in from_language_entries if x['service'] == service][0]
        to_entry = [x for x in to_language_entries if x['service'] == service][0]
        translation_services[service] = {
            'service': service,
            'source_language_id': from_entry['language_id'],
            'target_language_id': to_entry['language_id'],
        }
    # prioritize DeepL service if available
    if cloudlanguagetools.constants.Service.DeepL.name in translation_services:
        return translation_services[cloudlanguagetools.constants.Service.DeepL.name]
    # otherwise, pick Azure
    if cloudlanguagetools.constants.Service.Azure.name in translation_services:
        return translation_services[cloudlanguagetools.constants.Service.Azure.name]
    # if the translation_services dict is empty, throw an exception
    if len(translation_services) == 0:
        raise Exception('no common translation services found')
    # by defaut, pick the first service
    return list(translation_services.values())[0]


def get_default_tokenization_option(language):
    tokenization_candidates = [x for x in clt_language_data['tokenization_options'] if x['language_code'] == language.name]
    if language in [cloudlanguagetools.languages.Language.zh_cn,
        cloudlanguagetools.languages.Language.zh_tw,
        cloudlanguagetools.languages.Language.zh_tw,
        cloudlanguagetools.languages.Language.zh_lit,
        cloudlanguagetools.languages.Language.yue]:
        # prefer jieba
        tokenization_candidates = [x for x in tokenization_candidates if x['tokenization_key'] == {'model_name': 'zh_jieba'}]
    pprint.pprint(tokenization_candidates)
    return tokenization_candidates[0]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, 
        text="Please enter a sentence in your target language (language that you are learning)")
    context.user_data.clear()

async def perform_sentence_transformations(update: Update, context: ContextTypes.DEFAULT_TYPE):
 
    input_text = context.user_data['input_text']
    language = context.user_data['language']

    # message = f'here are the translation and transliteration for {input_text}:'
    # await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

    # translate
    # =========
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.constants.ChatAction.TYPING )
    translation_service = get_default_translation_service(language, cloudlanguagetools.languages.Language.en)
    translation = clt_manager.get_translation(input_text, translation_service['service'], translation_service['source_language_id'], translation_service['target_language_id'])
    context.user_data['translation'] = translation
    # translation, tokens = clt_manager.openai_single_prompt(f'translate to English: {input_text}')
    await context.bot.send_message(chat_id=update.effective_chat.id, text=translation)

    # transliterate
    # =============
    # look for transliterations
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.constants.ChatAction.TYPING )
    transliteration_option = get_default_transliteration(language)
    transliteration = clt_manager.get_transliteration(input_text, transliteration_option['service'], transliteration_option['transliteration_key'])
    context.user_data['transliteration'] = transliteration
    await context.bot.send_message(chat_id=update.effective_chat.id, text=transliteration)

    # breakdown
    # =========
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.constants.ChatAction.TYPING )
    tokenization_option = get_default_tokenization_option(language)
    breakdown = clt_manager.get_breakdown(input_text, tokenization_option, translation_service, transliteration_option)
    # pprint.pprint(breakdown)
    result_lines = []
    for entry in breakdown:
        lemma = ''
        if entry['lemma'].lower() != entry['token'].lower():
            lemma = f" ({entry['lemma']})"
        pos_description = ''
        if 'pos_description' in entry:
            pos_description = f" ({entry['pos_description']})"
        result = f"{entry['token']}{lemma}: {entry.get('transliteration', '')} - {entry.get('translation', '')}{pos_description}"
        result_lines.append(result)
    breakdown_result = '\n'.join(result_lines)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=breakdown_result)

    # 
    question_language = NATIVE_LANGUAGE
    message = f'Questions about this sentence ? Ask in {question_language.lang_name}.' + \
    f' Otherwise, write a new sentence in {language.lang_name}'
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)


async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # detect language
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.constants.ChatAction.TYPING )

    input_text = update.message.text
    detected_language = clt_manager.detect_language([input_text])
    # do we have input_text set already ?
    if 'input_text' not in context.user_data or detected_language != cloudlanguagetools.languages.Language.en:
        # this input can only be the target language sentence
        previous_language = context.user_data.get('language', None)
        context.user_data['input_text'] = input_text
        
        # did the user override the language ?
        if 'override_language' in context.user_data:
            detected_language = context.user_data['override_language']
        context.user_data['language'] = detected_language

        # notify the user about the detected language (first time we are encountering this language)
        if previous_language != detected_language:
            message = f"I'm assuming the sentence '{input_text}' is in {detected_language.lang_name}, /changelanguage to change"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

        await perform_sentence_transformations(update, context)
    else:
        # do we have an input sentence ?
        if 'input_text' not in context.user_data:
            # we don't have a sentence to work on
            await context.bot.send_message(chat_id=update.effective_chat.id, text='Please enter a sentence in the target language (language that you are learning) first.)')
        else:
            # this is a question about the existing sentence
            input_sentence = context.user_data['input_text']
            language = context.user_data['language']
            messages = [
                    {"role": "system", "content": f"You are an helpful language learning assistant. Your role is to answer questions about the {language.lang_name} sentence '{input_sentence}'"},
                    {"role": "user", "content": input_text}
            ]
            response = clt_manager.openai_full_query(messages)
            question_response = response['choices'][0]['message']['content']
            await context.bot.send_message(chat_id=update.effective_chat.id, text=question_response)

    # default is to go back to user input
    return USER_INPUT

async def handle_change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.constants.ChatAction.TYPING )
    if 'input_text' not in context.user_data:
        # user must enter a sentence first
        await context.bot.send_message(chat_id=update.effective_chat.id, text='Please enter a sentence in the target language (language that you are learning) first.)')
        return USER_INPUT
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text='What language is the sentence in ? Type it in.')
        return CHANGE_LANGUAGE

async def handle_change_language_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    input_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.constants.ChatAction.TYPING )

    # prepare language code to language name mappings for chatgpt
    language_code_entries = [f'{x.name}: {x.lang_name}' for x in cloudlanguagetools.languages.Language]
    language_code_entries_list_str = '\n'.join(language_code_entries)

    messages = [
            {"role": "system", "content": "You are an assistant which will give language codes when a user types in a language name. the list of language codes to language name mappings are as follows:\n" 
                + language_code_entries_list_str},
            {"role": "user", "content": "cantonese"},
            {"role": "assistant", "content": "yue"},
            {"role": "user", "content": "English"},
            {"role": "assistant", "content": "en"},
            {"role": "user", "content": "mandarin"},
            {"role": "assistant", "content": "zh_cn"},
            {"role": "user", "content": "French"},
            {"role": "assistant", "content": "fr"},            
            {"role": "user", "content": "canadian french"},
            {"role": "assistant", "content": "fr_ca"},
            {"role": "user", "content": input_text},
    ]
    # pprint.pprint(messages)
    response = clt_manager.openai_full_query(messages)
    # pprint.pprint(response)
    language_code_str = response['choices'][0]['message']['content']

    language = cloudlanguagetools.languages.Language[language_code_str]

    # store result, and notify user
    sentence = context.user_data['input_text']
    message = f"Got it, the language of sentence '{sentence}' is {language.lang_name}. I'll assume everything not in {NATIVE_LANGUAGE.lang_name} is also {language.lang_name} (/start to reset)"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    context.user_data['override_language'] = language
    context.user_data['language'] = language

    # now, process sentence again
    await perform_sentence_transformations(update, context)

    # and go back to USER_INPUT loop
    return USER_INPUT



async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return telegram.ext.ConversationHandler.END

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    start_handler = CommandHandler("start", start)

    conversation_handler = telegram.ext.ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & (~filters.COMMAND), handle_user_input)],
        states={
            USER_INPUT: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), handle_user_input),
                CommandHandler("changelanguage", handle_change_language )
            ],
            CHANGE_LANGUAGE: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_change_language_response)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],

    )

    application.add_handler(start_handler)
    application.add_handler(conversation_handler)
    application.run_polling()