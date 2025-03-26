from ...service import QaseService, PractitestService
from ...support import Logger, Mappings


class Milestones:
    def __init__(self, qase_service: QaseService, source_service: PractitestService, logger: Logger, mappings: Mappings) -> Mappings:
        self.qase = qase_service
        self.practitest = source_service
        self.logger = logger
        self.mappings = mappings

        self.map = {}
        self.logger.divider()
        self.i = 0

    # Milestones API are not supported by Practitest
    def import_milestones(self, project) -> Mappings:
        return self.mappings