import logging
import openai
import asyncio
import aiohttp
import traceback
import os
import srt
import ass
from datetime import timedelta
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
OPENAI_API_KEY="sk-None-8sibTULhasBuLDxkzxGVT3BlbkFJWxSw02sQ4jOwOKSiCVcR"
TELEGRAM_TOKEN="7435392711:AAH88KACBRpL9S9AoJ9Fk8sVAsR8sOHPASk"
TELEGRAM_API_HASH="1f20df54dfd91bcee05278d3b01da2c7"
TELEGRAM_API_ID="7391573"

# OpenAI API key from environment variable
openai.api_key = OPENAI_API_KEY


TELEGRAM_BOT_TOKEN = TELEGRAM_TOKEN

# Create a Pyrogram client
app = Client("hinglish_bot", api_id=TELEGRAM_API_ID, api_hash=TELEGRAM_API_HASH, bot_token=TELEGRAM_BOT_TOKEN)

# Function to translate text to Hinglish
def translate_to_hinglish(text):
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"Translate the following text to Hinglish:\n\n{text}",
            max_tokens=1000,
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

# Start command handler
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text('Send me a subtitle file (SRT or ASS format) and I will translate it to Hinglish and convert it to both SRT and ASS formats.')

# File message handler
@app.on_message(filters.document & filters.incoming)
async def handle_file(client, message: Message):
    document = message.document

    if document.mime_type not in ["application/x-subrip", "application/x-ass"]:
        await message.reply_text('Unsupported file format. Please send an SRT or ASS file.')
        return

    file_path = await app.download_media(document)

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

    await message.reply_text('Translation complete. Here are your files:')
    await message.reply_document(document=translated_srt_path)
    await message.reply_document(document=translated_ass_path)

    os.remove(file_path)
    os.remove(translated_srt_path)
    os.remove(translated_ass_path)

async def ping_server():
    sleep_time = 40
    while True:
        await asyncio.sleep(sleep_time)
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            ) as session:
                async with session.get("https://ai-hindi-sub-bot-t2oy.onrender.com") as resp:
                    logging.info("Pinged server with response: {}".format(resp.status))
        except TimeoutError:
            logging.warning("Couldn't connect to the site URL..!")
        except Exception:
            traceback.print_exc()
# Run the bot
if __name__ == "__main__":
    asyncio.run(ping_server())
    app.run()
