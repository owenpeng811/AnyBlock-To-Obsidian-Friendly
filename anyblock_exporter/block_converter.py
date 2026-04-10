import logging
from typing import Dict, Any, List
from anyblock_exporter.utils import format_inline_text, convert_table_to_markdown, format_latex_equation

LOGGER = logging.getLogger("anyblock_exporter")
 
def convert_dataview_to_markdown(dv_data: Dict[str, Any], relation_handler, page_names: Dict[str, str]) -> str:
    """Converts Anytype dataview (Sets/Collections) to Obsidian Dataview syntax."""
    if not dv_data or not dv_data.get('views'):
        return ""
    
    view = dv_data['views'][0]
    view_type = view.get('type', 'Table')
    
    # Map view type to Dataview syntax
    dv_type = "TABLE" if view_type == 'Table' else "LIST"
    
    def get_dv_field(name: str) -> str:
        """Heuristically escapes field names for Dataview."""
        if name == "file.name":
            return name
        if ' ' in name:
            return f'row["{name}"]'
        return name

    # Columns for Table
    columns = []
    if dv_type == "TABLE":
        for rel in view.get('relations', []):
            if rel.get('isVisible', False):
                rel_key = rel.get('key')
                if rel_key == 'name':
                    continue # Skip name as it's the default first column
                rel_name = relation_handler.resolve_name(rel_key) if relation_handler else rel_key
                if not rel_name or rel_name.strip() == "":
                    continue
                dv_field = get_dv_field(rel_name)
                if dv_field != rel_name:
                    columns.append(f'{dv_field} AS "{rel_name}"')
                else:
                    columns.append(dv_field)
    
    # Source (TargetObjectId)
    target_id = dv_data.get('TargetObjectId')
    from_clause = ""
    where_clauses = []
    
    if target_id:
        target_name = relation_handler.resolve_name(target_id) if relation_handler else target_id
        # "Object type" is common. Always use row[] for it since it has a space.
        object_type_field = get_dv_field("Object type")
        if target_name == "Page":
            where_clauses.append(f'{object_type_field} = [[{target_name}]]')
        else:
            if page_names and target_id in page_names:
                from_clause = f"[[{target_name}]]"
            else:
                where_clauses.append(f'{object_type_field} = [[{target_name}]]')

    # Filters
    filters = view.get('filters', [])
    for f in filters:
        rel_key = f.get('RelationKey')
        rel_name = relation_handler.resolve_name(rel_key) if relation_handler else rel_key
        dv_field = get_dv_field(rel_name)
        
        condition = f.get('condition')
        values = f.get('value', [])
        
        if not values:
            continue

        if rel_name.lower() == "backlinks" and condition == "In":
            link_vals = []
            for v in values:
                v_name = relation_handler.resolve_name(v) if relation_handler else v
                link_vals.append(f"outgoing([[{v_name}]])")
            if link_vals:
                joined_outgoing = " OR ".join(link_vals)
                if from_clause:
                    from_clause = f"({from_clause}) AND ({joined_outgoing})"
                else:
                    from_clause = joined_outgoing
        elif condition == "In":
            val_names = []
            for v in values:
                v_name = relation_handler.resolve_name(v) if relation_handler else v
                # Use link syntax for values
                val_names.append(f"[[{v_name}]]")
            if val_names:
                if len(val_names) == 1:
                    where_clauses.append(f"contains({dv_field}, {val_names[0]})")
                else:
                    clauses = " OR ".join([f"contains({dv_field}, {v})" for v in val_names])
                    where_clauses.append(f"({clauses})")

    # Sorts
    sort_clauses = []
    for s in view.get('sorts', []):
        rel_key = s.get('RelationKey')
        rel_name = "file.name" if rel_key == "name" else (relation_handler.resolve_name(rel_key) if relation_handler else rel_key)
        order = "ASC" if s.get('type') == 'Asc' else "DESC"
        dv_field = get_dv_field(rel_name)
        sort_clauses.append(f"{dv_field} {order}")

    # Build the final string
    query_lines = [f"```dataview\n{dv_type}"]
    if columns:
        query_lines[0] += " " + ", ".join(columns)
    
    if from_clause:
        query_lines.append(f"FROM {from_clause}")
    
    if where_clauses:
        query_lines.append(f"WHERE " + " AND ".join(where_clauses))
    
    if sort_clauses:
        query_lines.append(f"SORT " + ", ".join(sort_clauses))
    
    query_lines.append("```")
    return "\n".join(query_lines)

def is_organizational_block(block: Dict[str, Any]) -> bool:
    """Determine if a block is an organizational block."""
    if 'dataview' in block or 'file' in block:
        return False
    if any(k in block for k in ['table', 'tableColumn', 'tableRow']):
        if 'table' in block:
             return False
        return True
    layout_style = (block.get('layout') or {}).get('style', '')
    if layout_style in ['Div', 'TableColumns', 'TableRows', 'TableRowsContainer', 'TableColumn', 'TableRow']:
        return True
    if 'latex' in block:
        return False
    return not (block.get('text') or {}).get('text', '')

def has_unique_children(block: Dict[str, Any], all_blocks: Dict[str, Any], processed_blocks: set) -> bool:
    """Check if the block has any unprocessed children with different IDs."""
    for child_id in block.get('childrenIds', []):
        if child_id not in processed_blocks and child_id != block['id']:
            return True
    return False

def convert_block_to_markdown(block: Dict[str, Any], all_blocks: Dict[str, Any], parent_indent: str, is_top_level: bool, file_handler, processed_blocks: set, page_names: Dict[str, str] = None, list_level: int = 0, list_number: int = 1, relation_handler = None) -> str:
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
                    list_level=list_level, list_number=list_number,
                    relation_handler=relation_handler
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
    elif block.get('dataview'):
        dv_content = convert_dataview_to_markdown(block['dataview'], relation_handler, page_names)
        if dv_content:
            markdown += apply_indent(dv_content) + spacing
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
        if lang == 'clike':
            lang = 'c'
        # Code blocks usually want a bit of space even when nested
        markdown += apply_indent(f"```{lang}\n{content}\n```") + spacing
    elif block_type == 'Checkbox':
        text_data = block.get('text') or {}
        checked = '[x]' if text_data.get('checked', False) else '[ ]'
        markdown += apply_indent(f"- {checked} {content}") + "\n"
    elif block_type == 'Equation' or block.get('latex'):
        latex_text = (block.get('latex') or {}).get('text') or content
        if (block.get('latex') or {}).get('processor') == 'Mermaid':
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
                    file_handler, processed_blocks, page_names=page_names,
                    relation_handler=relation_handler
                )
    
    return markdown

def process_blocks(blocks: List[Dict[str, Any]], file_handler, page_names: Dict[str, str] = None, relation_handler = None) -> str:
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
                    processed_blocks, page_names=page_names, list_number=list_number,
                    relation_handler=relation_handler
                )
                if (child_block.get('text') or {}).get('style') == 'Numbered':
                    list_number += 1

    return markdown_content