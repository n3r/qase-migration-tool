from ..repository.zephyr_enterprise import ZephyrEnterpriseApiRepository
from ..api.zephyr_enterprise import ZephyrEnterpriseApiClient


class ZephyrEnterpriseService:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.repository = ZephyrEnterpriseApiRepository(
            ZephyrEnterpriseApiClient(
                base_url = config.get('zephyr_enterprise.api.host'),
                token = config.get('zephyr_enterprise.api.token'),
                logger = logger,
                max_retries = 5,
                backoff_factor = 5
            )
        )
        
    def get_projects(self, limit: int = 100, offset: int = 0):
        return self.repository.get_projects(limit, offset)
    
    def get_users(self):
        return self.repository.get_users()
    
    def get_case_custom_fields(self):
        return self.repository.get_case_custom_fields()
    
    def get_case_system_fields(self):
        return self.repository.get_case_system_fields()
        
    def get_milestones(self, project_id: int, limit: int = 250, offset: int = 0):
        return self.repository.get_milestones(project_id, limit, offset)
    
    def get_root_suites(self, project_id: int, limit: int = 100, offset: int = 0):
        return self.repository.get_root_suites(project_id, limit, offset)
    
    def get_cases(self, suite_id: int = 0, limit: int = 250, offset: int = 0):
        return self.repository.get_cases(suite_id, limit, offset)
    
    def get_cases_for_suite(self, suite_id: int):
        return self.repository.get_cases_for_suite(suite_id)
    
    def get_children(self, tree_id: int):
        return self.repository.get_children(tree_id)
    
    def get_suite(self, tree_id: int):
        return self.repository.get_suite(tree_id)
    
    def get_releases(self, project_id: int):
        return self.repository.get_releases(project_id)
    
    def get_suites_by_release(self, release_id: int):
        return self.repository.get_suites_by_release(release_id)