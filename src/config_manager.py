import os, json, copy, yaml
from constants import *
try:
    from secrets_runtime import BUILTIN_GLM_API_KEY
except Exception:
    BUILTIN_GLM_API_KEY = ""

BUILTIN_ALIASES = {BUILTIN_ALIAS, BUILTIN_MODEL_ID}

DEFAULT_MODEL_TEMPLATE = {
    "slug": "template",
    "display_name": "Template",
    "description": "Custom",
    "default_reasoning_level": "medium",
    "supported_reasoning_levels": [
        {"effort": "low", "description": "Fast responses with lighter reasoning"},
        {"effort": "medium", "description": "Balances speed and reasoning depth for everyday tasks"},
        {"effort": "high", "description": "Greater reasoning depth for complex problems"},
    ],
    "shell_type": "shell_command",
    "visibility": "list",
    "supported_in_api": True,
    "priority": 1000,
    "additional_speed_tiers": [],
    "service_tiers": [],
    "availability_nux": None,
    "upgrade": None,
}


def _builtin_key():
    return (os.environ.get(BUILTIN_KEY_ENV) or BUILTIN_GLM_API_KEY or "").strip()


def ensure_base_files():
    os.makedirs(INSTALL_DIR, exist_ok=True)
    os.makedirs(AUTH_DIR, exist_ok=True)
    os.makedirs(CODEX_HOME, exist_ok=True)
    if not os.path.exists(CONFIG_PATH):
        cfg = {
            "host": GATEWAY_DEFAULT_HOST,
            "port": GATEWAY_DEFAULT_PORT,
            "tls": {"enable": False, "cert": "", "key": ""},
            "remote-management": {
                "allow-remote": False,
                "secret-key": "",
                "disable-control-panel": True,
            },
            "auth-dir": AUTH_DIR.replace("\\", "/"),
            "api-keys": [GATEWAY_KEY],
            "debug": False,
            "logging-to-file": True,
            "usage-statistics-enabled": True,
        }
        save_config(cfg)
    else:
        cfg = load_config()
        changed = False
        if not cfg.get("api-keys"):
            cfg["api-keys"] = [GATEWAY_KEY]
            changed = True
        if not cfg.get("auth-dir"):
            cfg["auth-dir"] = AUTH_DIR.replace("\\", "/")
            changed = True
        if not cfg.get("host"):
            cfg["host"] = GATEWAY_DEFAULT_HOST
            changed = True
        if not cfg.get("port"):
            cfg["port"] = GATEWAY_DEFAULT_PORT
            changed = True
        if changed:
            save_config(cfg)
    if not os.path.exists(CATALOG_PATH):
        save_catalog({"models": []})


def _models_list(cat):
    if isinstance(cat, dict):
        return cat.setdefault("models", [])
    return cat

def load_config():
    ensure_base_files_minimal()
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False,
                      default_flow_style=False)

def load_catalog():
    ensure_base_files_minimal()
    with open(CATALOG_PATH, encoding="utf-8") as f:
        return json.load(f)


def ensure_base_files_minimal():
    os.makedirs(INSTALL_DIR, exist_ok=True)
    os.makedirs(CODEX_HOME, exist_ok=True)
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8", newline="\n") as f:
            yaml.safe_dump({
                "host": GATEWAY_DEFAULT_HOST,
                "port": GATEWAY_DEFAULT_PORT,
                "auth-dir": AUTH_DIR.replace("\\", "/"),
                "api-keys": [GATEWAY_KEY],
            }, f, allow_unicode=True, sort_keys=False)
    if not os.path.exists(CATALOG_PATH):
        with open(CATALOG_PATH, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"models": []}, f, ensure_ascii=False, separators=(",", ":"))

