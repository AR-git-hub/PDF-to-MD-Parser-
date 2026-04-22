import re

def is_valid_html_table(html: str) -> bool:
    html = html.lower()
    return "<table" in html and "</table>" in html and "<tr" in html

def parse_html_table_to_md(html_str: str) -> str:
    """Парсит HTML таблицу в Markdown по ТЗ хакатона."""
    grid: dict[tuple[int, int], str] = {}
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html_str, re.DOTALL | re.IGNORECASE)
    
    r = 0
    header_row_indices = []

    for row_html in rows:
        cells = re.findall(r'<(t[hd])([^>]*)>(.*?)</\1>', row_html, re.DOTALL | re.IGNORECASE)
        c = 0
        is_header_row = True
        
        for tag, attrs, content in cells:
            tag = tag.lower()
            if tag == 'td': 
                is_header_row = False
            
            colspan, rowspan = 1, 1
            col_m = re.search(r'colspan=["\']?(\d+)["\']?', attrs, re.IGNORECASE)
            if col_m: colspan = int(col_m.group(1))
            row_m = re.search(r'rowspan=["\']?(\d+)["\']?', attrs, re.IGNORECASE)
            if row_m: rowspan = int(row_m.group(1))
            
            content = re.sub(r'<[^>]+>', '', content).strip()
            content = content.replace('\n', ' ').replace('|', '&#124;')
            
            while (r, c) in grid:
                c += 1
                
            for i in range(rowspan):
                for j in range(colspan):
                    grid[(r + i, c + j)] = content
            c += colspan
        
        if is_header_row and cells:
            header_row_indices.append(r)
        r += 1
    
    if not grid: 
        return ""
    
    max_r = r
    max_c = max([col for (row, col) in grid.keys()]) + 1
    
    if not header_row_indices:
        header_row_indices = [0]
        
    header_cols = []
    for c in range(max_c):
        col_headers = []
        for hr in header_row_indices:
            val = grid.get((hr, c), "")
            if val and (not col_headers or col_headers[-1] != val):
                col_headers.append(val)
        header_cols.append("_".join(col_headers) if col_headers else "Column") # склейка многоуровневых заголовков через _ , если они отличаются, иначе просто один заголовок или "Column" по умолчанию
        
    md = "|" + "|".join(header_cols) + "|\n"
    md += "|" + "|".join(["---"] * max_c) + "|\n"
    
    for row in range(max_r):
        if row in header_row_indices: continue
        row_data = [grid.get((row, col), "") for col in range(max_c)]
        md += "|" + "|".join(row_data) + "|\n"
        
    return md.strip()