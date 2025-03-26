import asyncio

from ...service import QaseService, QaseScimService, PractitestService
from ...support import Logger, Mappings, ConfigManager as Config, Pools
import time

class Users:
    def __init__(
        self,
        qase_service: QaseService,
        source_service: PractitestService,
        logger: Logger,
        mappings: Mappings,
        config: Config,
        pools: Pools,
        scim_service: QaseScimService = None,
    ):
        self.qase = qase_service
        self.scim = scim_service
        self.practitest = source_service
        self.logger = logger
        self.mappings = mappings
        self.config = config
        self.pools = pools
        self.map = {}  # This is a map of TestRail user ids to Qase user ids. Used for mapping users to groups
        self.active_ids = []  # This is a list of Qase active users that should be added to groups
        self.practitest_users = []
        self.logger.divider()

    def import_users(self):
        return asyncio.run(self.import_users_async())
    
    async def import_users_async(self):
        await self.get_practitest_users()

        if self.scim is not None:
            await self.create_users()

        await self.build_map()

        return self.mappings

    async def build_map(self):
        self.logger.log("[Users] Building users map")
        qase_users = await self.pools.qs_gen_all(self.qase.get_all_users)
        self.mappings.stats.add_user('qase', len(qase_users))
        self.mappings.stats.add_user('practitest', len(self.practitest_users))
        i = 0
        total = len(self.practitest_users)
        self.logger.print_status('Building users map', i, total)
        for practitest_user in self.practitest_users:
            i += 1
            flag = False
            for qase_user in qase_users:
                qase_user = qase_user.to_dict()
                if practitest_user['attributes']['email'].lower() == qase_user['email'].lower():
                    self.mappings.users[int(practitest_user['id'])] = qase_user['id']
                    flag = True
                    self.logger.log(f"[Users] User {practitest_user['attributes']['email']} found in Qase as {qase_user['email']}")
                    break
            if not flag:
                # Not found, using default user
                self.mappings.users[int(practitest_user['id'])] = self.config.get('users.default')
                self.logger.log(f"[Users] User {practitest_user['attributes']['email']} not found in Qase, using default user.")
            self.logger.print_status('Building users map', i, total)

    async def create_users(self):
        self.logger.log("[Users] Loading users from Qase using SCIM")
        qase_users = await self.pools.qs_gen_all(self.scim.get_all_users)

        async with asyncio.TaskGroup() as tg:
            for practitest_user in self.practitest_users:
                flag = False
                for qase_user in qase_users:
                    if practitest_user['attributes']['email'].lower() == qase_user['userName'].lower():
                        self.logger.log("[Users] User found in Qase using SCIM, skipping creation.")
                        self.map[practitest_user['id']] = qase_user['id']
                        self.active_ids.append(qase_user['id'])
                        flag = True
                if not flag:
                    try:
                        if self.config.get('users.create'):
                            tg.create_task(self.import_user(practitest_user))
                    except Exception as e:
                        self.logger.log(f"[Users] Failed to create user {practitest_user['attributes']['email']}", 'error')
                        self.logger.log(f'{e}')
                        continue
    
    async def create_user(self, practitest_user):
        # Function creates a new user in Qase
        self.logger.log(f"[Users] Creating user {practitest_user['attributes']['email']} in Qase")

        user_id = await self.pools.qs(
            self.scim.create_user,
            practitest_user['attributes']['email'],
            practitest_user['attributes']['first-name'],
            practitest_user['attributes']['last-name'],
            '',
            True,
        )
        self.logger.log(f"[Users] User {practitest_user['attributes']['email']} created in Qase with id {user_id}")
        return user_id

    async def get_practitest_users(self):
        self.logger.log("[Users] Getting users from Practitest")

        limit = 100
        page = 1

        while True:
            users = await self.pools.source(self.practitest.get_users, limit, page)
            if 'data' in users and users['data'] is not None:
                users = users['data']

            self.practitest_users = self.practitest_users + users

            if len(users) < limit:
                break

            page += 1

    async def import_user(self, practitest_user):
        user_id = await self.create_user(practitest_user)
        self.map[practitest_user['id']] = user_id