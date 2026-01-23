import google.auth
from google.auth.transport.requests import Request
import requests
import json
import os

def test_address_validation_oauth():
    print("Obtaining Application Default Credentials...")
    credentials, project_id = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    
    # Refresh credentials to get the token
    credentials.refresh(Request())
    token = credentials.token
    print(f"Obtained OAuth Token (truncated): {token[:10]}...")
    print(f"Project ID: {project_id}")

    # Address Validation API Endpoint
    url = "https://addressvalidation.googleapis.com/v1:validateAddress"
    
    # Simple test address
    payload = {
        "address": {
            "regionCode": "US",
            "addressLines": ["1600 Amphitheatre Parkway", "Mountain View, CA"]
        }
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_id # Explicitly bill to this project
    }
    
    print("\nCalling Address Validation API via OAuth...")
    response = requests.post(url, headers=headers, json=payload)
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("SUCCESS! API called without API Key.")
        print(json.dumps(response.json(), indent=2))
    else:
        print("FAILURE.")
        print(response.text)

if __name__ == "__main__":
    # Ensure project_id is available if default() doesn't pick it up from env
    # But usually google.auth.default() gets it from gcloud config
    try:
        test_address_validation_oauth()
    except Exception as e:
        print(f"Error: {e}")
