import asyncio

from ...service import QaseService, PractitestService
from ...support import Logger, Mappings, ConfigManager as Config, Pools

from .attachments import Attachments

from typing import List, Optional


class Suites:
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

        self.suites_map = {}
        self.logger.divider()

        self.roots = []
        self.children = []
        self.fake_index = 1000000

    def import_suites(self, project) -> Mappings:
        return self.mappings
