import asyncio
from datetime import datetime, timezone

from ...service import QaseService, PractitestService
from ...support import Logger, Mappings, ConfigManager as Config, Pools
from .attachments import Attachments

import re
from typing import Optional, Union, List
import json
import ast

class Runs:
    def __init__(
            self,
            qase_service: QaseService,
            source_service: PractitestService,
            logger: Logger,
            mappings: Mappings, config: Config,
            project: list,
            pools: Pools,
    ):
        self.qase = qase_service
        self.practitest = source_service
        self.config = config
        self.logger = logger
        self.mappings = mappings
        self.project = project
        self.pools = pools

        self.limit = 10

        self.attachments = Attachments(self.qase, self.practitest, self.logger, self.mappings, self.config, self.pools)

        self.created_after = self.config.get('runs.created_after')
        self.logger.divider()

        self.run_index = {}
        self.run_case_index = {}
        self.run_result_index = {}
        self.run_steps_index = {}

    def import_runs(self) -> None:
        return asyncio.run(self.import_runs_async())

    async def import_runs_async(self) -> None:
        self.logger.log(f'[{self.project["code"]}][Runs] Importing runs from PractiTest project {self.project["name"]}')

        self._build_run_index()
        self._build_run_case_index()
        self._build_run_steps_index()
        self._build_run_result_index()

        self.logger.log(f'[{self.project["code"]}][Runs] Found {str(len(self.run_index))} runs (test sets)')
        self.run_index = dict(sorted(self.run_index.items(), key=lambda item: item[1]['created_on']))
        i = 0
        async with asyncio.TaskGroup() as tg:
            for key, run in self.run_index.items():
                i += 1
                self.logger.print_status(f'[{self.project["code"]}] Importing runs', i, len(self.run_index), 1)
                tg.create_task(self._import_run(run))

    def _build_run_index(self) -> None:
        self.logger.log(f'[{self.project["code"]}][Runs] Building run index for project {self.project["name"]}')
        limit = self.limit
        page = 1

        while True:
            try:    
                sets = self.practitest.get_test_sets(self.project['practitest_id'], limit, page)
                self.logger.log(f'[{self.project["code"]}][Runs] Found {str(len(sets["data"]))} runs in Practitest')
                for testset in sets['data']:
                    try: 
                        dt = datetime.fromisoformat(testset['attributes']['created-at'])

                        if testset['attributes']['author-id']:
                            author_id = int(testset['attributes']['author-id'])
                        else:
                            author_id = 1

                        data = {
                            'id': int(testset['attributes']['display-id']),
                            'name': testset['attributes']['name'],
                            'description': testset['attributes']['description'],
                            'created_on': int(dt.timestamp()),
                            'is_completed': False,
                            'author_id': self.mappings.get_user_id(author_id),
                            'cases': [],
                            'custom_field': {}
                        }
                        data = self._import_custom_fields_for_run(run=testset, data=data)
                        
                        self.run_index[testset['attributes']['display-id']] = data
                    except Exception as e:
                        self.logger.log(f'[{self.project["code"]}][Runs] Failed to add test set to index: {str(e)}', 'error')

                if len(sets['data']) < limit:
                    break

            except Exception as e:
                self.logger.log(f'[{self.project["code"]}][Runs] Failed to get test sets in PractiTest: {str(e)}', 'error')

            page = page + 1
        self.logger.log(f'[{self.project["code"]}][Runs] Items in index: {str(len(self.run_index))}')

    def _import_custom_fields_for_run(self, run: dict, data: dict) -> dict:
        fields = {}
        try:
            for field_name in run['attributes']['custom-fields']:
                if field_name and field_name != 'null':
                    search = re.search(r'\d+', field_name)
                    if search:
                        id = int(search[0])
                        value = run['attributes']['custom-fields'][field_name]
                        if type(value) == str:
                            value = self.to_list_if_possible(value)
                        fields[id] = value
        except Exception as e:
            self.logger.log(f'[{self.project["code"]}][Runs] Failed to get custom fields for run: {e}', 'error')

        try:
            fields = self._transform_chains(self.mappings.custom_fields_parent_map, fields)
        except Exception as e:
            self.logger.log(f'[{self.project["code"]}][Runs] Failed to transform chains: {e}', 'error')

        try:    
            for field_id in fields:
                if field_id in self.mappings.run_custom_fields:
                    custom_field = self.mappings.run_custom_fields[field_id]
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
        except Exception as e:
            self.logger.log(f'[{self.project["code"]}][Runs] Failed to import custom fields for run: {e}', 'error')

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
                    self.logger.log(f'[{self.project["code"]}][Runs] Custom field {custom_field["name"]} has invalid value {value}', 'warning')
                    return None
            elif type(value) == list:
                filtered_values = []
                for item in value:
                    if str(item) in values:
                        filtered_values.append(item)
                    else:
                        self.logger.log(f'[{self.project["code"]}][Runs] Custom field {custom_field["name"]} has invalid value {value}', 'warning')
                if len(filtered_values) == 0:
                    return None
                else:
                    return filtered_values
            return value
        return None

    def _build_run_case_index(self) -> None:
        self.logger.log(f'[{self.project["code"]}][Runs] Building run case index for project {self.project["name"]}')
        limit = self.limit
        page = 1

        while True:
            try:
                instances = self.practitest.get_instances(self.project['practitest_id'], limit, page)
                self.logger.log(f'[{self.project["code"]}][Runs] Found {str(len(instances["data"]))} test cases in PractiTest in test runs')

                for instance in instances['data']:
                    try:
                        self.run_index[instance['attributes']['set-display-id']]['cases'].append(instance['attributes']['test-display-id'])
                        self.run_case_index[int(instance['id'])] = {
                            "run_id": instance['attributes']['set-display-id'],
                            "case_id": instance['attributes']['test-display-id']
                        }
                    except Exception as e:
                        self.logger.log(f'[{self.project["code"]}][Runs] Failed to add test case to index: {str(e)}', 'error')

                if len(instances['data']) < limit:
                    break
            except Exception as e:
                self.logger.log(f'[{self.project["code"]}][Runs] Failed to get test cases in PractiTest in test runs: {str(e)}', 'error')

            page = page + 1

    def _build_run_result_index(self) -> None:
        self.logger.log(f'[{self.project["code"]}][Runs] Building run result index for project {self.project["name"]}')
        limit = self.limit
        page = 1

        while True:
            try:
                results = self.practitest.get_runs(self.project['practitest_id'], limit, page)
                self.logger.log(f'[{self.project["code"]}][Runs] Found {str(len(results["data"]))} test results in PractiTest')

                for result in results['data']:
                    if int(result['attributes']['instance-id']) in self.run_case_index.keys():
                        run_id = self.run_case_index[int(result['attributes']['instance-id'])]['run_id']
                        case_id = self.run_case_index[int(result['attributes']['instance-id'])]['case_id']

                        if not (self.run_result_index.get(run_id, None)):
                            self.run_result_index[run_id] = []

                        data = {
                            "case_id": case_id,
                            'author_id': self.mappings.get_user_id(int(result['attributes']['tester-id'])),
                            'status': self._get_result_status(result['attributes']['status']),
                            'time_ms': self.time_to_milliseconds(result['attributes']['run-duration']),
                            'comment': '',
                            'start_time': int(datetime.fromisoformat(result['attributes']['created-at']).timestamp()),
                            'steps': self._get_steps(int(result['id']))
                        }
                            
                        self.run_result_index[int(run_id)].append(data)

                if len(results['data']) < limit:
                    break
            except Exception as e:
                self.logger.log(f'[{self.project["code"]}][Runs] Failed to get test results in PractiTest: {str(e)}', 'error')

            page = page + 1

    def _get_steps(self, run_id: int) -> list:
        return self.run_steps_index[run_id] if run_id in self.run_steps_index else None

    def _build_run_steps_index(self) -> None:
        self.logger.log(f'[{self.project["code"]}][Runs] Building run steps index for project {self.project["name"]}')
        limit = self.limit
        page = 1

        while True:
            try:
                steps = self.practitest.get_run_steps(self.project['practitest_id'], limit, page)
                self.logger.log(f'[{self.project["code"]}][Runs] Found {str(len(steps["data"]))} test steps in PractiTest')

                for step in steps['data']:
                    if not (self.run_steps_index.get(int(step['attributes']['run-id']), None)):
                        self.run_steps_index[int(step['attributes']['run-id'])] = []

                    data = {
                        'position': step['attributes']['position'],
                        'status': self._get_result_step_status(step['attributes']['status']),
                        'attachments': []
                    }
                    data = self._get_attachments_for_step(int(step['id']), data)

                    comment = self.attachments.find_and_replace_attachments(str(step['attributes']['actual-results']), self.project['code'])
                    if comment:
                        data['comment'] = comment

                    self.run_steps_index[int(step['attributes']['run-id'])].append(data)

                if len(steps['data']) < limit:
                    break
            except Exception as e:
                self.logger.log(f'[{self.project["code"]}][Runs] Failed to get run steps in PractiTest: {str(e)}', 'error')
            page = page + 1

    def _get_attachments_for_step(self, step_id: int, data: dict) -> dict:
        try:
            attachments = self.attachments.import_attachments_for_entity(code = self.project['code'], project_id=self.project['practitest_id'], entity_type='step-run', entity_id=int(step_id))
            if attachments:
                for attachment in attachments['data']:
                    id = int(attachment['id'])
                    if id in self.mappings.attachments_map:
                        data['attachments'].append(self.mappings.attachments_map[id]['hash'])
        except Exception as e:
            self.logger.log(f'[{self.project["code"]}][Runs] Failed to get attachments for step {step_id}: {e}', 'error')
        return data

    async def _import_run(self, run: list) -> None:
        # Import results for the run
        qase_run_id = await self.pools.qs(self.qase.create_run, run, self.project['code'])

        if not bool(qase_run_id):
            self.logger.log(f'[{self.project["code"]}][Runs] Failed to create a new run in Qase for PractiTest run {run["name"]} [{run["id"]}]', 'error')
            return

        self.logger.log(f'[{self.project["code"]}][Runs] Created a new run in Qase: {qase_run_id}')
        self.mappings.stats.add_entity_count(self.project['code'], 'runs', 'qase')

        if run['id'] in self.run_result_index.keys() and len(self.run_result_index[run['id']]) > 0:
            await self.pools.qs(
                self.qase.send_bulk_results_raw,
                self.run_result_index[int(run['id'])],
                qase_run_id,
                self.project['code']
            )

    def _get_result_status(self, status: str) -> str:
        return self.mappings.practitest_run_statuses[status] if status in self.mappings.practitest_run_statuses else 'passed'
    
    def _get_result_step_status(self, status: str) -> str:
        return self.mappings.practitest_step_statuses[status] if status in self.mappings.practitest_step_statuses else 'passed'
        
    def time_to_milliseconds(self, time_str):
        """
        Convert a time string in HH:MM:SS format to milliseconds.
        
        :param time_str: Time string in HH:MM:SS format
        :return: Time in milliseconds
        """
        # Split the string into hours, minutes, and seconds
        hours, minutes, seconds = map(int, time_str.split(':'))
        
        # Convert to milliseconds
        total_milliseconds = (hours * 3600 + minutes * 60 + seconds) * 1000
        
        return total_milliseconds
    
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
            self.logger.log(f'[{self.project["code"]}][Runs] Failed to get value for custom field {qase_values}: {e}', 'error')
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