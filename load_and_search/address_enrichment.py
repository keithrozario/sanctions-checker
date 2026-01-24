import google.auth
from google.auth.transport.requests import Request
import requests
import json
import hashlib
import time
import logging

class AddressEnricher:
    def __init__(self, project_id):
        self.project_id = project_id
        self.base_url = "https://addressvalidation.googleapis.com/v1:validateAddress"
        self.credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        self.session = requests.Session()

    def get_token(self):
        if not self.credentials.valid:
            self.credentials.refresh(Request())
        return self.credentials.token

    def get_address_hash(self, raw_address):
        """Returns a SHA256 hash of the normalized address string."""
        if not raw_address:
            return None
        # Normalize: lower case, strip whitespace
        normalized = raw_address.lower().strip()
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def enrich(self, raw_address):
        """Calls the Address Validation API."""
        if not raw_address:
            return None

        token = self.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": self.project_id
        }
        
        # The API is smart enough to parse single lines.
        payload = {
            "address": {
                "addressLines": [raw_address]
            }
        }

        try:
            response = self.session.post(self.base_url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                # Return dictionary, not string, for BQ JSON type
                return response.json()
            elif response.status_code == 429:
                logging.warning(f"Rate limited for address: {raw_address}. Skipping.")
                return None
            else:
                logging.error(f"API Error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            logging.error(f"Request failed for {raw_address}: {e}")
            return None