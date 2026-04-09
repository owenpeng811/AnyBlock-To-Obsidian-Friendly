import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta
from .config_loader import config
from .utils import sanitize_filename

class RelationHandler:
    def __init__(self, json_objects: List[Dict[str, Any]]):
        self.json_objects = json_objects
        self.relation_cache = {}
        self.reference_date = datetime(2001, 1, 1)  # Reference date: January 1, 2001
        self.decode_timestamps = config.get('decode_timestamps', True)
        self.ignored_properties = config.get('ignored_properties', [])
        self.link_mode = config.get('turn_relations_into_obsidian_links', 'select')
        self.logger = logging.getLogger("anyblock_exporter")
        self.page_name_cache = {}
        for obj in self.json_objects:
            data = obj.get('snapshot', {}).get('data', {}) or {}
            details = data.get('details', {}) or {}
            
            # Try to get ID from various possible locations
            obj_id = details.get('id') or details.get('relationKey')
            if not obj_id:
                blocks = data.get('blocks', [])
                if blocks:
                    obj_id = blocks[0].get('id')
            
            # Get Name
            obj_name = details.get('name') or obj.get('name')
            
            if obj_id and obj_name:
                self.page_name_cache[obj_id] = obj_name

    def convert_timestamp_if_applicable(self, value: Any) -> Tuple[str, bool]:
        is_date = False
        if self.decode_timestamps and isinstance(value, (int, float)) and len(str(int(value))) == 10:
            try:
                days_since_reference = int(value) // 86400
                date = self.reference_date + timedelta(days=days_since_reference)
                adjusted_date = date.replace(year=date.year - 31) - timedelta(days=1)
                is_date = True
                return adjusted_date.strftime("%Y-%m-%d"), is_date
            except Exception as e:
                self.logger.warning(f"Failed to convert timestamp {value}: {str(e)}")
        # Try to resolve Page ID to name first
        if value in self.page_name_cache and self.page_name_cache[value]:
            return sanitize_filename(self.page_name_cache[value]), is_date
            
        return self.get_relation_option_name(value), is_date

    def extract_relations(self, main_content: Dict[str, Any]) -> List[str]:
        relations = {}
        data = main_content.get('snapshot', {}).get('data', {}) or {}
        details = data.get('details', {}) or {}
        relation_links = data.get('relationLinks', []) or []

        for relation_link in relation_links:
            key = relation_link['key']
            if key in self.ignored_properties:
                continue  # Skip ignored relations

            value = details.get(key)
            relation_info = self.get_relation_info(key)
            relation_name = relation_info.get('name', key)

            if value is not None:
                if isinstance(value, list):
                    relations[relation_name] = [self.format_relation_value(item, key) for item in value]
                elif isinstance(value, bool):
                    relations[relation_name] = ['Yes' if value else 'No']
                else:
                    relations[relation_name] = [self.format_relation_value(value, key)]

        # Format relations
        formatted_relations = []
        for relation_name, values in relations.items():
            if len(values) == 1:
                formatted_relations.append(f"{relation_name}: {values[0]}")
            else:
                formatted_relations.append(f"{relation_name}:")
                formatted_relations.extend(f" - {value}" for value in values)

        self.logger.debug(f"Extracted relations: {formatted_relations}")
        return formatted_relations

    def format_relation_value(self, value: Any, key: str) -> str:
        converted_value, is_date = self.convert_timestamp_if_applicable(value)
        
        if is_date:
            return converted_value  # Return date without wrapping in links
        
        if self.link_mode == 'all':
            return f'"[[{converted_value}]]"'
        elif self.link_mode == 'select' and self.relation_has_options(key):
            return f'"[[{converted_value}]]"'
        else:
            return converted_value

    def relation_has_options(self, relation_key: str) -> bool:
        """Checks if a relation has pre-defined options."""
        for obj in self.json_objects:
            data = obj.get('snapshot', {}).get('data', {}) or {}
            details = data.get('details', {}) or {}
            if obj.get('sbType') == 'STRelation' and details.get('relationKey') == relation_key:
                # Check if relationFormat is 0, indicating free-form text
                if details.get('relationFormat') == 0:
                    return False
                else:
                    return True
        return False  # Relation not found or format not specified

    def get_relation_info(self, relation_key: str) -> Dict[str, Any]:
        if relation_key in self.relation_cache:
            return self.relation_cache[relation_key]

        for obj in self.json_objects:
            data = obj.get('snapshot', {}).get('data', {}) or {}
            details = data.get('details', {}) or {}
            if obj.get('sbType') == 'STRelation' and details.get('relationKey') == relation_key:
                self.relation_cache[relation_key] = details
                return self.relation_cache[relation_key]

        self.logger.warning(f"Relation info not found for key: {relation_key}")
        return {}

    def get_relation_option_name(self, option_id: str) -> str:
        """Retrieves the name of a relation option given its ID."""
        for obj in self.json_objects:
            data = obj.get('snapshot', {}).get('data', {}) or {}
            details = data.get('details', {}) or {}
            if obj.get('sbType') == 'STRelationOption' and details.get('id') == option_id:
                return details.get('name', option_id)
        return str(option_id)  # Return the ID as a string if the name is not found

    def resolve_name(self, obj_id: str) -> str:
        """Generic name resolver for pages, relations, types, etc."""
        if not obj_id:
            return ""
        # 1. Check page/object names
        if obj_id in self.page_name_cache:
            return self.page_name_cache[obj_id]
        
        # 2. Check relations
        rel_info = self.get_relation_info(obj_id)
        if rel_info and rel_info.get('name'):
            return rel_info['name']
            
        # 3. Check types
        for obj in self.json_objects:
            if obj.get('sbType') == 'STType':
                data = obj.get('snapshot', {}).get('data', {}) or {}
                details = data.get('details', {}) or {}
                if details.get('id') == obj_id:
                    return details.get('name', obj_id)
        
        # 4. Check relation options
        return self.get_relation_option_name(obj_id)