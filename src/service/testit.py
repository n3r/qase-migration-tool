import testit_api_client
from testit_api_client.rest import ApiException
from testit_api_client.api_client import ApiClient
from testit_api_client.api import projects_api
from testit_api_client.api import project_sections_api
from testit_api_client.api import project_work_items_api
from testit_api_client.api import work_items_api
from testit_api_client.api import attachments_api


class TestItService:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger


        configuration = testit_api_client.Configuration()
        configuration.host = self.config.get('testit.host')
        configuration.verify_ssl = False

        self.client = ApiClient(configuration=configuration, header_name='Authorization', header_value=f"PrivateToken {self.config.get('testit.token')}")
        
    def get_projects(self, limit: int = 100, offset: int = 0):
        api_instance = projects_api.ProjectsApi(self.client)

        try:
            return api_instance.get_all_projects(skip=offset, take=limit)
        except testit_api_client.ApiException as e:
            print("Exception when calling ProjectsApi->get_all_projects: %s\n" % e)

    def get_sections(self, project_id: int, limit: int = 100, offset: int = 0):
        api_instance = project_sections_api.ProjectSectionsApi(self.client)

        try:
            return api_instance.get_sections_by_project_id(str(project_id), skip=offset, take=limit)
        except testit_api_client.ApiException as e:
            print("Exception when calling ProjectSectionsApi->get_sections_by_project_id: %s\n" % e)
    
    def get_cases(self, project_id: int, limit: int = 100, offset: int = 0):
        api_instance = project_work_items_api.ProjectWorkItemsApi(self.client)

        try:
            return api_instance.get_work_items_by_project_id(str(project_id), skip=offset, take=limit, include_iterations=True)
        except testit_api_client.ApiException as e:
            print("Exception when calling get_work_items_by_project_id: %s\n" % e)

    def get_case(self, id):
        api_instance = work_items_api.WorkItemsApi(self.client)

        try:
            return api_instance.get_work_item_by_id(id)
        except testit_api_client.ApiException as e:
            print("Exception when calling get_work_item_by_id: %s\n" % e)