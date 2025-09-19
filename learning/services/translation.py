# learning/services/translation.py
import os
import time
import requests

def translate_es_to_gn(text: str) -> str:
    """
    Safe translator.
    - Tries Hugging Face Inference API (OPUS es->gn) if a token is present.
    - If anything fails, returns the original text so the caller can treat it as fallback.
    """
    if not text:
        return ""
    token = os.getenv("HUGGINGFACE_API_TOKEN", "").strip()
    model = (os.getenv("HF_MODEL_PRIMARY", "Helsinki-NLP/opus-mt-es-gn")
             or "Helsinki-NLP/opus-mt-es-gn").strip().strip('"').strip("'")
    # No token → return input (frontend will prompt manual)
    if not token:
        return text

    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": "Bearer " + token}
    payload = {"inputs": text}

    # A couple retries to handle cold starts; always fail-safe
    for _ in range(2):
        try:
            r = requests.post(
                url, headers=headers, json=payload, timeout=60,
                proxies={"http": None, "https": None}  # bypass OS proxies
            )
            if r.status_code == 503:
                # model loading
                try:
                    wait_s = float(r.json().get("estimated_time", 10))
                except Exception:
                    wait_s = 10
                time.sleep(min(30, wait_s))
                continue
            if r.ok:
                try:
                    data = r.json()
                    if isinstance(data, list) and data and isinstance(data[0], dict) and "translation_text" in data[0]:
                        return data[0]["translation_text"]
                except Exception:
                    break
            # Non-OK: break and fallback
            break
        except Exception:
            break

    # Fallback: return input so the view can decide to prompt manual
    return text