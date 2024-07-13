import logging
import openai
import os
import srt
import ass
from datetime import timedelta
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAI API key from environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

# Telegram bot token from environment variable
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Function to translate text to Hinglish
def translate_to_hinglish(text):
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"Translate the following text to Hinglish:\n\n{text}",
            max_tokens=100,
            n=1,
            stop=None,
            temperature=0.5,
        )
        return response.choices[0].text.strip()
    except Exception as e:
        logger.error(f"Error in OpenAI API call: {e}")
        return text

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
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Send me a subtitle file (SRT or ASS format) and I will translate it to Hinglish and convert it to both SRT and ASS formats.')

# Message handler to process subtitle files
async def handle_file(update: Update, context: CallbackContext) -> None:
    file = await context.bot.get_file(update.message.document.file_id)
    file_path = f'/tmp/{update.message.document.file_name}'
    await file.download_to_drive(file_path)
    
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
        await update.message.reply_text('Unsupported file format. Please send an SRT or ASS file.')
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
    
    await update.message.reply_text('Translation complete. Here are your files:')
    await update.message.reply_document(document=InputFile(translated_srt_path))
    await update.message.reply_document(document=InputFile(translated_ass_path))

# Main function to start the bot
def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.MimeType("application/x-subrip"), handle_file))
    app.add_handler(MessageHandler(filters.Document.MimeType("application/x-ass"), handle_file))

    app.run_polling()

if __name__ == '__main__':
    main()
