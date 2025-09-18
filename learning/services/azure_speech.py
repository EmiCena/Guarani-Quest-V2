# learning/services/azure_speech.py
import requests
from django.conf import settings

def issue_azure_speech_token():
    region = settings.AZURE_SPEECH_REGION
    key = settings.AZURE_SPEECH_KEY
    if not region or not key:
        raise RuntimeError("Azure Speech region/key not configured")

    url = f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    headers = {"Ocp-Apim-Subscription-Key": key, "Content-Length": "0"}
    resp = requests.post(url, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.text