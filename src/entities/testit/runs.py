import asyncio

from ...service import QaseService, TestItService
from ...support import Logger, Mappings, ConfigManager as Config, Pools
from .attachments import Attachments

class Runs:
    def __init__(
            self,
            qase_service: QaseService,
            source_service: TestItService,
            logger: Logger,
            mappings: Mappings, config: Config,
            project: list,
            pools: Pools,
    ):
        self.qase = qase_service
        self.testit = source_service
        self.config = config
        self.logger = logger
        self.mappings = mappings
        self.project = project
        self.pools = pools

        self.attachments = Attachments(self.qase, self.testrail, self.logger, self.mappings, self.config, self.pools)
        
        self.configurations = self.mappings.configurations[self.project['code']]

        self.created_after = self.config.get('runs.created_after')
        self.index = []
        self.logger.divider()

    def import_runs(self) -> None:
        return