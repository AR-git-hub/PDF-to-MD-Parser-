import os
import io
import json
import base64
import re
import time
from pathlib import Path
from openai import OpenAI
from utils.html_parser import is_valid_html_table

def get_openai_client() -> OpenAI | None:
    api_key = os.environ.get("API_KEY")
    if not api_key:
        print("ВНИМАНИЕ: API_KEY не найден в .env файле.")
        return None
    return OpenAI(api_key=api_key, base_url="https://api.vsegpt.ru/v1")

def call_vlm_for_image(client: OpenAI, img_path: Path) -> dict:
    with open(img_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')

    prompt = """
    You are an expert in document layout analysis and OCR. Analyze the provided image and classify it.
    Note: The text might be a disconnected, random set of words in Russian and English.

    Classes:
    - "figures": Clean image, chart, photo without extractable text.
    - "figures_with_text": Image (diagram, flowchart) with extractable text inside.
    - "text": Scanned or rasterized text.
    - "watermark": Watermarks, page numbers, background noise. Do NOT extract text.
    - "table": A single data table.
    - "many_tables": Two or more tables.
    - "garbage": Chaotic mix of elements, fragments. MUST extract everything (can contain both text strings and HTML tables).

    INSTRUCTIONS FOR "elements" array:
    - If "figures" or "watermark": return elements = []
    - If "figures_with_text" or "text": return elements = ["string 1", "string 2"]
    - If "table": return elements = ["<table>...</table>"]
    - If "many_tables": return elements = ["<table 1 HTML>", "<table 2 HTML>"]
    - If "garbage": return elements = ["text line", "<table>...</table>", "another text"]

    CRITICAL FOR TABLES: 
    1. Output strictly the HTML code. 
    2. Preserve the exact grid structure: use colspan and rowspan. 
    3. Empty cells MUST be <td></td>. Do not skip them!
    4. For multi-level headers, use <th> tags inside <thead>. Do NOT manually join headers.

    Return STRICTLY valid JSON. Do NOT wrap it in Markdown formatting blocks.
    Example output format:
    {
      "class": "table",
      "elements": [
        "<table><thead><tr><th>Header1</th></tr></thead><tbody><tr><td>Value1</td><td></td></tr></tbody></table>"
      ]
    }
    """

    
            
    return {"class": "figures", "elements": []}