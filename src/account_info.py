import glob
import json
import os
import re

from constants import *


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _codex_installed():
    local = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        os.path.join(local, "OpenAI", "Codex", "Codex.exe"),
        os.path.join(local, "codex", "Codex.exe"),
    ]
    candidates.extend(glob.glob(os.path.join(local, "Packages", "OpenAI.Codex_*")))
    candidates.extend(glob.glob(os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "WindowsApps", "OpenAI.Codex_*")))
    return any(os.path.exists(x) for x in candidates)


def _provider_mode():
    if not os.path.exists(CODEX_CONFIG):
        return "未配置"
    try:
        text = open(CODEX_CONFIG, encoding="utf-8").read()
    except Exception:
        return "未知"
    if 'model_provider = "cliproxyapi"' in text and "requires_openai_auth = true" in text:
        return "官方登录 + 第三方模型"
    if 'model_provider = "cliproxyapi"' in text and "requires_openai_auth = false" in text:
        return "API 登录 + 第三方模型"
    if 'model_provider = "cliproxyapi"' in text:
        return "第三方模型网关"
    return "官方默认配置"


def _third_party_count():
    try:
        import config_manager
        entries = config_manager.collect_entries(config_manager.load_config())
        return len([x for x in entries if not x.get("built_in")])
    except Exception:
        return 0


def get_account_info():
    installed = _codex_installed()
    files = glob.glob(os.path.join(AUTH_DIR, "codex-*.json"))
    auth_json = _read_json(os.path.join(CODEX_HOME, "auth.json"))
    best = {}
    for path in files:
        data = _read_json(path)
        if data and not data.get("disabled"):
            best = data
            best["_path"] = path
            break
    email = best.get("email") or ((auth_json.get("tokens") or {}).get("id_token_email") if isinstance(auth_json.get("tokens"), dict) else "")
    if not email and best.get("_path"):
        m = re.search(r"codex-(.*?)-(free|plus|pro|team|enterprise)\.json$", os.path.basename(best["_path"]), re.I)
        if m:
            email = m.group(1)
    plan = ""
    if best.get("_path"):
        m = re.search(r"-(free|plus|pro|team|enterprise)\.json$", os.path.basename(best["_path"]), re.I)
        if m:
            plan = m.group(1).capitalize()
    if not plan:
        plan = best.get("plan") or best.get("plan_type") or "未知"
    logged_in = bool(best or auth_json)
    mode = "未安装" if not installed else ("未登录" if not logged_in else _provider_mode())
    return {
        "installed": installed,
        "logged_in": logged_in,
        "email": email or "未读取到",
        "plan": plan,
        "expired": best.get("expired") or "未知",
        "account_id": best.get("account_id") or auth_json.get("account_id") or "未知",
        "mode": mode,
        "third_party_count": _third_party_count(),
        "usage": "本地文件未提供套餐用量",
    }
