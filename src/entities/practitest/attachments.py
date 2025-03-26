from ...service import QaseService, PractitestService
from ...support import Logger, Mappings, ConfigManager as Config, Pools
from io import BytesIO
import re
from urllib.parse import unquote
import mimetypes

from typing import List

class Attachments:
    def __init__(
            self,
            qase_service: QaseService,
            source_service: PractitestService,
            logger: Logger,
            mappings: Mappings,
            config: Config,
            pools: Pools,
    ):
        self.qase = qase_service
        self.practitest = source_service
        self.logger = logger
        self.config = config
        self.mappings = mappings
        self.pools = pools
    
    def import_all_attachments(self) -> Mappings:
        # Practitest doesn't support bulk attachments import
        return self.mappings
    
    def import_attachment(self, code: str, name: str, project_id: int, attachment_id: int):
        try:
            content = self.practitest.get_attachment(project_id, attachment_id)
            meta = self.build_attachment_meta(name, content, len(content))
            if meta:
                qase_attachment = self.qase.upload_attachment(code, meta)
                if qase_attachment:
                    self.mappings.attachments_map[int(attachment_id)] = qase_attachment
                    self.logger.log(f'[Attachments] Attachment {attachment_id} uploaded to Qase')
                    return qase_attachment
                else:
                    self.logger.log(f'[Attachments] Attachment {attachment_id} failed to upload to Qase', 'error')
        except Exception as e:
            self.logger.log(f'[{code}][Tests] Failed to get attachment {attachment_id}: {e}', 'error')
        return None
    
    def import_attachments_for_entity(self, code: str, project_id: int, entity_type: str, entity_id: int) -> list:
        self.logger.log(f'[{code}][Tests] Getting attachments for {entity_type} with ID: {entity_id}')
        try:
            attachments = self.practitest.get_attachments_for_entity(project_id, entity_type, entity_id)
            if attachments and attachments['data']:
                self.logger.log(f'[{code}][Tests] Found {len(attachments["data"])} attachments for {entity_type} with ID: {entity_id}')
                for attachment in attachments['data']:
                    try:
                        id = int(attachment['id'])
                        if id not in self.mappings.attachments_map:
                            self.import_attachment(code, attachment['attributes']['name'], project_id, int(id))
                    except Exception as e:
                        self.logger.log(f'[{code}][Tests] Failed to import attachment for {entity_type} with ID: {entity_id}: {e}', 'error')
                return attachments
        except Exception as e:
            self.logger.log(f'[{code}][Tests] Failed to get attachments for {entity_type} with ID: {entity_id}: {e}', 'error')
        return []

    def build_attachment_meta(self, filename: str, content: bytes, size: int) -> dict:
        content = BytesIO(content)
        content.mime = self._get_mime_type(filename)
        content.name = filename
        content.size = size

        return content
    
    def _get_mime_type(self, filename: str) -> str:
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type
    
    def find_and_replace_attachments(self, text: str, code: str) -> str:
        if text:
            try:
                """
                Finds PractiTest attachment URLs in Markdown image syntax and replaces them 
                with <REPLACED>. Also prints out captured project_id and attachment_id.
                """

                # Regex to match the entire Markdown pattern and extract the URL in group(1)
                # Example matched text: ![ ](https://eu1-prod.practitest.app/projects/16396/pattachments/12266508?style=thumb)
                image_pattern = re.compile(r'!\[[^\]]*\]\((https?://[^)]+)\)')
                
                # Regex to parse the project_id and attachment_id from the URL
                # Example URL: https://eu1-prod.practitest.app/projects/16396/pattachments/12266508?style=thumb
                url_pattern = re.compile(r'/projects/(\d+)/pattachments/(\d+)')

                def replacement_function(match):
                    """
                    This function will be called for each match of the image_pattern. 
                    We extract the URL, parse out the IDs, and then return "<REPLACED>".
                    """
                    url = match.group(1)  # The full URL within parentheses
                    
                    # Attempt to parse out project ID and attachment ID
                    url_match = url_pattern.search(url)
                    if url_match:
                        return ""
                    else:
                        self.logger.log(f'[{code}][Attachments] URL found, but could not parse project_id and attachment_id', 'error')
                    # Use sub with a function so we can parse IDs before replacing
                text = image_pattern.sub(replacement_function, text)
            except Exception as e:
                self.logger.log(f'[{code}][Attachments] Failed to find and replace attachments: {str(e)}', 'error')
        return text