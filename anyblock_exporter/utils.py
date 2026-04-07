# utils.py

from typing import List, Dict, Any
import re
import unicodedata
import os

def sanitize_filename(filename: str, max_length: int = 150) -> str:
    if not filename.strip():
        return "Untitled"
    
    # Remove invalid characters, but keep spaces
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Truncate if too long
    if len(filename) > max_length:
        filename = filename[:max_length].rstrip()
    
    return filename or "Untitled"

def format_inline_text(text: str, marks: List[Dict[str, Any]], page_names: Dict[str, str] = None) -> str:
    if not marks:
        return text

    formatted_text = text
    offset = 0

    for mark in sorted(marks, key=lambda x: (x.get('range') or {}).get('from', 0)):
        range_info = mark.get('range') or {}
        start = range_info.get('from', 0) + offset
        end = range_info.get('to', 0) + offset
        mark_type = mark.get('type')

        if mark_type == 'Bold':
            formatted_text = f"{formatted_text[:start]}**{formatted_text[start:end]}**{formatted_text[end:]}"
            offset += 4
        elif mark_type == 'Italic':
            formatted_text = f"{formatted_text[:start]}*{formatted_text[start:end]}*{formatted_text[end:]}"
            offset += 2
        elif mark_type == 'Underscored':
            formatted_text = f"{formatted_text[:start]}_{formatted_text[start:end]}_{formatted_text[end:]}"
            offset += 2
        elif mark_type == 'Strikethrough':
            formatted_text = f"{formatted_text[:start]}~~{formatted_text[start:end]}~~{formatted_text[end:]}"
            offset += 4
        elif mark_type == 'Link':
            url = mark.get('param', '')
            formatted_text = f"{formatted_text[:start]}[{formatted_text[start:end]}]({url}){formatted_text[end:]}"
            offset += len(url) + 4
        elif mark_type == 'Mention':
            page_id = mark.get('param', '')
            if page_names and page_id in page_names:
                # Sanitize the name just like the filename
                from .utils import sanitize_filename
                display_name = sanitize_filename(page_names[page_id])
                formatted_text = f"{formatted_text[:start]}[[{display_name}]]{formatted_text[end:]}"
                # The original text within the range is replaced by [[name]]
                # so offset needs to account for the difference in length
                offset += (len(display_name) + 4) - (range_info.get('to', 0) - range_info.get('from', 0))
            else:
                # Fallback if name not found
                formatted_text = f"{formatted_text[:start]}[[{formatted_text[start:end]}]]{formatted_text[end:]}"
                offset += 4

    return formatted_text

def convert_table_to_markdown(table_block: Dict[str, Any], all_blocks: Dict[str, Any], page_names: Dict[str, str] = None) -> str:
    """Converts various hierarchical Anytype table structures into Markdown."""
    child_ids = table_block.get('childrenIds', [])
    
    # 1. Helper to find components
    def find_component(parent_ids, styles):
        for cid in parent_ids:
            blk = all_blocks.get(cid)
            if not blk: continue
            style = blk.get('layout', {}).get('style', '')
            if style in styles: return blk
            sub = find_component(blk.get('childrenIds', []), styles)
            if sub: return sub
        return None

    columns_container = find_component(child_ids, ['TableColumns', 'TableColumn'])
    rows_container = find_component(child_ids, ['TableRows', 'TableRow', 'TableRowsContainer'])

    if not columns_container or not rows_container:
        return ""

    # 2. Extract column info
    col_ids = columns_container.get('childrenIds', [])
    columns = []
    for cid in col_ids:
        cblk = all_blocks.get(cid)
        name = (cblk.get('text') or {}).get('text') if cblk else "Column"
        if not name and cblk:
            name = cblk.get('snapshot', {}).get('data', {}).get('details', {}).get('name', 'Column')
        columns.append(name)

    if not columns: return ""

    # 3. Extract rows and cells
    rows_data = []
    row_ids = rows_container.get('childrenIds', [])
    for rid in row_ids:
        rblk = all_blocks.get(rid)
        if not rblk: continue
        
        row_cells = []
        row_children = rblk.get('childrenIds', [])
        
        for cid in col_ids:
            # Try 1: Composite ID (RowID-ColID)
            cell_id = f"{rid}-{cid}"
            cell_blk = all_blocks.get(cell_id)
            
            # Try 2: Direct child lookup
            if not cell_blk:
                cell_blk = next((all_blocks[ch_id] for ch_id in row_children if ch_id == cell_id), None)
            
            content = ""
            if cell_blk:
                content = (cell_blk.get('text') or {}).get('text', '')
                if not content:
                    # Maybe it's a mention or other mark
                    from .utils import format_inline_text
                    content = format_inline_text("", (cell_blk.get('text') or {}).get('marks', {}).get('marks', []), page_names)
            
            if not content:
                # Fallback to row details
                rel_key = (all_blocks.get(cid, {}).get('relation') or {}).get('key')
                if rel_key:
                    details = rblk.get('snapshot', {}).get('data', {}).get('details', {}) or {}
                    val = details.get(rel_key, "")
                    content = str(val) if val else ""

            row_cells.append(content.replace('\n', '<br>') if content else " ")
        
        if any(c.strip() for c in row_cells):
            rows_data.append(row_cells)

    if not rows_data:
        return ""

    # 4. Format Markdown
    # Ensure there's a blank line before the table for proper rendering
    markdown = "\n| " + " | ".join(columns) + " |\n"
    markdown += "| " + " | ".join(['----' for _ in columns]) + " |\n"
    for r in rows_data:
        # Pad cells with spaces
        padded_row = [f" {c} " if c.strip() else "      " for c in r]
        markdown += "|" + "|".join(padded_row) + "|\n"
    return markdown

def format_latex_equation(equation: str) -> str:
    return f"$${equation}$$"

def sanitize_filename(filename: str) -> str:
    return re.sub(r'[^\w\-_\. ]', '_', filename)