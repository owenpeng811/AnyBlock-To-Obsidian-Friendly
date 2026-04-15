import logging
from typing import Dict, Any, List
from anyblock_exporter.utils import format_inline_text, convert_table_to_markdown, format_latex_equation

LOGGER = logging.getLogger("anyblock_exporter")

def is_organizational_block(block: Dict[str, Any]) -> bool:
    """Determine if a block is an organizational block."""
    return block.get('layout', {}).get('style') == 'Div' or not block.get('text', {}).get('text', '')

def has_unique_children(block: Dict[str, Any], all_blocks: Dict[str, Any], processed_blocks: set) -> bool:
    """Check if the block has any unprocessed children with different IDs."""
    for child_id in block.get('childrenIds', []):
        if child_id not in processed_blocks and child_id != block['id']:
            return True
    return False

def convert_block_to_markdown(block: Dict[str, Any], all_blocks: Dict[str, Any], parent_indent: str, is_top_level: bool, file_handler, processed_blocks: set, page_names: Dict[str, str] = None, list_level: int = 0, list_number: int = 1) -> str:
    if block is None or block.get('id') is None:
        return ""

    block_id = block['id']
    if block_id in processed_blocks:
        return ""
    processed_blocks.add(block_id)

    if is_organizational_block(block):
        markdown = ""
        for child_id in block.get('childrenIds', []):
            child_block = all_blocks.get(child_id)
            if child_block:
                markdown += convert_block_to_markdown(
                    child_block, all_blocks, parent_indent, is_top_level,
                    file_handler, processed_blocks, page_names=page_names,
                    list_level=list_level, list_number=list_number
                )
        return markdown

    # Initial indentation
    current_indent = "" if is_top_level else parent_indent + "    "

    text_field = block.get('text') or {}
    block_type = text_field.get('style', 'Paragraph')
    content = text_field.get('text', '')
    marks = (text_field.get('marks') or {}).get('marks', [])
    content = format_inline_text(content, marks, page_names=page_names) if content else ""

    def apply_indent(text: str) -> str:
        lines = text.split('\n')
        if not current_indent:
            return text
        return '\n'.join([f"{current_indent}{line}" for line in lines])

    markdown = ""
    spacing = "\n\n" if is_top_level else "\n"

    if block.get('file'):
        attachment = file_handler.handle_file_attachment(block['file'])
        markdown += apply_indent(attachment) + spacing
    elif block_type == 'Table' or any(k in block for k in ['table', 'tableColumn', 'tableRow']):
        table = convert_table_to_markdown(block, all_blocks, page_names)
        if table:
            markdown += apply_indent(table) + "\n\n"
        elif content:
            markdown += apply_indent(content) + spacing
    elif block_type.startswith('Header'):
        level = block_type[-1]
        markdown += f"{current_indent}{'#' * int(level)} {content}\n\n"
    elif block_type == 'Numbered':
        indent = "    " * list_level
        prefix = f"{indent}{list_number}. "
        markdown += f"{prefix}{content}\n"
    elif block_type == 'Toggle':
        markdown += apply_indent(f"- {content}") + "\n" if content else "- \n"
    elif block_type == 'Marked':
        markdown += apply_indent(f"- {content}") + "\n"
    elif block_type == 'Code':
        fields = block.get('fields') or {}
        lang = fields.get('lang', '')
        code_block = f"\n```{lang}\n{content}\n```\n"
        markdown += apply_indent(code_block) + spacing
    elif block_type == 'Checkbox':
        text_data = block.get('text') or {}
        checked = '[x]' if text_data.get('checked', False) else '[ ]'
        markdown += apply_indent(f"- {checked} {content}") + "\n"
    elif block.get('latex'):
        latex_text = block['latex'].get('text', '')
        if block['latex'].get('processor') == 'Mermaid':
            markdown += apply_indent(f"```mermaid\n{latex_text}\n```") + spacing
        else:
            markdown += apply_indent(format_latex_equation(latex_text)) + spacing
    elif block_type == 'Paragraph':
        markdown += apply_indent(content) + spacing if content else ""
    else:
        LOGGER.warning(f"Unknown block type: {block_type}")
        markdown += apply_indent(content) + spacing

    if has_unique_children(block, all_blocks, processed_blocks):
        for i, child_id in enumerate(block.get('childrenIds', [])):
            child_block = all_blocks.get(child_id)
            if not child_block or child_id in processed_blocks:
                continue
                
            if block_type == 'Numbered':
                markdown += convert_block_to_markdown(
                    child_block, all_blocks, current_indent, False,
                    file_handler, processed_blocks, page_names=page_names,
                    list_level=list_level + 1, list_number=i + 1
                )
            else:
                markdown += convert_block_to_markdown(
                    child_block, all_blocks, current_indent, False,
                    file_handler, processed_blocks, page_names=page_names
                )
    
    return markdown

def process_blocks(blocks: List[Dict[str, Any]], file_handler, page_names: Dict[str, str] = None) -> str:
    all_blocks = {block['id']: block for block in blocks if block.get('id')}
    processed_blocks = set()
    markdown_content = ""
    
    root_block = blocks[0] if blocks else None
    if root_block:
        list_number = 1
        for child_id in root_block.get('childrenIds', []):
            child_block = all_blocks.get(child_id)
            if child_block and child_id not in processed_blocks:
                markdown_content += convert_block_to_markdown(
                    child_block, all_blocks, "", True, file_handler,
                    processed_blocks, page_names=page_names, list_number=list_number
                )
                if (child_block.get('text') or {}).get('style') == 'Numbered':
                    list_number += 1

    return markdown_content