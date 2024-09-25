import asyncio

from ...service import QaseService, QaseScimService, ZephyrEnterpriseService
from ...support import Logger, Mappings, ConfigManager as Config, Pools


class Users:
    def __init__(
        self,
        qase_service: QaseService,
        source_service: ZephyrEnterpriseService,
        logger: Logger,
        mappings: Mappings,
        config: Config,
        pools: Pools,
        scim_service: QaseScimService = None,
    ):
        self.qase = qase_service
        self.scim = scim_service
        self.zephyr = source_service
        self.logger = logger
        self.mappings = mappings
        self.config = config
        self.pools = pools
        self.map = {}  # This is a map of TestRail user ids to Qase user ids. Used for mapping users to groups
        self.active_ids = []  # This is a list of Qase active users that should be added to groups
        self.zephyr_users = []
        self.logger.divider()

    def import_users(self):
        return asyncio.run(self.import_users_async())
    
    async def import_users_async(self):
        await self.get_zephyr_users()

        if self.scim is not None:
            await self.create_users()

        await self.build_map()

        return self.mappings

    async def build_map(self):
        self.logger.log("[Users] Building users map")
        qase_users = await self.pools.qs_gen_all(self.qase.get_all_users)
        self.mappings.stats.add_user('qase', len(qase_users))
        self.mappings.stats.add_user('zephyr-enterprise', len(self.zephyr_users))
        i = 0
        total = len(self.zephyr_users)
        self.logger.print_status('Building users map', i, total)
        for zephyr_user in self.zephyr_users:
            i += 1
            flag = False
            for qase_user in qase_users:
                qase_user = qase_user.to_dict()
                if zephyr_user['email'].lower() == qase_user['email'].lower():
                    self.mappings.users[zephyr_user['id']] = qase_user['id']
                    flag = True
                    self.logger.log(f"[Users] User {zephyr_user['email']} found in Qase as {qase_user['email']}")
                    break
            if not flag:
                # Not found, using default user
                self.mappings.users[zephyr_user['id']] = self.config.get('users.default')
                self.logger.log(f"[Users] User {zephyr_user['email']} not found in Qase, using default user.")
            self.logger.print_status('Building users map', i, total)

    async def create_users(self):
        self.logger.log("[Users] Loading users from Qase using SCIM")
        qase_users = await self.pools.qs_gen_all(self.scim.get_all_users)

        async with asyncio.TaskGroup() as tg:
            for zephyr_user in self.zephyr_users:
                flag = False
                for qase_user in qase_users:
                    if zephyr_user['email'].lower() == qase_user['userName'].lower():
                        self.logger.log("[Users] User found in Qase using SCIM, skipping creation.")
                        self.map[zephyr_user['id']] = qase_user['id']
                        if zephyr_user['accountEnabled']:
                            self.active_ids.append(qase_user['id'])
                        flag = True
                if not flag:
                    # Not found, using default user
                    if zephyr_user['accountEnabled'] is False and not self.config.get('users.inactive'):
                        self.logger.log(f"[Users] User {zephyr_user['email']} is not active, skipping creation.")
                        continue
                    try:
                        if self.config.get('users.create'):
                            tg.create_task(self.import_user(zephyr_user))
                    except Exception as e:
                        self.logger.log(f"[Users] Failed to create user {zephyr_user['email']}", 'error')
                        self.logger.log(f'{e}')
                        continue
    
    async def create_user(self, zephyr_user):
        # Function creates a new user in Qase
        self.logger.log(f"[Users] Creating user {zephyr_user['email']} in Qase")

        user_id = await self.pools.qs(
            self.scim.create_user,
            zephyr_user['email'],
            zephyr_user['firstName'],
            zephyr_user['lastName'],
            zephyr_user['title'],
            int(zephyr_user['accountEnabled']),
        )
        self.logger.log(f"[Users] User {zephyr_user['email']} created in Qase with id {user_id}")
        return user_id

    async def get_zephyr_users(self):
        self.logger.log("[Users] Getting users from Zephyr Enterprise")
        users = await self.pools.source(self.zephyr.get_users)
        return users
