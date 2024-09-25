from ...service import QaseService, ZephyrEnterpriseService
from ...support import Logger, Mappings, ConfigManager as Config, Pools

class Attachments:
    def __init__(
            self,
            qase_service: QaseService,
            source_service: ZephyrEnterpriseService,
            logger: Logger,
            mappings: Mappings,
            config: Config,
            pools: Pools,
    ):
        self.qase = qase_service
        self.zephyr = source_service
        self.logger = logger
        self.config = config
        self.mappings = mappings
        self.pools = pools
    
    def import_all_attachments(self) -> Mappings:
        # Zephyr Enterprise doesn't support bulk attachments import
        return self.mappings