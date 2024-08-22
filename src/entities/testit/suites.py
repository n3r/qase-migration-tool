import asyncio

from ..service import QaseService, TestItService
from ..support import Logger, Mappings, ConfigManager as Config, Pools

from .attachments import Attachments

from typing import List, Optional


class Suites:
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
        self.config = config
        self.logger = logger
        self.mappings = mappings
        self.pools = pools
        self.attachments = Attachments(self.qase, self.testit, self.logger, self.mappings, self.config, self.pools)

        self.suites_map = {}
        self.logger.divider()

        self.roots = []
        self.children = []

    def import_suites(self, project) -> Mappings:
        sections = self._get_sections(project['testit_id'])
        self.mappings.stats.add_entity_count(project['code'], 'suites', 'testit', len(sections))
        self.logger.log(f"[{project['code']}][Suites] Found {len(sections)} sections")

        for section in sections:
            if (section['parent_id'] == None):
                self.roots.append(section.to_dict())
            else:
                self.children.append(section.to_dict())

        for root in self.roots:
            root['children'] = self.build_children(root['id'])
            self._create_suite(project['code'], root)

        self.mappings.suites[project['code']] = self.suites_map
        return self.mappings
    
    def build_children(self, id: str):
        children = []
        for child in self.children:
            if child['parent_id'] == id:
                child['children'] = self.build_children(child['id'])
                children.append(child)
        return children


    def _create_suite(self, qase_code: str, section: dict):
        self.logger.log(f"[{qase_code}][Suites] Creating suite in Qase: {section['name']} ({section['id']})")
        parent_id = self.suites_map.get(section['parent_id'], None) if section['parent_id'] else None

        self.suites_map[section['id']] = self.qase.create_suite(
            code = qase_code.upper(),
            title = section['name'],
            description = None,
            parent_id = parent_id
        )
        self.mappings.stats.add_entity_count(qase_code, 'suites', 'qase')

        if section['children'] and len(section['children']) > 0:
            for child in section['children']:
                self._create_suite(qase_code, child)
    
    # Recursively get all sections
    def _get_sections(self, project_id: int, offset: int = 0, limit: int = 100) -> List:
        sections = self.testit.get_sections(project_id, limit, offset)
        if (len(sections) > 0 and len(sections) == limit):
            sections += self._get_sections(project_id, offset + limit, limit)
        return sections