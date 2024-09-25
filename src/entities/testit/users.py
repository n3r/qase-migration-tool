from ...service import QaseService, QaseScimService, TestItService
from ...support import Logger, Mappings, ConfigManager as Config, Pools


class Users:
    def __init__(
        self,
        qase_service: QaseService,
        source_service: TestItService,
        logger: Logger,
        mappings: Mappings,
        config: Config,
        pools: Pools,
        scim_service: QaseScimService = None,
    ):
        self.qase = qase_service
        self.scim = scim_service
        self.testit = source_service
        self.logger = logger
        self.mappings = mappings
        self.config = config
        self.pools = pools
        self.map = {}
        self.active_ids = []
        self.testit_users = []
        self.logger.divider()

    def import_users(self):
        # Not supported yet
        return self.mappings
