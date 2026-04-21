import re
from difflib import SequenceMatcher
from utils.html_parser import parse_html_table_to_md

def process_extracted_elements(elements: list) -> str:
    processed = []
    for el in elements:
        if not isinstance(el, str): continue
        if "<table" in el.lower() and "</table>" in el.lower():
            md_table = parse_html_table_to_md(el)
            processed.append(md_table if md_table else el)
        else:
            processed.append(el)
    return "\n\n".join(processed)
