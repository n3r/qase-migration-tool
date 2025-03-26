from ..repository.practitest import PractitestApiRepository
from ..api.practitest import PractitestApiClient

class PractitestService:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.repository = PractitestApiRepository(
            PractitestApiClient(
                base_url = config.get('practitest.api.host'),
                token = config.get('practitest.api.token'),
                logger = logger,
                max_retries = 5,
                backoff_factor = 5
            )
        )
        
    def get_projects(self, limit: int = 100, page: int = 1):
        return self.repository.get_projects(limit, page)
    
    def get_users(self, limit: int = 250, page: int = 1):
        return self.repository.get_users(limit, page)
    
    def get_custom_fields(self, project_id: int, limit: int = 100, page: int = 1):
        return self.repository.get_custom_fields(project_id, limit, page)
    
    def get_project_fields(self, project_id: int, limit: int = 100, page: int = 1):
        return self.repository.get_project_fields(project_id, limit, page)
    
    def get_field_data(self, project_id: int, field_id: int):
        return self.repository.get_field_data(project_id, field_id)
    
    def get_instances(self, project_id: int, limit: int = 100, page: int = 1):
        return self.repository.get_instances(project_id, limit, page)
    
    def get_runs(self, project_id: int, limit: int = 100, page: int = 1):
        return self.repository.get_runs(project_id, limit, page)
    
    def get_run_steps(self, project_id: int, limit: int = 100, page: int = 1):
        return self.repository.get_run_steps(project_id, limit, page)
    
    def get_attachments_for_entity(self, project_id: int, entity_type: str, entity_id: int, limit: int = 100, page: int = 1):
        return self.repository.get_attachments_for_entity(project_id, entity_type, entity_id)
    
    def get_case_custom_fields(self):
        return self.repository.get_case_custom_fields()
    
    def get_case_system_fields(self):
        return self.repository.get_case_system_fields()
        
    def get_milestones(self, project_id: int, limit: int = 100, page: int = 1):
        return self.repository.get_milestones(project_id, limit, page)
    
    def get_root_suites(self, project_id: int, limit: int = 100, page: int = 1):
        return self.repository.get_root_suites(project_id, limit, page)
    
    def get_cases(self, project_id: int, limit: int = 100, page: int = 1):
        return self.repository.get_cases(project_id, limit, page)
    
    def get_test_sets(self, project_id: int, limit: int = 100, page: int = 1):
        return self.repository.get_test_sets(project_id, limit, page)
    
    def get_steps(self, project_id: int, limit: int = 100, page: int = 1):
        return self.repository.get_steps(project_id, limit, page)
    
    def get_children(self, tree_id: int):
        return self.repository.get_children(tree_id)
    
    def get_suite(self, tree_id: int):
        return self.repository.get_suite(tree_id)
    
    def get_releases(self, project_id: int):
        return self.repository.get_releases(project_id)
    
    def get_suites_by_release(self, release_id: int):
        return self.repository.get_suites_by_release(release_id)
    
    def get_attachment(self, project_id: int, attachment_id: int):
        return self.repository.get_attachment(project_id, attachment_id)

    def get_defects(self, project_id: int, limit: int = 100, page: int = 1):
        return self.repository.get_defects(project_id, limit, page)
