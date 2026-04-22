"""Интеграция с VLM-моделью для классификации изображений и извлечения содержимого."""

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
    """Создает клиента OpenAI при наличии API-ключа в окружении."""
    api_key = os.environ.get("API_KEY")
    if not api_key:
        print("ВНИМАНИЕ: API_KEY не найден в .env файле.")
        return None
    return OpenAI(api_key=api_key, base_url="https://api.vsegpt.ru/v1")

def call_vlm_for_image(client: OpenAI, img_path: Path) -> dict:
    """Отправляет изображение в VLM и возвращает распарсенный JSON-результат."""
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

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="vis-meta-llama/llama-3.2-11b-vision-instruct",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
                        ],
                    }
                ],
                max_tokens=6000,
                temperature=0.0, # Чтобы был воспроизводимый результат
                timeout=30
            )
            
            raw_text = response.choices[0].message.content
            json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if not json_match:
                raise ValueError("JSON не найден")
                
            res = json.loads(json_match.group())
            cls = res.get("class", "figures")
            elements = res.get("elements", [])
            
            if cls in ("table", "many_tables"):
                if not elements:
                    raise ValueError(f"Class '{cls}' requires elements")
                if not any(is_valid_html_table(str(el)) for el in elements):
                    raise ValueError("Valid HTML table structure not found in response")
                    
            for el in elements:
                if isinstance(el, str) and "<table" in el.lower():
                    if not is_valid_html_table(el):
                        raise ValueError(f"Broken HTML table found in class '{cls}'")
                        
            return res

        except Exception as e:
            print(f"Ошибка VLM (Попытка {attempt+1}/3): {e}")
            time.sleep(2)
            
    return {"class": "figures", "elements": []}