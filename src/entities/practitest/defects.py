from ...service import QaseService, PractitestService
from ...support import Logger, Mappings, ConfigManager as Config, Pools
import asyncio
import re
from typing import Optional, Union, List
import json
import ast

from .attachments import Attachments
class Defects:
    def __init__(self, qase_service: QaseService, source_service: PractitestService, logger: Logger, mappings: Mappings, config: Config, pools: Pools) -> Mappings:
        self.qase = qase_service
        self.practitest = source_service
        self.logger = logger
        self.mappings = mappings
        self.pools = pools
        self.config = config
        self.index = []
        self.map = {}
        self.logger.divider()
        self.attachments = Attachments(self.qase, self.practitest, self.logger, self.mappings, self.config, self.pools)
        self.i = 0

    def import_defects(self, project) -> Mappings:
        self.project = project
        return asyncio.run(self.import_defects_async())
    
    async def import_defects_async(self) -> Mappings:
        self.logger.log(f'[{self.project["code"]}][Defects] Importing defects from PractiTest project {self.project["name"]}')
        await self._build_index()
        self.logger.log(f'[{self.project["code"]}][Defects] Found {str(len(self.index))} defects')
        i = 0
        async with asyncio.TaskGroup() as tg:
            for defect in self.index:
                i += 1
                self.logger.print_status(f'[{self.project["code"]}] Importing defects', i, len(self.index), 1)
                tg.create_task(self._import_defect(defect))
        return

    async def _build_index(self) -> None:
        self.logger.log(f'[{self.project["code"]}][Defects] Building index for project {self.project["name"]}')
        
        limit = 100
        page = 1

        while True:
            defects = await self.pools.source(self.practitest.get_defects, self.project['practitest_id'], limit, page)

            if 'data' in defects and defects['data'] is not None:
                defects = defects['data']

            self.index = self.index + defects

            if len(defects) < limit:
                break
            page += 1
        
        return

    async def _import_defect(self, defect) -> None:
        self.logger.log(f'[{self.project["code"]}][Defects] Importing defect {defect["id"]} from PractiTest project {self.project["name"]}')
        try:
            data = {
                'title': defect['attributes']['title'],
                'description': str(defect['attributes']['description']) if defect['attributes']['description'] else '',
                'custom_field': {},
                'attachments': [],
                'author_id': self.mappings.get_user_id(int(defect['attributes']['author-id'])),
                'status': 0,
            }
            
            if defect['attributes']['closed-at']:
                data['status'] = 2

            data = self._get_attachments_for_defect(defect['id'], data)
            data = self._import_custom_fields_for_defects(defect=defect, data=data)

            self.qase.create_defect(self.project['code'], data)
            self.logger.log(f'[{self.project["code"]}][Defects] Imported defect {defect["id"]} from PractiTest project {self.project["name"]}')
        except Exception as e:
            self.logger.log(f'[{self.project["code"]}][Defects] Failed to import defect {defect["id"]} from PractiTest project {self.project["name"]}: {e}')
        return
    
    def _import_custom_fields_for_defects(self, defect: dict, data: dict) -> dict:
        fields = {}
        for field_name in defect['attributes']['custom-fields']:
            if field_name and field_name != 'null':
                search = re.search(r'\d+', field_name)
                if search:
                    id = int(search[0])
                    value = defect['attributes']['custom-fields'][field_name]
                    if type(value) == str:
                        value = self.to_list_if_possible(value)
                    fields[id] = value
        try:
            fields = self._transform_chains(self.mappings.custom_fields_parent_map, fields)
        except Exception as e:
            self.logger.log(f'[{self.project["code"]}][Defects] Failed to transform chains: {e}', 'error')

        for field_id in fields:
            if field_id in self.mappings.defect_custom_fields:
                custom_field = self.mappings.defect_custom_fields[field_id]
                if custom_field['field-format'] in ('multilist', 'list'):
                    value = self._validate_custom_field_values(custom_field, fields[field_id])
                    if value:
                        if type(value) == str or type(value) == int:
                            data['custom_field'][str(custom_field['qase_id'])] = str(self._get_value(custom_field['qase_values'], value))
                        if type(value) == list:
                            data['custom_field'][str(custom_field['qase_id'])] = ','.join(str(self._get_value(custom_field['qase_values'], v)) for v in value)
                elif custom_field['field-format'] == 'user':
                    value = str(self.mappings.get_user_id(int(fields[field_id])))
                    data['custom_field'][str(custom_field['qase_id'])] = value
                elif custom_field['field-format'] == 'checkbox':
                    if fields[field_id] == 'yes':
                        data['custom_field'][str(custom_field['qase_id'])] = "true"
                else:
                    data['custom_field'][str(custom_field['qase_id'])] = fields[field_id]
        return data
    
    def _transform_chains(self, parent_child, fields):
        # Collect all child IDs in a set
        children = set(parent_child.values())
        
        # Top-level keys = any key in names that is NOT a child.
        # (This includes keys that are never used as parents or children.)
        top_level_keys = set(fields.keys()) - children
        
        result = {}
        
        # Helper function: follow the chain from a given starting key
        def follow_chain(start):
            chain_vals = []
            current = start
            while True:
                chain_vals.append(fields[current])
                if current in parent_child:
                    # Go to the child
                    current = parent_child[current]
                else:
                    # No child -> end of chain
                    break
            return " - ".join(chain_vals)
        
        # Build the result for each top-level key
        for key in top_level_keys:
            if key in parent_child:
                # If this key is a parent, follow its chain
                result[key] = follow_chain(key)
            else:
                # Otherwise, it's just a standalone
                result[key] = fields[key]
                
        return result
    
    # Done. Method validates if custom field value exists (skip)
    def _validate_custom_field_values(self, custom_field: dict, value: Union[str, int, List]) -> Optional[Union[str, list]]:
        value = self._normalize_value(value)
        if len(custom_field['possible-values']) > 0:
            values = custom_field['possible-values']
            if type(value) == str or type(value) == int:
                if str(value) not in values:
                    self.logger.log(f'[{self.project["code"]}][Defects] Custom field {custom_field["name"]} has invalid value {value}', 'warning')
                    return None
            elif type(value) == list:
                filtered_values = []
                for item in value:
                    if str(item) in values:
                        filtered_values.append(item)
                    else:
                        self.logger.log(f'[{self.project["code"]}][Defects] Custom field {custom_field["name"]} has invalid value {value}', 'warning')
                if len(filtered_values) == 0:
                    return None
                else:
                    return filtered_values
            return value
        return None
    
    def to_list_if_possible(self, s):
        """
        Convert a string that looks like ['2.0', '1.6'] etc. into a Python list.
        If it isn't a valid bracketed Python list, return the string as-is.
        """
        s = s.strip()
        if s.startswith("[") and s.endswith("]"):
            try:
                val = ast.literal_eval(s)  # Safely parse the Python literal
                if isinstance(val, list):
                    return val
            except (ValueError, SyntaxError):
                pass
        return s
    
    def _get_attachments_for_defect(self, issue_id: dict, data: dict) -> dict:
        try:
            attachments = self.attachments.import_attachments_for_entity(code = self.project['code'], project_id=self.project['practitest_id'], entity_type='issue', entity_id=int(issue_id))
            if attachments:
                for attachment in attachments['data']:
                    id = int(attachment['id'])
                    if id in self.mappings.attachments_map:
                        data['attachments'].append(self.mappings.attachments_map[id]['hash'])
        except Exception as e:
            self.logger.log(f'[{self.project["code"]}][Defects] Failed to get attachments for defect {issue_id}: {e}', 'error')
        return data
    
    def _normalize_value(self, value: Union[str, int, List]) -> Union[str, int, List]:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
        return value
    
    def _get_value(self, qase_values, value):
        try:
            for key, val in qase_values.items():
                if val == value:
                    return key
            return None  # Return None if value not found
        except Exception as e:
            self.logger.log(f'[{self.project["code"]}][Defects] Failed to get value for custom field {qase_values}: {e}', 'error')
            return None