import time
import requests
import http.client
from ..exceptions.api import APIError


class ZephyrEnterpriseApiClient:
    def __init__(self, base_url, token, logger, max_retries=7, backoff_factor=5):
        if not base_url.endswith('/'):
            base_url += '/'
        self.__url = base_url + 'flex/services/rest/latest/'
        self.logger = logger
        self.base_url = base_url

        self.headers = {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json',
        }
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.page_size = 30

    def get(self, uri):
        return self.send_request(requests.get, uri)

    def send_request(self, request_method, uri, payload=None):
        url = self.__url + uri
        for attempt in range(self.max_retries + 1):
            try:
                response = request_method(url, headers=self.headers, data=payload)
                if response.status_code != 429 and response.status_code <= 201:
                    return self.process_response(response, uri)
                if response.status_code == 403:
                    raise APIError('Access denied.')
                if response.status_code == 400:
                    raise APIError('Invalid data or entity not found.')
                else:
                    time.sleep(self.backoff_factor * (2 ** attempt))
            except (requests.exceptions.Timeout, http.client.RemoteDisconnected, ConnectionResetError, requests.exceptions.ConnectionError) as e:
                time.sleep(self.backoff_factor * (2 ** attempt))
            
            if attempt == self.max_retries:
                raise APIError('Max retries reached or server error.')

    def process_response(self, response, uri):
        try:
            return response.json()
        except:
            raise APIError('Failed to parse JSON response')