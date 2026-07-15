import base64
import datetime
import glob
import json
import os
import re
import sys

from constants import *


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _jwt_claims(token):
    """Decode local JWT claims without exposing or validating the credential."""
    try:
        payload = str(token or "").split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload.encode("ascii")))
    except Exception:
        return {}


def _official_auth_details(auth_json):
    tokens = auth_json.get("tokens") if isinstance(auth_json, dict) else {}
    tokens = tokens if isinstance(tokens, dict) else {}
    id_claims = _jwt_claims(tokens.get("id_token"))
    access_claims = _jwt_claims(tokens.get("access_token"))
    id_auth = id_claims.get("https://api.openai.com/auth") or {}
    access_auth = access_claims.get("https://api.openai.com/auth") or {}
    profile = access_claims.get("https://api.openai.com/profile") or {}
    email = id_claims.get("email") or profile.get("email") or tokens.get("id_token_email") or ""
    plan = id_auth.get("chatgpt_plan_type") or access_auth.get("chatgpt_plan_type") or ""
    account_id = (
        tokens.get("account_id") or auth_json.get("account_id")
        or id_auth.get("chatgpt_account_id") or access_auth.get("chatgpt_account_id") or ""
    )
    subscription_until = id_auth.get("chatgpt_subscription_active_until") or ""
    if subscription_until:
        try:
            parsed = datetime.datetime.fromisoformat(str(subscription_until).replace("Z", "+00:00"))
            subscription_until = parsed.astimezone().strftime("%Y-%m-%d")
        except Exception:
            subscription_until = str(subscription_until)
    return {
        "email": email,
        "plan": str(plan).capitalize() if plan else "",
        "account_id": account_id,
        "subscription_until": subscription_until,
    }


def _codex_installed():
    if sys.platform == "darwin":
        return any(os.path.exists(path) for path in (
            "/Applications/Codex.app",
            os.path.expanduser("~/Applications/Codex.app"),
            "/Applications/ChatGPT.app",
            os.path.expanduser("~/Applications/ChatGPT.app"),
        ))
    local = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        os.path.join(local, "OpenAI", "Codex", "Codex.exe"),
        os.path.join(local, "codex", "Codex.exe"),
    ]
    candidates.extend(glob.glob(os.path.join(local, "Packages", "OpenAI.Codex_*")))
    candidates.extend(glob.glob(os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "WindowsApps", "OpenAI.Codex_*")))
    return any(os.path.exists(x) for x in candidates)


def _codex_config_flags():
    flags = {
        "has_config": os.path.exists(CODEX_CONFIG),
        "uses_gateway": False,
        "requires_openai_auth": None,
    }
    if not os.path.exists(CODEX_CONFIG):
        return flags
    try:
        text = open(CODEX_CONFIG, encoding="utf-8").read()
    except Exception:
        return flags
    flags["uses_gateway"] = bool(re.search(r'model_provider\s*=\s*"cliproxyapi"', text))
    m = re.search(r'requires_openai_auth\s*=\s*(true|false)', text, re.I)
    if m:
        flags["requires_openai_auth"] = m.group(1).lower() == "true"
    return flags


def classify_mode(installed=None, logged_in=None):
    if installed is None:
        installed = _codex_installed()
    if logged_in is None:
        logged_in = _has_login()
    flags = _codex_config_flags()
    if not installed:
        return "not_installed", "未安装 Codex Desktop"
    if not flags["uses_gateway"]:
        return ("pure_official", "纯官方订阅") if logged_in else ("not_logged_in", "未登录")
    if flags["requires_openai_auth"] is False or not logged_in:
        return "api_only", "纯 API + 第三方模型"
    return "official_plus_api", "官方订阅 + 第三方 API"


def _has_login():
    files = glob.glob(os.path.join(AUTH_DIR, "codex-*.json"))
    auth_json = _read_json(os.path.join(CODEX_HOME, "auth.json"))
    for path in files:
        data = _read_json(path)
        if data and not data.get("disabled"):
            return True
    return bool(auth_json)


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
    official = _official_auth_details(auth_json)
    best = {}
    for path in files:
        data = _read_json(path)
        if data and not data.get("disabled"):
            best = data
            best["_path"] = path
            break
    email = best.get("email") or official["email"]
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
        plan = best.get("plan") or best.get("plan_type") or official["plan"] or "未知"
    logged_in = bool(best or auth_json)
    mode_key, mode = classify_mode(installed, logged_in)
    return {
        "installed": installed,
        "logged_in": logged_in,
        "gateway_logged_in": bool(best),
        "email": email or "未读取到",
        "plan": plan,
        # CLIProxyAPI's `expired` field is the short-lived access-token expiry,
        # not the ChatGPT subscription end date shown to the user.
        "expired": official["subscription_until"] or best.get("subscription_until") or "未知",
        "account_id": best.get("account_id") or official["account_id"] or "未知",
        "mode": mode,
        "mode_key": mode_key,
        "third_party_count": _third_party_count(),
        "usage": "本地文件未提供套餐用量",
    }
