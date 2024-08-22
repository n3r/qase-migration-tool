import asyncio

from ..service import QaseService, TestItService
from ..support import Logger, Mappings, ConfigManager as Config, Pools

from typing import List

from io import BytesIO

from urllib.parse import unquote

import re


class Attachments:
    def __init__(
            self,
            qase_service: QaseService,
            testit_service: TestItService,
            logger: Logger,
            mappings: Mappings,
            config: Config,
            pools: Pools,
    ):
        self.qase = qase_service
        self.testit = testit_service
        self.logger = logger
        self.config = config
        self.mappings = mappings
        self.pools = pools
        self.pattern = r'!\[\]\(index\.php\?/attachments/get/([a-f0-9-]+)\)'

    def check_and_replace_attachments(self, string: str, code: str) -> str:
        if string:
            attachments = self.check_attachments(string)
            if (attachments):
                return self.replace_attachments(string=string, code = code)
        return str(string)
    
    def check_and_replace_attachments_array(self, attachments: list, code: str) -> list:
        result = []
        for attachment in attachments:
            if attachment:
                attachment = re.sub(r'^E_', '', attachment)
            if attachment and attachment not in self.mappings.attachments_map:
                self.logger.log(f'[Attachments] Attachment {attachment} not found in attachments_map (array)', 'warning')
                self.replace_failover(attachment, code)
            if attachment and attachment in self.mappings.attachments_map and self.mappings.attachments_map[attachment] and 'hash' in self.mappings.attachments_map[attachment]:
                result.append(self.mappings.attachments_map[attachment]['hash'])
        return result
    
    def check_attachments(self, string: str) -> List:
        if (string):
            return re.findall(r'index\.php\?/attachments/get/([a-f0-9-]+)', str(string))
        return []

    def import_all_attachments(self) -> Mappings:
        return asyncio.run(self.import_all_attachments_async())

    async def import_all_attachments_async(self) -> Mappings:
        self.logger.log('[Attachments] Importing all attachments')
        attachments_raw = self.testit.get_attachments()
        self.mappings.stats.add_attachment('testit', len(attachments_raw))

        async with asyncio.TaskGroup() as tg:
            for attachment in attachments_raw:
                tg.create_task(self.import_raw_attachment(attachment))

        self.logger.log(f'[Attachments] Imported {len(attachments_raw)} attachments')

        return self.mappings

    async def import_raw_attachment(self, attachment):
        self.logger.log(f'[Attachments] Importing attachment: {attachment["id"]}')
        if len(attachment['project_id']) > 1:
            self.logger.log(f'[Attachments] Attachment {attachment["id"]} is linked to multiple projects', 'warning')
        if len(attachment['project_id']) > 0:
            if attachment['project_id'][0] in self.mappings.project_map:
                code = self.mappings.project_map[attachment['project_id'][0]]
                try: 
                    meta = self._get_attachment_meta(await self.pools.tr(self.testit.get_attachment, attachment['id']))
                except Exception as e:
                    self.logger.log(f'[Attachments] Exception when calling TestIT->get_attachment: {e}', 'error')
                    return

                try:
                    qase_attachment = await self.pools.qs(self.qase.upload_attachment, code, meta)
                    if qase_attachment:
                        self.mappings.attachments_map[attachment['id']] = qase_attachment
                        self.logger.log(f'[Attachments] Attachment {attachment["id"]} imported')
                        self.mappings.stats.add_attachment('qase')
                    else:
                        self.logger.log(f'[Attachments] Attachment {attachment["id"]} not imported', 'error')
                except Exception as e:
                    self.logger.log(f'[Attachments] Exception when calling Qase->upload_attachment: {e}', 'error')
            else:
                self.logger.log(f'[Attachments] Attachment {attachment["id"]} is not linked to any project', 'error')
        else:
            self.logger.log(f'[Attachments] Attachment {attachment["id"]} is not linked to any project', 'warning')
