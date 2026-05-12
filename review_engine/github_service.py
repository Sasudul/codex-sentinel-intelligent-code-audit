import hmac
import hashlib
import requests
import os
from django.conf import settings

def verify_github_signature(payload_body, secret_token, signature_header):
    """
    Verify that the webhook payload was sent from GitHub.
    """
    if not signature_header or not secret_token:
        return False
    
    hash_object = hmac.new(secret_token.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    
    return hmac.compare_digest(expected_signature, signature_header)

def fetch_pr_diff(repo_full_name, pr_number):
    """
    Fetch the diff for a given pull request.
    """
    # GITHUB_API_TOKEN might be in settings or os.environ
    token = getattr(settings, 'GITHUB_API_TOKEN', os.getenv('GITHUB_API_TOKEN'))
    
    url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}"
    headers = {
        "Accept": "application/vnd.github.v3.diff"
    }
    
    if token:
        headers["Authorization"] = f"token {token}"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    return None
