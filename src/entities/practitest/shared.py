import asyncio

from ...service import QaseService, PractitestService
from ...support import Logger, Mappings, Pools


class SharedSteps:
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
        self.project = None

        self.map = {}
        self.logger.divider()
        self.i = 0

    def import_shared_steps(self, project) -> Mappings:
        # Practitest doesn't have shared steps
        return self.mappings