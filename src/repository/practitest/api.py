from ...api.practitest import PractitestApiClient

class PractitestApiRepository:
    def __init__(self, client: PractitestApiClient):
        self.client = client
    
    def get_all_users(self):
        return
    
    def get_users(self, limit = 100, page = 1):
        return self.client.get(f'users.json?page[size]={limit}&page[number]={page}')
    
    def get_custom_fields(self, project_id: int, limit: int = 100, page: int = 1):
        return self.client.get(f'projects/{project_id}/custom_fields.json?page[size]={limit}&page[number]={page}')
    
    def get_project_fields(self, project_id: int, limit: int = 100, page: int = 1):
        return self.client.get(f'projects/{project_id}/fields.json?page[size]={limit}&page[number]={page}')
    
    def get_field_data(self, project_id: int, field_id: int):
        return self.client.get(f'projects/{project_id}/custom_fields/{field_id}.json')
    
    def get_instances(self, project_id: int, limit: int = 100, page: int = 1):
        return self.client.get(f'projects/{project_id}/instances.json?page[size]={limit}&page[number]={page}')
    
    def get_groups(self, limit = 100, page = 1):
        return
    
    def get_case_types(self):
        return
    
    def get_result_statuses(self):
        return
    
    def get_case_statuses(self):
        return
    
    def get_priorities(self):
        return
    
    def get_case_custom_fields(self):
        return self.client.get('field/entity/TestCase')
    
    def get_attachments_for_entity(self, project_id: int, entity_type: str, entity_id: int):
        return self.client.get(f'projects/{project_id}/attachments.json?entity={entity_type}&entity-id={entity_id}')
    
    def get_case_system_fields(self):
        return self.client.get('field/entity/TestCase?includsystemfield=true')
    
    def get_configurations(self, project_id: int):
        return
    
    def get_children(self, tree_id: int) -> list:
        return self.client.get(f'testcasetree/hierarchy/{tree_id}')
    
    def get_projects(self, limit = 100, page = 1):
        return self.client.get('projects.json')
    
    def get_cases(self, project_id: int, limit: int = 250, page: int = 1):
        return self.client.get(f'projects/{project_id}/tests.json?page[size]={limit}&page[number]={page}')
    
    def get_steps(self, project_id: int, limit: int = 250, page: int = 1):
        return self.client.get(f'projects/{project_id}/steps.json?page[size]={limit}&page[number]={page}')
    
    def get_runs(self, project_id: int, limit: int = 100, page: int = 1):
        return self.client.get(f'projects/{project_id}/runs.json?page[size]={limit}&page[number]={page}')
    
    def get_run_steps(self, project_id: int, limit: int = 100, page: int = 1):
        return self.client.get(f'projects/{project_id}/step_runs.json?page[size]={limit}&page[number]={page}')
    
    def get_test_sets(self, project_id: int, limit: int = 100, page: int = 1):
        return self.client.get(f'projects/{project_id}/sets.json?page[size]={limit}&page[number]={page}')
    
    def get_results(self, run_id: int, limit: int = 250, offset: int = 0):
        return
    
    def get_attachment(self, project_id: int, attachment_id: int):
        return self.client.get_file(f'projects/{project_id}/attachments/{attachment_id}')
    
    def get_defects(self, project_id: int, limit: int = 100, page: int = 1):
        return self.client.get(f'projects/{project_id}/issues.json?page[size]={limit}&page[number]={page}')