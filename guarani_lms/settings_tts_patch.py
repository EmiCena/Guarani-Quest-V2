# guarani_lms/settings_tts_patch.py
# Opcional: fija la ruta del ejecutable si no está en PATH
# ESPEAK_NG_EXE = r"C:\Program Files\eSpeak NG\espeak-ng.exe"

# Presets y overrides para espeak-ng
TTS_ESPEAK_CONFIG = {
    "default": {"voice": None, "speed": 155, "pitch": 45, "amplitude": 160, "gap": 6, "ensure_punct": True, "variant": None},
    "lang_overrides": {
        "gn": {"voice": "gn", "speed": 150, "pitch": 45, "amplitude": 170, "gap": 6, "variant": "f2"},
        "es": {"voice": "es", "speed": 160, "pitch": 40, "amplitude": 160, "gap": 5, "variant": None},
    },
    "presets": {
        "suave": {
            "gn": {"speed": 145, "pitch": 42, "amplitude": 165, "gap": 7, "variant": "f2"},
            "es": {"speed": 150, "pitch": 38, "amplitude": 160, "gap": 6, "variant": None},
        }
    }
}