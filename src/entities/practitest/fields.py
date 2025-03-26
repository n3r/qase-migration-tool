import asyncio
import json

from ...service import QaseService, PractitestService
from ...support import Logger, Mappings, ConfigManager as Config, Pools

from qaseio.models import CustomFieldCreateValueInner

from pprint import pprint
import copy
class Fields:
    def __init__(
            self, 
            qase_service: QaseService,
            source_service: PractitestService,
            logger: Logger,
            mappings: Mappings,
            config: Config,
            pools: Pools,
    ):
        self.qase = qase_service
        self.practitest = source_service
        self.logger = logger
        self.mappings = mappings
        self.config = config
        self.pools = pools

        self.refs_id = None
        self.system_fields = []

        self.map = {}
        self.logger.divider()
        self.fields_map = {}
        self.parent_map = {}

    def import_fields(self):
        return asyncio.run(self.import_fields_async())
    
    async def import_fields_async(self):
        self.logger.log('[Fields] Loading system fields from Qase')
        qase_system_fields = await self.pools.qs(self.qase.get_system_fields)
        for field in qase_system_fields:
            self.system_fields.append(field.to_dict())

        for project in self.mappings.projects:
            self.logger.log('[Fields] Loading custom fields from PractiTest')
            fields = self._flatten_children(await self.pools.source(self.practitest.get_custom_fields, project['practitest_id']))
            self._build_fields_map(project)
            for id in fields:
                field = fields[id]
                if field['type'] == 'custom-fields':
                    for entity_id in self.fields_map[int(field['id'])]:
                        self._create_custom_field(field, project, entity_id)
        return self.mappings
    
    def _build_fields_map(self, project: dict):
        # 0 - case, 1 - run, 2 - defect,
        self.fields_map = {}
        practitest_project_fields = self.practitest.get_project_fields(project['practitest_id'])
        for field in practitest_project_fields:
            if field['type'] == 'CustomField':
                self.fields_map[field['id']] = []
                if 'Test' in field['entities']:
                    self.fields_map[field['id']].append(0)
                if 'TestSet' in field['entities']:
                    self.fields_map[field['id']].append(1)
                if 'Issue' in field['entities']:
                    self.fields_map[field['id']].append(2)

            if field['name'] == 'Status' and field['type'] == 'SystemField' and 'Test' in field['entities']:
                self._add_status_field(field)
        self.mappings.custom_fields_parent_map = self.parent_map

    def _add_status_field(self, field: dict):
        statuses_to_add = []
        for status in field['possible_values']:
            if status not in self.mappings.case_statuses.keys():
                statuses_to_add.append(status)

        if statuses_to_add:
            qase_statuses = []
            for field in self.system_fields:
                if field['slug'] == 'status':
                    for option in field['options']:
                        qase_statuses.append(option)

            for status in statuses_to_add:
                self.mappings.case_statuses[status] = 1
                for qase_status in qase_statuses:
                    if status.lower() == qase_status['title'].lower():
                        self.mappings.case_statuses[status] = qase_status['id']

    def _flatten_children(self, fields: list):
        result = {}
        for field in fields['data']:
            field['attributes']['id'] = field['id']
            field['attributes']['type'] = field['type']
            result[field['id']] = field['attributes']

        for key in result:
            if result[key]['parent-list-id'] is not None:
                result[str(result[key]['parent-list-id'])]['child'] = result[key]
                self.parent_map[int(result[key]['parent-list-id'])] = int(key)
        
        keys_to_delete = []
        for key in result:
            if result[key]['parent-list-id'] is not None:
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del result[key]

        for key in result:
            if 'child' in result[key] and result[key]['child'] is not None:
                result[key]['possible-values'] = self.flatten_cf(result[key])
                del result[key]['child']

        return result

    def _create_custom_field(self, field: dict, project: dict, entity_id: int):
        try:
            data = self._prepare_custom_field_data(field, project, entity_id)
            qase_id = self.qase.create_custom_field(data)
            if qase_id > 0:
                self.logger.log('[Fields] Custom field created: ' + field['name'])
                if entity_id == 0:
                    self.mappings.case_custom_fields[int(field['id'])] = copy.deepcopy(field)
                    self.mappings.case_custom_fields[int(field['id'])]['qase_id'] = qase_id
                elif entity_id == 1:
                    self.mappings.run_custom_fields[int(field['id'])] = copy.deepcopy(field)
                    self.mappings.run_custom_fields[int(field['id'])]['qase_id'] = qase_id
                elif entity_id == 2:
                    self.mappings.defect_custom_fields[int(field['id'])] = copy.deepcopy(field)
                    self.mappings.defect_custom_fields[int(field['id'])]['qase_id'] = qase_id
                self.mappings.stats.add_custom_field('qase')
        except Exception as e:
            self.logger.log(f'[Fields] Error creating custom field {field}: {e}')

    def _prepare_custom_field_data(self, field: dict, project: dict, entity_id: int) -> dict:
        data = {
            'title': field['name'],
            'entity': entity_id,
            'type': self.mappings.practitest_fields_type[field['field-format']],
            'value': [],
            'is_filterable': True,
            'is_visible': True,
            'is_required': False,
            'projects_codes': [project['code']],
            'is_enabled_for_all_projects': False
        }

        if field['field-format'] in ('multilist', 'list', 'linkedlist'):
            field['qase_values'] = {}
            if len(field['possible-values']) > 0:
                i = 1
                for value in field['possible-values']:
                    data['value'].append(
                        CustomFieldCreateValueInner(
                            id=i,  
                            title=value,
                        ),
                    )
                    field['qase_values'][i] = value
                    i += 1
            else:
                self.logger.log('Error creating custom field: ' + field['name'] + '. No options found', 'warning')
        return data
    
    def flatten_cf(self, cf):
        """
        Given a PractiTest CF-like dict with possible-values (which can be
        either a list or dict) and an optional 'child' containing more nested
        possible-values, flatten them into a list of strings joined by " - ".
        """
        # Start with all top-level paths (lists-of-strings). Then convert
        # them to joined strings at the very end.
        all_paths = self._collect_paths(cf)
        return [" - ".join(path) for path in all_paths]


    def _collect_paths(self, cf, prefix=None):
        """
        Returns a list of all possible 'paths' (as lists-of-strings)
        from the given CF node.
        """
        if prefix is None:
            prefix = []
        results = []

        # The 'possible-values' can be a list or a dict
        possible_values = cf.get("possible-values", [])
        child = cf.get("child")  # could be None or another CF dict

        if isinstance(possible_values, list):
            # Top-level or any level that just has a list
            for val in possible_values:
                new_prefix = prefix + [val]

                # If there is a child with dict-based possible-values, we match by lowercasing
                if child and isinstance(child.get("possible-values"), dict):
                    child_dict = child["possible-values"]
                    key = val.lower()
                    if key in child_dict:
                        subitems = child_dict[key]
                        if subitems:
                            # For each sub-item in the child, descend further
                            for subitem in subitems:
                                results.extend(self._descend(child, new_prefix, subitem))
                        else:
                            # No subitems -> this path is complete
                            results.append(new_prefix)
                    else:
                        # No matching key in child dict -> just this level
                        results.append(new_prefix)
                else:
                    # No child or child's possible-values is not a dict
                    results.append(new_prefix)

        elif isinstance(possible_values, dict):
            # A "linkedlist" CF: keys are the possible-values, each maps to a list
            for key, sublist in possible_values.items():
                new_prefix = prefix + [key]
                if sublist:
                    for subitem in sublist:
                        results.extend(self._descend(cf, new_prefix, subitem))
                else:
                    # No subitems for this key
                    results.append(new_prefix)

        return results


    def _descend(self, cf, prefix, item):
        """
        Descend one level deeper from a dictionary-based possible-values node.
        'prefix' is what we have so far; 'item' is the sub-value we're adding.
        """
        new_prefix = prefix + [item]
        results = []

        child = cf.get("child")
        # If there's another nested child with dict-based possible-values, we keep going
        if child and isinstance(child.get("possible-values"), dict):
            sub_dict = child["possible-values"]
            item_lower = item.lower()
            if item_lower in sub_dict:
                subitems = sub_dict[item_lower]
                if subitems:
                    for s in subitems:
                        results.extend(self._descend(child, new_prefix, s))
                else:
                    # Reached the bottom under this branch
                    results.append(new_prefix)
            else:
                # No matching key in nested dictionary
                results.append(new_prefix)
        else:
            # No further child to descend into
            results.append(new_prefix)

        return results


class UnsupportedCustomField(Exception):
    def __init__(self, field: dict):
        self.field = field
        self.message = f'Unsupported custom field: {field["attributes"]["name"]}'
        super().__init__(self.message)
