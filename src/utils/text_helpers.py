"""Текстовые утилиты для постобработки извлеченных элементов и фильтрации шума."""

import re
from difflib import SequenceMatcher
from utils.html_parser import parse_html_table_to_md

def process_extracted_elements(elements: list) -> str:
    """Преобразует список элементов VLM в единый Markdown-текст."""
    processed = []
    for el in elements:
        if not isinstance(el, str): continue
        if "<table" in el.lower() and "</table>" in el.lower():
            md_table = parse_html_table_to_md(el)
            processed.append(md_table if md_table else el)
        else:
            processed.append(el)
    return "\n\n".join(processed)

def is_text_in_local_context_fuzzy(vlm_text: str, full_md: str, match_pos: int) -> bool:
    """Проверяет, присутствует ли извлеченный текст рядом с позицией изображения."""
    clean_vlm = re.sub(r'<[^>]+>', '', vlm_text).replace(" ", "").replace("\n", "").replace("|", "").replace("-", "")
    
    if len(clean_vlm) < 15: 
        return False
        
    fingerprint = clean_vlm[:100] 
    
    start_idx = max(0, match_pos - 1000)
    end_idx = min(len(full_md), match_pos + 1000)
    local_context = full_md[start_idx:end_idx]
    
    clean_local_md = re.sub(r'<[^>]+>', '', local_context).replace(" ", "").replace("\n", "").replace("|", "").replace("-", "")
    
    if fingerprint in clean_local_md:
        return True
        
    window_size = len(fingerprint)
    if len(clean_local_md) <= window_size:
        return SequenceMatcher(None, fingerprint, clean_local_md).ratio() > 0.65
        
    for i in range(0, len(clean_local_md) - window_size + 1, 5):
        chunk = clean_local_md[i:i+window_size]
        ratio = SequenceMatcher(None, fingerprint, chunk).ratio()
        if ratio > 0.65:
            return True
            
    return False

def remove_text_watermarks(text: str) -> str:
    """Удаляет из текста строки, которые являются типовыми водяными знаками."""
    watermarks = ["черновик", "draft", "копия", "образец", "секретно", "конфиденциально", "draf"]
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        clean_line = line.strip().lower()
        clean_line = re.sub(r'^#+\s*', '', clean_line)
        
        if not any(wm == clean_line or wm == clean_line.replace(" ", "") for wm in watermarks):
            cleaned_lines.append(line)
            
    return '\n'.join(cleaned_lines)