from ...api.zephyr_enterprise import ZephyrEnterpriseApiClient

class ZephyrEnterpriseApiRepository:
    def __init__(self, client: ZephyrEnterpriseApiClient):
        self.client = client
    
    def get_all_users(self):
        return
    
    def get_users(self, limit = 250, offset = 0):
        return self.client.get('user/filter?includeDashboardUser=true')
    
    def get_groups(self, limit = 250, offset = 0):
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
    
    def get_case_system_fields(self):
        return self.client.get('field/entity/TestCase?includsystemfield=true')
    
    def get_configurations(self, project_id: int):
        return
    
    def get_children(self, tree_id: int) -> list:
        return self.client.get(f'testcasetree/hierarchy/{tree_id}')
    
    def get_projects(self, limit = 250, offset = 0):
        return self.client.get('project/lite')
    
    def get_suite(self, tree_id: int):
        return self.client.get(f'testcasetree/{tree_id}')
    
    def get_releases(self, project_id: int):
        return self.client.get(f'release/project/{project_id}')
    
    def get_suites_by_release(self, release_id: int):
        return self.client.get(f'testcasetree/phases/{release_id}')
    
    def get_cases_for_suite(self, suite_id: int):
        return self.client.get(f'testcase/nodes?treeids={suite_id}')
    
    def get_suites(self, project_id, offset = 0, limit = 100):
        return
    
    def get_sections(self, project_id: int, limit: int = 100, offset: int = 0, suite_id: int = 0):
        return
    
    def get_shared_steps(self, project_id: int, limit: int = 250, offset: int = 0):
        return
    
    def get_cases(self, project_id: int, suite_id: int = 0, limit: int = 250, offset: int = 0) -> dict:
        return
    
    def get_runs(self, project_id: int, suite_id: int = 0, created_after: int = 0, limit: int = 250, offset: int = 0):
        return
    
    def get_results(self, run_id: int, limit: int = 250, offset: int = 0):
        return
    
    def get_attachment(self, attachment):
        return
    
    def get_attachments_list(self):
        return
    
    def get_attachments_case(self, case_id: int):
        return
    
    def get_test(self, test_id: int):
        return
    
    def get_tests(self, run_id: int, limit: int = 250, offset: int = 0):
        return
    
    def get_plans(self, project_id: int, limit: int = 250, offset: int = 0):
        return
    
    def get_plan(self, plan_id: int):
        return
    
    def get_milestones(self, project_id: int, limit: int = 250, offset: int = 0):
        return self.client.get(f'release/paged/project/{str(project_id)}?pagesize={limit}&offset={offset}')
    
    def get_root_suites(self, project_id: int, limit: int = 100, offset: int = 0):
        return self.client.get(f'testcasetree/projectrepository/{project_id}')
    
    def get_cases(self, suite_id: int = 0, limit: int = 250, offset: int = 0):
        return self.client.get(f'testcase/tree/{suite_id}?offset={offset}&pagesize={limit}')