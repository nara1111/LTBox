import json
import sys
from pathlib import Path

APP_DIR = Path(__file__).parent.resolve()
LANG_DIR = APP_DIR / "lang"

_lang_data = {}
_fallback_data = {}

def load_lang(lang_code: str = "en"):
    global _lang_data, _fallback_data
    
    fallback_file = LANG_DIR / "en.json"
    if not _fallback_data and fallback_file.exists():
        try:
            with open(fallback_file, 'r', encoding='utf-8') as f:
                _fallback_data = json.load(f)
        except Exception as e:
            print(f"[!] Failed to load fallback language en.json: {e}", file=sys.stderr)
            _fallback_data = {}

    if lang_code == "en" or not (LANG_DIR / f"{lang_code}.json").exists():
        _lang_data = _fallback_data
    else:
        lang_file = LANG_DIR / f"{lang_code}.json"
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                _lang_data = json.load(f)
        except Exception as e:
            print(f"[!] Failed to load language {lang_code}, using fallback: {e}", file=sys.stderr)
            _lang_data = _fallback_data

def get_string(key: str, default: str = "") -> str:
    val = _lang_data.get(key, _fallback_data.get(key, default))
    if val:
        return val
    return f"[{key}]"