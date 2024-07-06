from telegram.ext import MessageHandler, Filters
from notion_handler import add_to_notion
from ai_processing import transcribe_audio, process_transcription
import requests
import os
from pydub import AudioSegment
import io
import os
import json
import tempfile
from io import BytesIO
from telegram import ParseMode
from urllib.parse import quote


ALLOWED_USERS = [int(user_id) for user_id in os.getenv('ALLOWED_USERS', '').split(',') if user_id.isdigit()]


def handle_message(update, context):
    processed_text = None

    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        update.message.reply_text('You are not allowed to use this bot!')
        return
    
    if update.message.text:
        user_message = update.message.text
        print("Processing text message...")
        processed_output = process_transcription(user_message)
        parsed_output = json.loads(processed_output)
        task_page_url, asset_page_url, asset_page = add_to_notion(processed_output)
        title = parsed_output.get('title', 'a task') 
        date = parsed_output.get('date', 'a certain date') 
        project = parsed_output.get('Project', 'your project')
        
        if asset_page_url and asset_page:
            asset_page_title = asset_page['properties']['Name']['title'][0]['plain_text']
            response_message = f"I added task: <a href='{task_page_url}'>{title}</a> on {date} in {project}. Also, new asset name: <a href='{asset_page_url}'>{asset_page_title}</a>."
        else:
            response_message = f"I added task: <a href='{task_page_url}'>{title}</a> on {date} in {project}."

        try:
            update.message.reply_text(response_message, parse_mode=ParseMode.HTML)
            print(response_message)
        except Exception as e:
            print(f"Failed to send message: {e}")
    
    if update.message.voice:
        voice_message = update.message.voice
        voice_file_id = voice_message.file_id
        print(f"Received voice message with ID: {voice_file_id}")

        file_info = context.bot.getFile(voice_file_id)
        response = requests.get(file_info.file_path)

        if response.status_code == 200:
            voice_file_stream = BytesIO(response.content)
            audio = AudioSegment.from_file(voice_file_stream, format="ogg")
            mp3_file_stream = BytesIO()
            audio.export(mp3_file_stream, format="mp3")
            mp3_file_stream.seek(0)

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_file.write(mp3_file_stream.getvalue())
                temp_file_path = tmp_file.name

            transcription = transcribe_audio(temp_file_path)

            os.remove(temp_file_path)
        print("Transcribing audio...")
        processed_output = process_transcription(transcription)
        parsed_output = json.loads(processed_output)
        task_page_url, asset_page_url, asset_page = add_to_notion(processed_output)
        title = parsed_output.get('title', 'a task') 
        date = parsed_output.get('date', 'a certain date') 
        project = parsed_output.get('Project', 'your project')

        user_message = transcription
        
        if asset_page_url and asset_page:
            asset_page_title = asset_page['properties']['Name']['title'][0]['plain_text']
            response_message = f"I added task: <a href='{task_page_url}'>{title}</a> on {date} in {project}. Also, new asset name: <a href='{asset_page_url}'>{asset_page_title}</a>."
        else:
            response_message = f"I added task: <a href='{task_page_url}'>{title}</a> on {date} in {project}."

        try:
            update.message.reply_text(response_message, parse_mode=ParseMode.HTML)
            print(response_message)
        except Exception as e:
            print(f"Failed to send message: {e}")

message_handler = MessageHandler(Filters.text | Filters.voice & ~Filters.command, handle_message)
