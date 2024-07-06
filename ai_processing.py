from openai import OpenAI
import sys
import os 
from dotenv import load_dotenv
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from prompts import system_prompt_task, system_prompt_asset

load_dotenv()

def get_current_date():
    now = datetime.now()
    day_of_week = now.strftime('%A')
    date = now.strftime('%Y-%m-%d')
    return f"{date}, {day_of_week}"

def transcribe_audio(file_path):
    client = OpenAI()
    with open(file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file,
            response_format="text"  
        )
    return transcript

def process_transcription(text):

    current_date = get_current_date()
    
    llm = ChatOpenAI(model_name="gpt-4o-2024-05-13", temperature=0, api_key=os.getenv('OPENAI_API_KEY'))
    chat = llm
    messages = [
    SystemMessage(
        content=f'Current date: {current_date}. {system_prompt_task}'
    ),
    HumanMessage(content=f'Now, format the following text accordingly (on English): {text}'),
        ]
    
    response = chat.invoke(messages)
    
    return response.content

def generate_asset_page_title(extracted_text):
    
    llm = ChatOpenAI(model_name="gpt-4o-2024-05-13", temperature=0, api_key=os.getenv('OPENAI_API_KEY'))
    chat = llm
    messages = [
    SystemMessage(
        content=f'{system_prompt_asset}'
    ),
    HumanMessage(content=f'{extracted_text}. JSON output:'),
        ]
    
    response = chat.invoke(messages)
    
    return response.content