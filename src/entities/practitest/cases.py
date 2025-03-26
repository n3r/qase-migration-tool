import asyncio

from ...service import QaseService, PractitestService
from ...support import Logger, Mappings, ConfigManager as Config, Pools

from .attachments import Attachments

from typing import List, Optional, Union
import json
import ast

from qaseio.models import TestStepCreate, TestCasebulkCasesInner
import re

class Cases:
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
        self.config = config
        self.logger = logger
        self.mappings = mappings
        self.pools = pools
        self.attachments = Attachments(self.qase, self.practitest, self.logger, self.mappings, self.config, self.pools)
        self.total = 0
        self.logger.divider()

        self.project = None
        self.steps = {}

    def import_cases(self, project: dict):
        return asyncio.run(self.import_cases_async(project))

    async def import_cases_async(self, project: dict):
        self.project = project

        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.import_all_steps())

        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.import_all_cases())

    async def import_all_steps(self):
        page = 1
        limit = 100
        while True:
            count = await self.process_steps(limit, page)
            if count < limit:
                break
            page += 1

    async def import_all_cases(self):
        page = 1
        limit = 100
        while True:
            count = await self.process_cases(limit, page)
            if count < limit:
                break
            page += 1
        

    async def process_steps(self, limit: int = 100, page: int = 1) -> int:
        try:
            res = await self.pools.source(self.practitest.get_steps, self.project['practitest_id'], limit, page)
            steps = res['data']
            if steps and len(steps) > 0:
                for step in steps:
                    if step['attributes']['test-id'] not in self.steps:
                        self.steps[step['attributes']['test-id']] = []
                    step['attributes']['id'] = step['id']
                    self.steps[step['attributes']['test-id']].append(step['attributes'])
            return len(steps)
        except Exception as e:
            self.logger.log(f"[{self.project['code']}][Tests] Error processing steps: {e}", 'error')
            return 0

    async def process_cases(self, limit: int = 100, page: int = 1) -> int:
        try:
            res = await self.pools.source(self.practitest.get_cases, self.project['practitest_id'], limit, page)
            cases = res['data']
            self.mappings.stats.add_entity_count(self.project['code'], 'cases', 'practitest', len(cases))
            if cases and len(cases) > 0:
                self.logger.print_status('['+self.project['code']+'] Importing test cases', self.total, self.total+len(cases), 1)
                self.logger.log(f'[{self.project["code"]}][Tests] Importing {len(cases)}')
                data = await self._prepare_cases(cases)
                if data:
                    status = await self.pools.qs(self.qase.create_cases, self.project['code'], data)
                    if status:
                        self.mappings.stats.add_entity_count(self.project['code'], 'cases', 'qase', len(cases))
                self.total = self.total + len(cases)
                self.logger.print_status('['+self.project['code']+'] Importing test cases', self.total, self.total, 1)
            return len(cases)
        except Exception as e:
            self.logger.log(f"[{self.project['code']}][Tests] Error processing cases: {e}", 'error')
            return 0
        
    async def _prepare_cases(self, cases: List) -> List:
        results = []
        for case in cases:
            results.append(self._prepare_case(case))

        return results

    def _prepare_case(self, case):
        data = {
            'id': int(case['attributes']['display-id']),
            'title': case['attributes']['name'],
            'created_at': case['attributes']['created-at'],
            'updated_at': case['attributes']['updated-at'],
            'author_id': self.mappings.get_user_id(int(case['attributes']['author-id'])),
            'description': self.attachments.find_and_replace_attachments(case['attributes']['description'], self.project['code']),
            'preconditions': self.attachments.find_and_replace_attachments(case['attributes']['preconditions'], self.project['code']),
            'steps': [],
            'attachments': [],
            'is_flaky': 0,
            'custom_field': {},
            'suite_id': None
        }

        # import custom fields
        data = self._import_custom_fields_for_case(case=case, data=data)
        data = self._get_attachments_for_case(case=case, data=data)

        data = self._set_steps(case=case, data=data)

        #data = self._set_priority(case=case, data=data)
        #data = self._set_type(case=case, data=data)
        data = self._set_status(case=case, data=data)

        return TestCasebulkCasesInner(
                **data
            )
    
    def _get_attachments_for_case(self, case: dict, data: dict) -> dict:
        try:
            attachments = self.attachments.import_attachments_for_entity(code = self.project['code'], project_id=self.project['practitest_id'], entity_type='test', entity_id=int(case['id']))
            if attachments:
                for attachment in attachments['data']:
                    id = int(attachment['id'])
                    if id in self.mappings.attachments_map:
                        data['attachments'].append(self.mappings.attachments_map[id]['hash'])
        except Exception as e:
            self.logger.log(f'[{self.project["code"]}][Tests] Failed to get attachments for case {case['attributes']['name']}: {e}', 'error')
        return data
    
    def _get_attachments_for_steps(self, step_id: int) -> dict:
        res = []
        try:
            attachments = self.attachments.import_attachments_for_entity(code = self.project['code'], project_id=self.project['practitest_id'], entity_type='step', entity_id=int(step_id))
            if attachments:
                for attachment in attachments['data']:
                    id = int(attachment['id'])
                    if id in self.mappings.attachments_map:
                        res.append(self.mappings.attachments_map[id]['hash'])
        except Exception as e:
            self.logger.log(f'[{self.project["code"]}][Tests] Failed to get attachments for step in case: {e}', 'error')
        return res
    
    def _set_steps(self, case, data):
        steps = []
        if int(case['id']) and int(case['id']) in self.steps:
            steps = self.steps[int(case['id'])]
        if steps and len(steps) > 0:
            for step in steps:
                name = (step['name'] or '').strip()
                if name != '':
                    name = name + '\n'
                action = name + (step['description'] or '').strip()
                expected = (step['expected-results'] or '').strip()
                
                if (action == ''):
                    action = 'No action'

                attachments = self._get_attachments_for_steps(step['id'])

                action = self.attachments.find_and_replace_attachments(action, self.project['code'])
                expected = self.attachments.find_and_replace_attachments(expected, self.project['code'])

                data['steps'].append(
                    TestStepCreate(
                        action=action,
                        expected_result=expected,
                        position=step['position'],
                        attachments=attachments
                    )
                )
        return data
    
    # Done
    def _import_custom_fields_for_case(self, case: dict, data: dict) -> dict:
        fields = {}
        for field_name in case['attributes']['custom-fields']:
            if field_name and field_name != 'null':
                search = re.search(r'\d+', field_name)
                if search:
                    id = int(search[0])
                    value = case['attributes']['custom-fields'][field_name]
                    if type(value) == str:
                        value = self.to_list_if_possible(value)
                    fields[id] = value
        try:
            fields = self._transform_chains(self.mappings.custom_fields_parent_map, fields)
        except Exception as e:
            self.logger.log(f'[{self.project["code"]}][Tests] Failed to transform chains: {e}', 'error')

        for field_id in fields:
            if field_id in self.mappings.case_custom_fields:
                custom_field = self.mappings.case_custom_fields[field_id]
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
                    self.logger.log(f'[{self.project["code"]}][Tests] Custom field {custom_field["name"]} has invalid value {value}', 'warning')
                    return None
            elif type(value) == list:
                filtered_values = []
                for item in value:
                    if str(item) in values:
                        filtered_values.append(item)
                    else:
                        self.logger.log(f'[{self.project["code"]}][Tests] Custom field {custom_field["name"]} has invalid value {value}', 'warning')
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
            self.logger.log(f'[{self.project["code"]}][Tests] Failed to get value for custom field {qase_values}: {e}', 'error')
            return None
    
    def _set_priority(self, case: dict, data: dict) -> dict:
        data['priority'] = self.mappings.priorities[case['priority_id']] if case['priority_id'] in self.mappings.priorities else 1
        return data
    
    def _set_type(self, case: dict, data: dict) -> dict:
        data['type'] = self.mappings.types[case['type_id']] if case['type_id'] in self.mappings.types else 1
        return data
    
    def _set_status(self, case: dict, data: dict) -> dict:
        data['status'] = self.mappings.case_statuses[case['attributes']['status']] if case['attributes']['status'] in self.mappings.case_statuses.keys() else 1
        return data