import logging
import openai
import os
import srt
import ass
from telegram import Update, InputFile
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, CallbackContext

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAI API key
openai.api_key = 'sk-None-8sibTULhasBuLDxkzxGVT3BlbkFJWxSw02sQ4jOwOKSiCVcR'

# Telegram bot token
TELEGRAM_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'

# Function to translate text to Hinglish
def translate_to_hinglish(text):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that translates text to Hinglish."},
            {"role": "user", "content": text}
        ]
    )
    return response['choices'][0]['message']['content'].strip()

# Function to convert SRT to ASS
def srt_to_ass(srt_content):
    subs = list(srt.parse(srt_content))
    ass_doc = ass.document.Document()
    ass_doc.styles.append(ass.styling.Style())
    for sub in subs:
        event = ass.document.Event()
        event.start = sub.start.total_seconds()
        event.end = sub.end.total_seconds()
        event.text = sub.content.replace('\n', '\\N')
        ass_doc.events.append(event)
    return str(ass_doc)

# Function to convert ASS to SRT
def ass_to_srt(ass_content):
    ass_doc = ass.document.Document.parse(ass_content)
    subs = []
    for event in ass_doc.events:
        start = timedelta(seconds=event.start)
        end = timedelta(seconds=event.end)
        content = event.text.replace('\\N', '\n')
        subs.append(srt.Subtitle(index=len(subs) + 1, start=start, end=end, content=content))
    return srt.compose(subs)

# Command handler to start the bot
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Send me a subtitle file (SRT or ASS format) and I will translate it to Hinglish and convert it to both SRT and ASS formats.')

# Message handler to process subtitle files
def handle_file(update: Update, context: CallbackContext) -> None:
    file = context.bot.get_file(update.message.document.file_id)
    file_path = f'/tmp/{update.message.document.file_name}'
    file.download(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        subtitle_content = f.read()
    
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension == '.srt':
        subs = list(srt.parse(subtitle_content))
    elif file_extension == '.ass':
        ass_doc = ass.document.Document.parse(subtitle_content)
        subs = []
        for event in ass_doc.events:
            start = timedelta(seconds=event.start)
            end = timedelta(seconds=event.end)
            content = event.text.replace('\\N', '\n')
            subs.append(srt.Subtitle(index=len(subs) + 1, start=start, end=end, content=content))
    else:
        update.message.reply_text('Unsupported file format. Please send an SRT or ASS file.')
        return
    
    translated_subs = []
    for sub in subs:
        translated_text = translate_to_hinglish(sub.content)
        translated_subs.append(srt.Subtitle(index=sub.index, start=sub.start, end=sub.end, content=translated_text))
    
    translated_srt_content = srt.compose(translated_subs)
    translated_ass_content = srt_to_ass(translated_srt_content)
    
    translated_srt_path = file_path.replace(file_extension, '_hinglish.srt')
    with open(translated_srt_path, 'w', encoding='utf-8') as f:
        f.write(translated_srt_content)
    
    translated_ass_path = file_path.replace(file_extension, '_hinglish.ass')
    with open(translated_ass_path, 'w', encoding='utf-8') as f:
        f.write(translated_ass_content)
    
    update.message.reply_text('Translation complete. Here are your files:')
    update.message.reply_document(document=InputFile(translated_srt_path))
    update.message.reply_document(document=InputFile(translated_ass_path))

# Main function to start the bot
def main() -> None:
    updater = Updater(TELEGRAM_TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.document.mime_type("application/x-subrip"), handle_file))
    dispatcher.add_handler(MessageHandler(Filters.document.mime_type("application/x-ass"), handle_file))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
