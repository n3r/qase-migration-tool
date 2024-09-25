from .support import ConfigManager, Logger, Mappings, ThrottledThreadPoolExecutor, Pools

from .service import QaseService, QaseScimService

from concurrent.futures import ThreadPoolExecutor

class Importer:
    def __init__(self, config: ConfigManager, logger: Logger) -> None:
        self.pools = Pools(
            qase_pool=ThrottledThreadPoolExecutor(max_workers=8, requests=250, interval=12),
            source_pool=ThreadPoolExecutor(max_workers=8),
        )

        self.logger = logger
        self.config = config
        self.qase_scim_service = None
        self.source = config.get('source')
        
        self.qase_service = QaseService(config, logger)
        if config.get('qase.scim_token'):
            self.qase_scim_service = QaseScimService(config, logger)

        self.source_service = self.get_source_service()

        self.active_project_code = None

        self.mappings = Mappings(self.source, self.config.get('users.default'))

    def start(self):
        match self.source:
            case 'zephyr':
                self.logger.log('Zephyr is not supported yet')
                exit()
            case 'zephyr-enterprise':
                from .entities.zephyr_enterprise import Users, Fields, Projects, Attachments
            case 'testrail':
                from .entities.testrail import Users, Fields, Projects, Attachments
            case 'testrail-legacy':
                from .entities.testrail_legacy import Users, Fields, Projects, Attachments
            case 'testit':
                from .entities.testit import Users, Fields, Projects, Attachments
            case 'testlink':
                self.logger.log('Testlink is not supported yet')
                exit()
            case 'xray':
                self.logger.log('Xray is not supported yet')
                exit()
            case 'practitest':
                self.logger.log('Practitest is not supported yet')
                exit()
            case 'qtest':
                self.logger.log('QTest is not supported yet')
                exit()
            case 'allure-testops':
                self.logger.log('Allure TestOps is not supported yet')
                exit()
            case 'tuskr':
                self.logger.log('Tuskr is not supported yet')
                exit()
            case 'testmo':
                self.logger.log('Testmo is not supported yet')
                exit()
            case _:
                self.logger.log('Source is not supported yet')
                exit()
        
        # Step 1. Build users map +
        self.mappings = Users(
            self.qase_service,
            self.source_service,
            self.logger,
            self.mappings,
            self.config,
            self.pools,
            self.qase_scim_service,
        ).import_users()

        # Step 2. Import project and build projects map +
        self.mappings = Projects(
            self.qase_service, 
            self.source_service, 
            self.logger, 
            self.mappings,
            self.config,
            self.pools,
        ).import_projects()

        # Step 3. Import attachments +
        self.mappings = Attachments(
            self.qase_service,
            self.source_service,
            self.logger,
            self.mappings,
            self.config,
            self.pools,
        ).import_all_attachments()

        # Step 4. Import custom fields
        self.mappings = Fields(
            self.qase_service, 
            self.source_service, 
            self.logger, 
            self.mappings,
            self.config,
            self.pools,
        ).import_fields()

        # Step 5. Import projects data in parallel
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            for project in self.mappings.projects:
                # Submit each project import to the thread pool
                future = executor.submit(self.import_project_data, project)
                futures.append(future)

            # Wait for all futures to complete
            for future in futures:
                # This will also re-raise any exceptions caught during execution of the callable
                future.result()

        self.mappings.stats.print()
        self.mappings.stats.save(str(self.config.get('prefix')))
        self.mappings.stats.save_xlsx(str(self.config.get('prefix')))

    def import_project_data(self, project):
        match self.source:
            case 'zephyr-enterprise':
                from .entities.zephyr_enterprise import Suites, Cases, Runs, Milestones, Configurations, SharedSteps
            case 'testrail':
                from .entities.testrail import Suites, Cases, Runs, Milestones, Configurations, SharedSteps
            case 'testrail-legacy':
                from .entities.testrail_legacy import Suites, Cases, Runs, Milestones, Configurations, SharedSteps
            case 'testit':
                from .entities.testit import Suites, Cases, Runs, Milestones, Configurations, SharedSteps
            case _:
                self.logger.log('Source is not supported yet')
                exit()
                
        self.logger.print_group(f'Importing project: {project["name"]}'
                                + (' ('
                                   + project['suite_title']
                                   + ')' if 'suite_title' in project else ''))

        # Step 5.1. Import configurations +
        self.mappings = Configurations(
            self.qase_service,
            self.source_service,
            self.logger,
            self.mappings,
            self.pools,
        ).import_configurations(project)

        # Step 5.2. Import shared steps +
        self.mappings = SharedSteps(
            self.qase_service,
            self.source_service,
            self.logger,
            self.mappings,
            self.pools,
        ).import_shared_steps(project)

        # Step 5.3. Import milestones
        self.mappings = Milestones(
            self.qase_service,
            self.source_service,
            self.logger,
            self.mappings,
        ).import_milestones(project)

        # Step 5.4. Import suites
        self.mappings = Suites(
            self.qase_service,
            self.source_service,
            self.logger,
            self.mappings,
            self.config,
            self.pools,
        ).import_suites(project)

        # Step 5.5. Import cases
        Cases(
            self.qase_service,
            self.source_service,
            self.logger,
            self.mappings,
            self.config,
            self.pools,
        ).import_cases(project)

        # Step 5.6. Import runs
        #Runs(
        #    self.qase_service,
        #    self.source_service,
        #    self.logger,
        #    self.mappings,
        #    self.config,
        #    project,
        #    self.pools,
        #).import_runs()

    def get_source_service(self):
        match self.source:
            case 'zephyr-enterprise':
                from .service import ZephyrEnterpriseService
                return ZephyrEnterpriseService(self.config, self.logger)
            case 'testrail':
                from .service import TestrailService
                return TestrailService(self.config, self.logger)
            case 'testrail-legacy':
                from .service import TestrailLegacyService
                return TestrailLegacyService(self.config, self.logger)
            case 'testit':
                from .service import TestitService
                return TestitService(self.config, self.logger)
            case _:
                raise Exception('Invalid source')