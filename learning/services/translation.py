# learning/services/translation.py
from google.cloud import translate_v2 as translate

def translate_es_to_gn(text: str) -> str:
    if not text:
        return ""
    client = translate.Client()
    result = client.translate(text, source_language="es", target_language="gn")
    return result["translatedText"]