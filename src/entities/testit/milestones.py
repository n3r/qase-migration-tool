from ...service import QaseService, TestItService
from ...support import Logger, Mappings


class Milestones:
    def __init__(self, qase_service: QaseService, source_service: TestItService, logger: Logger, mappings: Mappings) -> Mappings:
        self.qase = qase_service
        self.testit = source_service
        self.logger = logger
        self.mappings = mappings

        self.map = {}
        self.logger.divider()
        self.i = 0

    def import_milestones(self, project) -> Mappings:
        return self.mappings