def save_catalog(cat):
    with open(CATALOG_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(cat, f, ensure_ascii=False, separators=(",", ":"))

def collect_entries(cfg):
    result = []
    for section in ("codex-api-key", "openai-compatibility", "claude-api-key"):
        for ei, entry in enumerate(cfg.get(section) or []):
            if not isinstance(entry, dict):
                continue
            for mi, model in enumerate(entry.get("models") or []):
                if not isinstance(model, dict):
                    continue
                alias = str(model.get("alias") or model.get("name") or "")
                if not alias:
                    continue
                has_key = bool(entry.get("api-key") or entry.get("api-key-entries"))
                result.append({
                    "number": len(result) + 1,
                    "section": section,
                    "entry_index": ei,
                    "model_index": mi,
                    "alias": alias,
                    "upstream": str(model.get("name") or ""),
                    "base_url": str(entry.get("base-url") or ""),
                    "has_key": has_key,
                    "built_in": alias in BUILTIN_ALIASES or entry.get("name") == BUILTIN_PROVIDER_ID,
                })
    return result

def get_catalog_model(catalog, alias):
    models = catalog.get("models") if isinstance(catalog, dict) else catalog
    for m in models:
        if m.get("slug") == alias:
            return m
    return {}

def get_summary():
    ensure_base_files()
    ensure_builtin_model()
    cfg = load_config()
    cat = load_catalog()
    entries = collect_entries(cfg)
    for item in entries:
        m = get_catalog_model(cat, item["alias"])
        item["display_name"] = m.get("display_name", item["alias"])
        item["provider_name"] = m.get("description", "")
        item["context_window"] = m.get("context_window")
        item["max_output_tokens"] = get_max_output(cfg, item["alias"])
    return {
        "entries": entries,
        "host": cfg.get("host") or "127.0.0.1",
        "port": cfg.get("port") or 8317,
        "auth_dir": cfg.get("auth-dir") or "",
        "api_keys_count": len(cfg.get("api-keys") or []),
    }

def get_max_output(cfg, alias):
    payload = cfg.get("payload") or {}
    for rule in payload.get("default") or []:
        for model in rule.get("models") or []:
            if isinstance(model, dict) and model.get("name") == alias:
                params = rule.get("params") or {}
                if "max_output_tokens" in params:
                    return params["max_output_tokens"]
    return None

def set_max_output(cfg, alias, value):
    params = {"max_output_tokens": int(value)} if value else None
    set_payload_params(cfg, alias, params)


def set_payload_params(cfg, alias, params):
    payload = cfg.setdefault("payload", {})
    defaults = payload.setdefault("default", [])
    defaults[:] = [
        rule for rule in defaults
        if not any(
            isinstance(model, dict) and model.get("name") == alias
            for model in rule.get("models", [])
        )
    ]
    if params:
        defaults.append({
            "models": [{"name": alias, "from-protocol": "responses"}],
            "params": params,
        })
    if not defaults:
        payload.pop("default", None)
    if not payload:
        cfg.pop("payload", None)

def get_port():
    cfg = load_config()
    return cfg.get("port") or 8317

def set_port(port):
    cfg = load_config()
    cfg["port"] = int(port)
    save_config(cfg)

def get_host():
    cfg = load_config()
    return cfg.get("host") or "127.0.0.1"

def set_host(host):
    cfg = load_config()
    cfg["host"] = host
    save_config(cfg)

def add_model(api_type, provider_name, base_url, api_key,
              model_id, alias, display_name, context_window=None,
              max_output_tokens=None, replace=False):
    cfg = load_config()
    cat = load_catalog()
    models = _models_list(cat)

    section_map = {"responses": "codex-api-key", "openai": "openai-compatibility",
                   "claude": "claude-api-key"}
    section = section_map[api_type]

    existing = [x for x in collect_entries(cfg) if x["alias"] == alias]
    if existing and not replace:
        raise ValueError(f"模型 alias {alias} 已存在。")
    if existing:
        for item in sorted(existing, key=lambda x: (x["section"], x["entry_index"], x["model_index"]), reverse=True):
            entry = cfg[item["section"]][item["entry_index"]]
            del entry["models"][item["model_index"]]
            if not entry.get("models"):
                del cfg[item["section"]][item["entry_index"]]

    provider_id = "".join(c if c.isalnum() else "_" for c in provider_name.lower()).strip("_")
    if not provider_id:
        provider_id = "custom"

    if section == "openai-compatibility":
        entry = {
            "name": provider_id,
            "base-url": base_url.rstrip("/"),
            "api-key-entries": [{"api-key": api_key}],
            "models": [{"name": model_id, "alias": alias}],
        }
    else:
        entry = {
            "api-key": api_key,
            "base-url": base_url.rstrip("/"),
            "models": [{"name": model_id, "alias": alias}],
        }
    cfg.setdefault(section, []).append(entry)

    by_slug = {m.get("slug"): m for m in models if isinstance(m, dict)}
    template = by_slug.get("gpt-5.5") or (models[0] if models else DEFAULT_MODEL_TEMPLATE)
    new_model = copy.deepcopy(template)
    new_model["slug"] = alias
    new_model["display_name"] = display_name
    new_model["description"] = provider_name
    new_model["visibility"] = "list"
    new_model["supported_in_api"] = True
    new_model["priority"] = max([int(m.get("priority", 0)) for m in models] + [999]) + 1
    new_model["additional_speed_tiers"] = []
    new_model["service_tiers"] = []
    new_model["availability_nux"] = None
    new_model["upgrade"] = None
    if context_window:
        new_model["context_window"] = int(context_window)
        new_model["max_context_window"] = int(context_window)
        new_model["effective_context_window_percent"] = 95
    else:
        new_model.pop("context_window", None)
        new_model.pop("max_context_window", None)
    models[:] = [m for m in models if m.get("slug") != alias]
    models.insert(0, new_model)

    if max_output_tokens is not None:
        set_max_output(cfg, alias, max_output_tokens)

    save_config(cfg)
    save_catalog(cat)
    return alias

def modify_model(number, base_url=None, api_key=None, upstream=None,
                 alias=None, display_name=None, provider_name=None,
                 context_window=None, max_output_tokens=None):
    cfg = load_config()
    cat = load_catalog()
    models = _models_list(cat)
    entries = collect_entries(cfg)

    for idx, item in enumerate(entries):
        item["number"] = idx + 1

    target = next((x for x in entries if x["number"] == number), None)
    if not target:
        raise ValueError("未找到指定编号。")
    if target.get("built_in"):
        raise ValueError("内置免费模型受保护，不能修改。")

    entry = cfg[target["section"]][target["entry_index"]]
    model = entry["models"][target["model_index"]]
    old_alias = target["alias"]
    new_alias = alias or old_alias

    if base_url:
        entry["base-url"] = base_url.rstrip("/")
    if api_key:
        if target["section"] == "openai-compatibility":
            entries_list = entry.setdefault("api-key-entries", [{}])
            if not entries_list:
                entries_list.append({})
            entries_list[0]["api-key"] = api_key
        else:
            entry["api-key"] = api_key
    if upstream:
        model["name"] = upstream
    if new_alias != old_alias:
        model["alias"] = new_alias
    else:
        model["alias"] = old_alias

    by_slug = {m.get("slug"): m for m in models if isinstance(m, dict)}
    cat_model = by_slug.get(old_alias)
    if not cat_model:
        template = by_slug.get("gpt-5.5") or (models[0] if models else DEFAULT_MODEL_TEMPLATE)
        cat_model = copy.deepcopy(template)
        models.insert(0, cat_model)
    if new_alias != old_alias:
        models[:] = [m for m in models if m.get("slug") != new_alias]
    cat_model["slug"] = new_alias
    if display_name:
        cat_model["display_name"] = display_name
    if provider_name:
        cat_model["description"] = provider_name
    cat_model["visibility"] = "list"
    cat_model["supported_in_api"] = True
    cat_model["availability_nux"] = None
    cat_model["upgrade"] = None
    cat_model["additional_speed_tiers"] = []
    cat_model["service_tiers"] = []

    if context_window is not None:
        if context_window:
            cat_model["context_window"] = int(context_window)
            cat_model["max_context_window"] = int(context_window)
            cat_model["effective_context_window_percent"] = 95
        else:
            cat_model.pop("context_window", None)
            cat_model.pop("max_context_window", None)

    if max_output_tokens is not None:
        set_max_output(cfg, old_alias, None)
        set_max_output(cfg, new_alias, max_output_tokens)

    save_config(cfg)
    save_catalog(cat)
    return new_alias

def remove_model(number):
    cfg = load_config()
    cat = load_catalog()
    models = _models_list(cat)
    entries = collect_entries(cfg)

    for idx, item in enumerate(entries):
        item["number"] = idx + 1

    target = next((x for x in entries if x["number"] == number), None)
    if not target:
        raise ValueError("未找到指定编号。")
    if target.get("built_in"):
        raise ValueError("内置免费模型受保护，不能删除。")

    alias = target["alias"]
    entry = cfg[target["section"]][target["entry_index"]]
    del entry["models"][target["model_index"]]
    if not entry.get("models"):
        del cfg[target["section"]][target["entry_index"]]
    models[:] = [m for m in models if m.get("slug") != alias]
    set_max_output(cfg, alias, None)
    save_config(cfg)
    save_catalog(cat)
    return alias

def get_redacted_config():
    import copy
    cfg = load_config()
    redacted = copy.deepcopy(cfg)
    for section in ("codex-api-key", "claude-api-key"):
        for entry in redacted.get(section) or []:
            if isinstance(entry, dict) and entry.get("api-key"):
                entry["api-key"] = "***REDACTED***"
    for entry in redacted.get("openai-compatibility") or []:
        if isinstance(entry, dict):
            for ke in entry.get("api-key-entries") or []:
                if isinstance(ke, dict) and ke.get("api-key"):
                    ke["api-key"] = "***REDACTED***"
    return yaml.safe_dump(redacted, allow_unicode=True, sort_keys=False,
                         default_flow_style=False)


def ensure_builtin_model():
    ensure_base_files_minimal()
    key = _builtin_key()
    if not key:
        return False
    cfg = load_config()
    cat = load_catalog()
    models = _models_list(cat)
    changed = False

    section = cfg.setdefault("openai-compatibility", [])
    entry = next((x for x in section if isinstance(x, dict) and x.get("name") == BUILTIN_PROVIDER_ID), None)
    if not entry:
        entry = {
            "name": BUILTIN_PROVIDER_ID,
            "base-url": BUILTIN_BASE_URL,
            "api-key-entries": [{"api-key": key}],
            "models": [{"name": BUILTIN_MODEL_ID, "alias": BUILTIN_ALIAS}],
        }
        section.insert(0, entry)
        changed = True
    else:
        if entry.get("base-url") != BUILTIN_BASE_URL:
            entry["base-url"] = BUILTIN_BASE_URL
            changed = True
        entries = entry.setdefault("api-key-entries", [{}])
        if not entries:
            entries.append({})
        if entries[0].get("api-key") != key:
            entries[0]["api-key"] = key
            changed = True
        model = next((m for m in entry.setdefault("models", []) if m.get("alias") == BUILTIN_ALIAS), None)
        if not model:
            entry["models"].insert(0, {"name": BUILTIN_MODEL_ID, "alias": BUILTIN_ALIAS})
            changed = True
        elif model.get("name") != BUILTIN_MODEL_ID:
            model["name"] = BUILTIN_MODEL_ID
            changed = True

    by_slug = {m.get("slug"): m for m in models if isinstance(m, dict)}
    template = by_slug.get("gpt-5.5") or (models[0] if models else DEFAULT_MODEL_TEMPLATE)
    cat_model = by_slug.get(BUILTIN_ALIAS)
    if not cat_model:
        cat_model = copy.deepcopy(template)
        models.insert(0, cat_model)
        changed = True
    cat_model.update({
        "slug": BUILTIN_ALIAS,
        "display_name": BUILTIN_DISPLAY_NAME,
        "description": BUILTIN_PROVIDER_NAME,
        "visibility": "list",
        "supported_in_api": True,
        "context_window": BUILTIN_CONTEXT_WINDOW,
        "max_context_window": BUILTIN_CONTEXT_WINDOW,
        "effective_context_window_percent": 95,
        "priority": min([int(m.get("priority", 1000)) for m in models if isinstance(m, dict)] + [1000]) - 1,
        "additional_speed_tiers": [],
        "service_tiers": [],
        "availability_nux": None,
        "upgrade": None,
        "x_gateway_builtin": True,
    })
    set_payload_params(cfg, BUILTIN_ALIAS, {
        "max_output_tokens": BUILTIN_MAX_OUTPUT_TOKENS,
        "thinking": {"type": "disabled"},
    })
    save_config(cfg)
    save_catalog(cat)
    return changed
