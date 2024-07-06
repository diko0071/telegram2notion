import os
from dotenv import load_dotenv
import json
from notion_client import Client
from bs4 import BeautifulSoup
import requests
import fitz
from ai_processing import generate_asset_page_title
from langchain_community.document_loaders import PyPDFLoader
load_dotenv() 

NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
NOTION_DATABASE_ID_ASSETS = os.getenv('NOTION_DATABASE_ID_ASSETS')
notion = Client(auth=NOTION_TOKEN)

def extract_text_from_pdf(url):
    loader = PyPDFLoader(url)

    pages = loader.load_and_split()

    return pages[0].page_content

def extract_info_from_html(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.find('title').text if soup.find('title') else 'No title found'
        description = soup.find('meta', attrs={'name': 'description'})['content'] if soup.find('meta', attrs={'name': 'description'}) else 'No description found'
        return title, description
    else:
        return 'Error', 'Could not fetch the page'


def parse_content_structure(content):
    url = content['url']
    
    if '/pdf' in url:
        extracted_text = extract_text_from_pdf(url)
        return extracted_text
    else:
        title, description = extract_info_from_html(url)
        formatted_output = f"Title: {title}, Description: {description}"
        return formatted_output


def parse_gpt_output(gpt_output):

    if "```json" in gpt_output:
        gpt_output = gpt_output.replace("```json", "").replace("```", "").strip()
    elif "'''json" in gpt_output: 
        gpt_output = gpt_output.replace("'''json", "").rstrip("'''").strip()
    
    content = json.loads(gpt_output)
    
    extracted_params = {
        "date": content.get("date", ""),
        "title": content.get("title", ""),
        "focus": content.get("focus?", False),
        "project": content.get("Project", ""),
        "content": content.get("content", ""),
        "url": content.get("url", ""),
        "type": content.get("type", "")
    }
    
    return extracted_params

def parse_asset_page_gpt_output(gpt_output):
    if "```json" in gpt_output:
        gpt_output = gpt_output.replace("```json", "").replace("```", "").strip()
    elif "'''json" in gpt_output: 
        gpt_output = gpt_output.replace("'''json", "").rstrip("'''").strip()
    
    content = json.loads(gpt_output)
    
    extracted_params = {
        "title": content.get("title", ""),
        "topics": [topic["name"] for topic in content.get("topic", [])]
    }
    return extracted_params


def create_task_page(content, notion_client, asset_page_url=None):
    # Define the basic structure for the children blocks
    children_blocks = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": content['content']
                        }
                    }
                ]
            }
        }
    ]
    
    # If there's an asset page URL, add a link to it in a new paragraph block
    if asset_page_url:
        children_blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Asset page",
                                "link": {
                                    "url": asset_page_url
                                }
                            },
                            "annotations": {
                                "bold": True,
                                "italic": False,
                                "strikethrough": False,
                                "underline": False,
                                "code": False,
                                "color": "default"
                            }
                        }
                    ]
                }
            }
        )

    # Create the task page with the specified children blocks
    page = notion_client.pages.create(
        parent={"database_id": NOTION_DATABASE_ID},
        properties={
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": content['title']
                        }
                    }
                ]
            },
            "Date": {
                "date": {
                    "start": content['date']
                }
            },
            "Focus?": {
                "checkbox": content['focus']
            },
            "Project": {
                "select": {
                    "name": content['project'] if content['project'] else 'Personal'
                }
            },
            "Timeline": {
                "select": {
                    "name": "Daily"
                }
            },
        },
        children=children_blocks
    )
    return page

def create_asset_page(content, notion_client):
    extracted_info = parse_content_structure(content)

    json_asset_page = generate_asset_page_title(extracted_info)

    structure = parse_asset_page_gpt_output(json_asset_page)

    topics_multi_select = [{"name": topic} for topic in structure["topics"]]

    page = notion_client.pages.create(
        parent={"database_id": NOTION_DATABASE_ID_ASSETS},
        properties={
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": structure["title"]
                        }
                    }
                ]
            },
            "URL": {
                "url": content['url']
            },
            "Type": {
                "multi_select": [
                   {"name": content['type']} if content['type'] else {}
                ]
            },
            "Topic": {
                "multi_select": topics_multi_select
            },
            "Status": {
                "select": {
                    "name": "To Do"
                }
            },
        }
    )
    return page

def add_to_notion(gpt_output):
    try:
        content = parse_gpt_output(gpt_output)
        
        # Initialize asset_page_url to None
        asset_page_url = None

        asset_page = None

        # Create the asset page if 'type' is specified in the content
        if content['type'] and content['url']:
            asset_page = create_asset_page(content, notion)
            asset_page_url = f"https://www.notion.so/{asset_page['id'].replace('-', '')}"
            print(f"Asset page created: {asset_page_url}")
        else:
            print("No type specified, skipping asset page creation.")

        # Pass the asset_page_url to create_task_page function
        task_page = create_task_page(content, notion, asset_page_url)
        task_page_url = f"https://www.notion.so/{task_page['id'].replace('-', '')}"
        print(f"Main page created: {task_page_url}")

        return task_page_url, asset_page_url, asset_page

    except json.JSONDecodeError as json_error:
        print(f"JSON parsing failed: {json_error}")
        return None, None, None  # Return None, None in case of an error
    except Exception as e:
        print(f"Failed to add to Notion: {e}")
        return None, None, None # Return None, None in case of an error