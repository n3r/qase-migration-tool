from ...service import QaseService, PractitestService
from ...support import Logger, Mappings, Pools

import asyncio


class Configurations:
    def __init__(
            self,
            qase_service: QaseService,
            source_service: PractitestService,
            logger: Logger,
            mappings: Mappings,
            pools: Pools,
    ):
        self.qase = qase_service
        self.practitest = source_service
        self.logger = logger
        self.mappings = mappings
        self.pools = pools

        self.map = {}
        self.logger.divider()

    def import_configurations(self, project) -> Mappings:
        return self.mappings