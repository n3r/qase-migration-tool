import time
import requests
import http.client
import random
import sqlite3
import json
import hashlib
from ..exceptions.api import APIError

class PractitestApiClient:
    def __init__(self, base_url, token, logger, max_retries=3, backoff_factor=5, db_path='api_cache.db'):
        if not base_url.endswith('/'):
            base_url += '/'
        self.__url = base_url + 'api/v2/'
        self.logger = logger
        self.token = token
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.db_path = db_path
        self._initialize_cache()

    def _initialize_cache(self):
        """Initialize SQLite database for caching API responses."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_cache (
                    request_hash TEXT PRIMARY KEY,
                    response_data TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def _set_headers(self):
        token = self._get_token()
        return {
            'PTToken': token,
            'Content-Type': 'application/json',
        }

    def _get_token(self):
        if isinstance(self.token, list):
            return random.choice(self.token)
        return self.token

    def _generate_cache_key(self, uri):
        """Generate a unique cache key based on the request URI."""
        return hashlib.sha256(uri.encode()).hexdigest()

    def _get_from_cache(self, uri):
        """Retrieve cached response if available."""
        cache_key = self._generate_cache_key(uri)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT response_data FROM api_cache WHERE request_hash = ?', (cache_key,))
            row = cursor.fetchone()
            if row:
                self.logger.log(f"Cache hit for URI: {uri}")
                return json.loads(row[0])
        self.logger.log(f"Cache miss for URI: {uri}")
        return None

    def _save_to_cache(self, uri, response_data):
        """Save response data to the cache."""
        cache_key = self._generate_cache_key(uri)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO api_cache (request_hash, response_data)
                VALUES (?, ?)
            ''', (cache_key, json.dumps(response_data)))
            conn.commit()
        self.logger.log(f"Response cached for URI: {uri}")

    def get(self, uri):
        """Fetch data using GET, utilizing caching if possible."""
        cached_response = self._get_from_cache(uri)
        if cached_response:
            return cached_response

        response = self.send_request(requests.get, uri)
        if response.status_code == 200:
            data = response.json()
            self._save_to_cache(uri, data)
            return data
        else:
            raise APIError(f'Failed to fetch data, status code: {response.status_code}')

    def get_file(self, uri):
        """Fetch file data without caching."""
        return self.send_request(requests.get, uri).content

    def send_request(self, request_method, uri, payload=None):
        """Send an HTTP request with retry logic."""
        url = self.__url + uri
        for attempt in range(self.max_retries + 1):
            headers = self._set_headers()
            try:
                response = request_method(url, headers=headers, data=payload)
                if response.status_code == 200:
                    return response
                if response.status_code == 403:
                    raise APIError('Access denied.')
                if response.status_code == 400:
                    raise APIError('Invalid data or entity not found.')
                if response.status_code == 500:
                    raise APIError('Server error.')
                if response.status_code == 404:
                    raise APIError('Entity not found.')
                time.sleep(self.backoff_factor * (2 ** attempt))
            except (requests.exceptions.Timeout, http.client.RemoteDisconnected, ConnectionResetError, requests.exceptions.ConnectionError) as e:
                self.logger.log(f"Request error: {e}", "error")
                time.sleep(self.backoff_factor * (2 ** attempt))

            if attempt == self.max_retries:
                raise APIError('Max retries reached or server error.')