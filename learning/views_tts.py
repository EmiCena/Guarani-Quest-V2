# learning/views_tts.py
import os
import re
import hashlib
import subprocess
import shutil
from django.http import FileResponse, JsonResponse, HttpResponse
from django.conf import settings
from django.views.decorators.http import require_GET

def _pick_espeak_exe():
  return getattr(settings, "ESPEAK_NG_EXE", None) or shutil.which("espeak-ng") or shutil.which("espeak")

def _clean_text_for_tts(text: str, ensure_punct=True) -> str:
  t = re.sub(r"\s+", " ", text or "").strip()
  t = t.replace("“","\"").replace("”","\"").replace("’","'").replace("‘","'")
  if ensure_punct and t and t[-1] not in ".!?…":
    t += "."
  return t

def _cfg_for(lang: str, preset: str | None):
  cfg_all = getattr(settings, "TTS_ESPEAK_CONFIG", {}) or {}
  base = dict(cfg_all.get("default", {}))
  lang_over = (cfg_all.get("lang_overrides", {}) or {}).get(lang, {})
  base.update(lang_over)
  if preset:
    p = (cfg_all.get("presets", {}) or {}).get(preset, {})
    base.update(p.get(lang, {}))
  if not base.get("voice"):
    base["voice"] = lang
  return base

@require_GET
def tts_view(request):
  """
  /learning/api/tts/?lang=gn&text=...&preset=suave
  Devuelve WAV con espeak-ng usando presets de settings.
  """
  text = (request.GET.get("text") or "").strip()
  lang = (request.GET.get("lang") or "gn").strip().lower()
  preset = (request.GET.get("preset") or "").strip().lower() or None

  if not text:
    return HttpResponse("Missing text", status=400)
  if len(text) > 300:
    text = text[:300]

  exe = _pick_espeak_exe()
  if not exe:
    return JsonResponse({"error": "espeak-ng not found"}, status=501)

  cfg = _cfg_for(lang, preset)
  voice = cfg.get("voice") or lang
  variant = cfg.get("variant") or None
  voice_tag = f"{voice}+{variant}" if variant else voice
  cleaned = _clean_text_for_tts(text, ensure_punct=bool(cfg.get("ensure_punct", True)))

  params_sig = f"{voice_tag}:{cfg.get('speed')}:{cfg.get('pitch')}:{cfg.get('amplitude')}:{cfg.get('gap')}"
  h = hashlib.sha1(f"{params_sig}:{cleaned}".encode("utf-8")).hexdigest()[:16]

  cache_root = getattr(settings, "MEDIA_ROOT", None) or os.path.join(os.path.dirname(os.path.dirname(__file__)), "media")
  cache_dir = os.path.join(cache_root, "tts-cache")
  os.makedirs(cache_dir, exist_ok=True)
  wav_path = os.path.join(cache_dir, f"{voice_tag}-{h}.wav")

  if not os.path.exists(wav_path):
    cmd = [
      exe,
      "-v", voice_tag,
      "-s", str(cfg.get("speed", 155)),
      "-p", str(cfg.get("pitch", 45)),
      "-a", str(cfg.get("amplitude", 160)),
      "-g", str(cfg.get("gap", 6)),
      "-w", wav_path,
      cleaned,
    ]
    try:
      subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
      if voice_tag != voice:
        try:
          subprocess.run([
            exe, "-v", voice,
            "-s", str(cfg.get("speed", 155)),
            "-p", str(cfg.get("pitch", 45)),
            "-a", str(cfg.get("amplitude", 160)),
            "-g", str(cfg.get("gap", 6)),
            "-w", wav_path,
            cleaned,
          ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception:
          return JsonResponse({"error": "TTS failed"}, status=500)
      else:
        return JsonResponse({"error": "TTS failed"}, status=500)

  return FileResponse(open(wav_path, "rb"), content_type="audio/wav")