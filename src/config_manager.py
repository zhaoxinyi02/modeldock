import os, json, copy, yaml
from constants import *
try:
    from secrets_runtime import BUILTIN_GLM_API_KEY
except Exception:
    BUILTIN_GLM_API_KEY = ""

BUILTIN_ALIASES = {BUILTIN_ALIAS, BUILTIN_MODEL_ID, BUILTIN_DISPLAY_NAME}

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


def _builtin_alias_like(value):
    value = str(value or "").strip()
    return value in BUILTIN_ALIASES or value.startswith(BUILTIN_DISPLAY_NAME + " (")


def invalidate_codex_model_cache():
    """Remove Codex's disposable model catalog cache after provider changes."""
    try:
        if os.path.exists(MODELS_CACHE_PATH):
            os.remove(MODELS_CACHE_PATH)
            return True
    except OSError:
        pass
    return False


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

def load_config_from(path):
    with open(path, encoding="utf-8") as f:
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


def ensure_catalog_display_names():
    """Keep both known display-name fields in sync for Codex catalog readers."""
    cat = load_catalog()
    changed = False
    for model in _models_list(cat):
        if not isinstance(model, dict):
            continue
        display = str(model.get("display_name") or "").strip()
        if display and model.get("name") != display:
            model["name"] = display
            changed = True
    if changed:
        save_catalog(cat)
    return changed


def expose_display_names_to_codex():
    """Use configured display names as client-facing IDs.

    CLIProxyAPI currently publishes the upstream name as ``display_name`` for
    API-key models.  The new Codex desktop prefers that field, so distinct
    providers with the same upstream ID collapse visually.  Making the
    client-facing alias equal to our configured display name fixes both the
    label and the collision while the upstream ``name`` remains unchanged.
    """
    cfg = load_config()
    cat = load_catalog()
    models = _models_list(cat)
    by_slug = {str(m.get("slug")): m for m in models if isinstance(m, dict)}
    used = set()
    changes = []
    for item in collect_entries(cfg):
        old = item["alias"]
        entry = cfg[item["section"]][item["entry_index"]]
        configured_model = entry["models"][item["model_index"]]
        if item["built_in"]:
            # The bundled provider has one immutable client-facing model.  It
            # is canonicalized by ensure_builtin_model(); never rename it here
            # or every refresh would create another numbered copy.
            used.add(BUILTIN_DISPLAY_NAME.casefold())
            continue
        catalog_model = by_slug.get(old)
        if not catalog_model:
            continue
        desired = str(catalog_model.get("display_name") or old).strip() or old
        base = desired
        n = 2
        while desired.casefold() in used:
            desired = "{} ({})".format(base, n)
            n += 1
        used.add(desired.casefold())
        model_changed = False
        if configured_model.get("display-name") != desired:
            configured_model["display-name"] = desired
            model_changed = True
        if item["section"] == "codex-api-key" and configured_model.get("force-mapping") is not True:
            configured_model["force-mapping"] = True
            model_changed = True
        if desired != old:
            configured_model["alias"] = desired
            catalog_model["slug"] = desired
            catalog_model["x_legacy_alias"] = old
            set_max_output(cfg, desired, get_max_output(cfg, old))
            set_max_output(cfg, old, None)
            changes.append((old, desired))
        elif model_changed:
            changes.append((old, desired))
    if changes:
        save_config(cfg)
        save_catalog(cat)
        invalidate_codex_model_cache()
    return changes

def _merge_list_unique(target, source, key_fn):
    existing = {key_fn(x) for x in target if isinstance(x, dict)}
    changed = False
    for item in source or []:
        if not isinstance(item, dict):
            continue
        key = key_fn(item)
        if key not in existing:
            target.append(copy.deepcopy(item))
            existing.add(key)
            changed = True
    return changed

def merge_external_config(source_config_path):
    ensure_base_files()
    if not source_config_path or not os.path.exists(source_config_path):
        return False
    if os.path.abspath(source_config_path).lower() == os.path.abspath(CONFIG_PATH).lower():
        return False
    target = load_config()
    source = load_config_from(source_config_path)
    changed = False
    for section in ("codex-api-key", "openai-compatibility", "claude-api-key"):
        changed = _merge_list_unique(
            target.setdefault(section, []),
            source.get(section) or [],
            lambda x, s=section: json.dumps({
                "section": s,
                "name": x.get("name"),
                "base-url": x.get("base-url"),
                "models": x.get("models"),
            }, ensure_ascii=False, sort_keys=True),
        ) or changed
    if not target.get("api-keys") and source.get("api-keys"):
        target["api-keys"] = copy.deepcopy(source.get("api-keys"))
        changed = True
    source_defaults = (source.get("payload") or {}).get("default") or []
    if source_defaults:
        target_payload = target.setdefault("payload", {})
        target_defaults = target_payload.setdefault("default", [])
        changed = _merge_list_unique(
            target_defaults,
            source_defaults,
            lambda x: json.dumps(x.get("models") or [], ensure_ascii=False, sort_keys=True),
        ) or changed
    if changed:
        save_config(target)
    return changed

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
                if section == "openai-compatibility":
                    key_entries = entry.get("api-key-entries") or []
                    api_key = str(key_entries[0].get("api-key") or "") if key_entries and isinstance(key_entries[0], dict) else ""
                else:
                    api_key = str(entry.get("api-key") or "")
                serial_value = model.get("x-modeldock-serial")
                order_value = model.get("x-modeldock-order")
                result.append({
                    "number": int(serial_value if serial_value is not None else (len(result) + 1)),
                    "order": int(order_value if order_value is not None else (len(result) + 1)),
                    "section": section,
                    "entry_index": ei,
                    "model_index": mi,
                    "alias": alias,
                    "upstream": str(model.get("name") or ""),
                    "base_url": str(entry.get("base-url") or ""),
                    "has_key": has_key,
                    "api_key": api_key,
                    "built_in": alias in BUILTIN_ALIASES or entry.get("name") == BUILTIN_PROVIDER_ID,
                })
    return result


def _ensure_model_metadata(cfg):
    """Assign immutable display numbers and independent sortable positions."""
    changed = False
    used = set()
    next_serial = 1
    for section in ("codex-api-key", "openai-compatibility", "claude-api-key"):
        for entry in cfg.get(section) or []:
            for model in (entry.get("models") or []) if isinstance(entry, dict) else []:
                if not isinstance(model, dict):
                    continue
                built_in = _builtin_alias_like(model.get("alias")) or entry.get("name") == BUILTIN_PROVIDER_ID
                serial = 0 if built_in else model.get("x-modeldock-serial")
                try:
                    serial = int(serial)
                except (TypeError, ValueError):
                    serial = None
                if serial is None or (serial in used and serial != 0):
                    while next_serial in used:
                        next_serial += 1
                    serial = next_serial
                used.add(serial)
                next_serial = max(next_serial, serial + 1)
                if model.get("x-modeldock-serial") != serial:
                    model["x-modeldock-serial"] = serial
                    changed = True
    entries = collect_entries(cfg)
    ordered = sorted(entries, key=lambda x: (0 if x.get("built_in") else 1, x.get("order", 10**9), x["number"]))
    for order, item in enumerate(ordered):
        model = cfg[item["section"]][item["entry_index"]]["models"][item["model_index"]]
        desired = 0 if item.get("built_in") else order
        if model.get("x-modeldock-order") != desired:
            model["x-modeldock-order"] = desired
            changed = True
    return changed


def _coalesce_provider_entries(cfg):
    """CLIProxyAPI de-duplicates repeated credentials; merge their model lists first."""
    changed = False
    for section in ("codex-api-key", "claude-api-key", "openai-compatibility"):
        section_changed = False
        entries = cfg.get(section) or []
        kept = []
        grouped = {}
        for entry in entries:
            if not isinstance(entry, dict):
                kept.append(entry)
                continue
            if section == "openai-compatibility":
                credentials = json.dumps(entry.get("api-key-entries") or [], sort_keys=True)
            else:
                credentials = str(entry.get("api-key") or "")
            signature = (str(entry.get("base-url") or "").rstrip("/"), credentials)
            target = grouped.get(signature)
            if target is None or not signature[0] or not credentials:
                grouped[signature] = entry
                kept.append(entry)
                continue
            aliases = {str(m.get("alias") or m.get("name") or "") for m in target.get("models") or [] if isinstance(m, dict)}
            for model in entry.get("models") or []:
                alias = str(model.get("alias") or model.get("name") or "") if isinstance(model, dict) else ""
                if alias and alias not in aliases:
                    target.setdefault("models", []).append(model)
                    aliases.add(alias)
            changed = True
            section_changed = True
        if section_changed:
            cfg[section] = kept
    return changed


def _catalog_template(models):
    return next((m for m in models if isinstance(m, dict) and m.get("slug") == "gpt-5.5"), None) or DEFAULT_MODEL_TEMPLATE


def _reconcile_catalog(cfg, cat):
    """Backfill imported config entries and keep catalog order identical to ModelDock."""
    models = _models_list(cat)
    original_models = copy.deepcopy(models)
    by_slug = {str(m.get("slug")): m for m in models if isinstance(m, dict) and m.get("slug")}
    desired = []
    entries = sorted(collect_entries(cfg), key=lambda x: (x.get("order", 10**9), x["number"]))
    for index, item in enumerate(entries):
        model_cfg = cfg[item["section"]][item["entry_index"]]["models"][item["model_index"]]
        cat_model = by_slug.pop(item["alias"], None)
        if cat_model is None:
            cat_model = copy.deepcopy(_catalog_template(models))
        display = str(model_cfg.get("display-name") or cat_model.get("display_name") or item["alias"]).strip()
        provider = str(cat_model.get("description") or "").strip()
        if not provider:
            provider_entry = cfg[item["section"]][item["entry_index"]]
            provider = str(provider_entry.get("name") or "Custom")
        configured_context = model_cfg.get("x-modeldock-context-window")
        if configured_context and not cat_model.get("context_window"):
            cat_model["context_window"] = int(configured_context)
            cat_model["max_context_window"] = int(configured_context)
            cat_model["effective_context_window_percent"] = 95
        cat_model.update({
            "slug": item["alias"], "display_name": display, "name": display,
            "description": provider, "visibility": "list", "supported_in_api": True,
            "priority": index, "availability_nux": None, "upgrade": None,
            "additional_speed_tiers": [], "service_tiers": [],
        })
        if item.get("built_in"):
            cat_model["x_gateway_builtin"] = True
            cat_model["description"] = BUILTIN_PROVIDER_NAME
            cat_model["context_window"] = BUILTIN_CONTEXT_WINDOW
            cat_model["max_context_window"] = BUILTIN_CONTEXT_WINDOW
            cat_model["effective_context_window_percent"] = 95
        desired.append(cat_model)
    # Keep unrelated catalog entries, but always after configured gateway models.
    desired.extend(by_slug.values())
    if original_models != desired:
        models[:] = desired
        return True
    return False


def _backfill_model_metadata(cfg, cat):
    changed = False
    for item in collect_entries(cfg):
        model_cfg = cfg[item["section"]][item["entry_index"]]["models"][item["model_index"]]
        cat_model = get_catalog_model(cat, item["alias"])
        context = cat_model.get("context_window")
        if context and model_cfg.get("x-modeldock-context-window") != int(context):
            model_cfg["x-modeldock-context-window"] = int(context)
            changed = True
        display = str(cat_model.get("display_name") or item["alias"])
        if model_cfg.get("display-name") != display:
            model_cfg["display-name"] = display
            changed = True
    return changed


def synchronize_models():
    cfg = load_config()
    cat = load_catalog()
    changed_cfg = _coalesce_provider_entries(cfg)
    changed_cfg = _ensure_model_metadata(cfg) or changed_cfg
    changed_cat = _reconcile_catalog(cfg, cat)
    changed_cfg = _backfill_model_metadata(cfg, cat) or changed_cfg
    if changed_cfg:
        save_config(cfg)
    if changed_cat:
        save_catalog(cat)
    if changed_cfg or changed_cat:
        invalidate_codex_model_cache()
    return changed_cfg or changed_cat

def get_catalog_model(catalog, alias):
    models = catalog.get("models") if isinstance(catalog, dict) else catalog
    for m in models:
        if m.get("slug") == alias:
            return m
    return {}

def get_summary():
    ensure_base_files()
    ensure_builtin_model()
    synchronize_models()
    ensure_catalog_display_names()
    cfg = load_config()
    cat = load_catalog()
    entries = collect_entries(cfg)
    for item in entries:
        m = get_catalog_model(cat, item["alias"])
        configured_model = cfg[item["section"]][item["entry_index"]]["models"][item["model_index"]]
        item["display_name"] = m.get("display_name", item["alias"])
        item["provider_name"] = m.get("description", "")
        item["context_window"] = m.get("context_window") or configured_model.get("x-modeldock-context-window")
        item["max_output_tokens"] = get_max_output(cfg, item["alias"])
        item["display_number"] = item["number"]
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

    _ensure_model_metadata(cfg)
    all_entries = collect_entries(cfg)
    existing = [x for x in all_entries if x["alias"] == alias]
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

    next_serial = max([int(x["number"]) for x in all_entries if not x.get("built_in")] + [0]) + 1
    next_order = max([int(x.get("order", 0)) for x in all_entries] + [0]) + 1
    model_record = {"name": model_id, "alias": alias, "display-name": display_name,
                    "x-modeldock-serial": next_serial, "x-modeldock-order": next_order}
    if context_window:
        model_record["x-modeldock-context-window"] = int(context_window)
    if section == "openai-compatibility":
        entry = {
            "name": provider_id,
            "base-url": base_url.rstrip("/"),
            "api-key-entries": [{"api-key": api_key}],
            "models": [model_record],
        }
    else:
        entry = {
            "api-key": api_key,
            "base-url": base_url.rstrip("/"),
            "models": [model_record],
        }
    cfg.setdefault(section, []).append(entry)

    by_slug = {m.get("slug"): m for m in models if isinstance(m, dict)}
    template = by_slug.get("gpt-5.5") or (models[0] if models else DEFAULT_MODEL_TEMPLATE)
    new_model = copy.deepcopy(template)
    new_model["slug"] = alias
    new_model["display_name"] = display_name
    new_model["name"] = display_name
    new_model["description"] = provider_name
    new_model["visibility"] = "list"
    new_model["supported_in_api"] = True
    new_model["priority"] = next_order
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
    models.append(new_model)

    if max_output_tokens is not None:
        set_max_output(cfg, alias, max_output_tokens)

    save_config(cfg)
    save_catalog(cat)
    synchronize_models()
    invalidate_codex_model_cache()
    return alias

def modify_model(number, base_url=None, api_key=None, upstream=None,
                 alias=None, display_name=None, provider_name=None,
                 context_window=None, max_output_tokens=None):
    cfg = load_config()
    cat = load_catalog()
    models = _models_list(cat)
    entries = collect_entries(cfg)

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
    if display_name:
        model["display-name"] = display_name

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
        cat_model["name"] = display_name
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
            model["x-modeldock-context-window"] = int(context_window)
            cat_model["context_window"] = int(context_window)
            cat_model["max_context_window"] = int(context_window)
            cat_model["effective_context_window_percent"] = 95
        else:
            model.pop("x-modeldock-context-window", None)
            cat_model.pop("context_window", None)
            cat_model.pop("max_context_window", None)

    if max_output_tokens is not None:
        set_max_output(cfg, old_alias, None)
        set_max_output(cfg, new_alias, max_output_tokens)

    save_config(cfg)
    save_catalog(cat)
    synchronize_models()
    invalidate_codex_model_cache()
    return new_alias

def remove_model(number):
    cfg = load_config()
    cat = load_catalog()
    models = _models_list(cat)
    entries = collect_entries(cfg)

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
    synchronize_models()
    invalidate_codex_model_cache()
    return alias


def move_model(number, direction):
    cfg = load_config()
    _ensure_model_metadata(cfg)
    entries = sorted([x for x in collect_entries(cfg) if not x.get("built_in")],
                     key=lambda x: (x.get("order", 10**9), x["number"]))
    index = next((i for i, x in enumerate(entries) if x["number"] == number), None)
    if index is None:
        raise ValueError("未找到指定编号。")
    other = index + (-1 if direction < 0 else 1)
    if other < 0 or other >= len(entries):
        return False
    first, second = entries[index], entries[other]
    a = cfg[first["section"]][first["entry_index"]]["models"][first["model_index"]]
    b = cfg[second["section"]][second["entry_index"]]["models"][second["model_index"]]
    a["x-modeldock-order"], b["x-modeldock-order"] = b["x-modeldock-order"], a["x-modeldock-order"]
    save_config(cfg)
    synchronize_models()
    return True

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
    canonical_model = {
        "name": BUILTIN_MODEL_ID,
        "alias": BUILTIN_DISPLAY_NAME,
        "display-name": BUILTIN_DISPLAY_NAME,
        "x-modeldock-serial": 0,
        "x-modeldock-order": 0,
        "x-modeldock-context-window": BUILTIN_CONTEXT_WINDOW,
    }
    if entry.get("models") != [canonical_model]:
        # This provider is intentionally immutable, so any extra model here is
        # necessarily a duplicate left by an older ModelDock build.
        entry["models"] = [canonical_model]
        changed = True

    by_slug = {m.get("slug"): m for m in models if isinstance(m, dict)}
    template = by_slug.get("gpt-5.5") or (models[0] if models else DEFAULT_MODEL_TEMPLATE)
    cat_model = next((
        m for m in models if isinstance(m, dict) and (
            m.get("x_gateway_builtin") is True
            or (_builtin_alias_like(m.get("slug")) and m.get("display_name") == BUILTIN_DISPLAY_NAME)
        )
    ), None)
    if not cat_model:
        cat_model = copy.deepcopy(template)
        changed = True
    models[:] = [m for m in models if not (
        isinstance(m, dict) and (
            m.get("x_gateway_builtin") is True
            or (_builtin_alias_like(m.get("slug")) and m.get("display_name") == BUILTIN_DISPLAY_NAME)
        )
    )]
    models.insert(0, cat_model)
    cat_model.update({
        "slug": BUILTIN_DISPLAY_NAME,
        "display_name": BUILTIN_DISPLAY_NAME,
        "name": BUILTIN_DISPLAY_NAME,
        "description": BUILTIN_PROVIDER_NAME,
        "visibility": "list",
        "supported_in_api": True,
        "context_window": BUILTIN_CONTEXT_WINDOW,
        "max_context_window": BUILTIN_CONTEXT_WINDOW,
        "effective_context_window_percent": 95,
        "priority": min([
            int(m.get("priority", 1000)) for m in models
            if isinstance(m, dict) and m is not cat_model
        ] + [1000]) - 1,
        "additional_speed_tiers": [],
        "service_tiers": [],
        "availability_nux": None,
        "upgrade": None,
        "x_gateway_builtin": True,
    })
    payload = cfg.setdefault("payload", {}).setdefault("default", [])
    payload[:] = [rule for rule in payload if not any(
        _builtin_alias_like(model.get("name"))
        for model in (rule.get("models") or []) if isinstance(model, dict)
    )]
    set_payload_params(cfg, BUILTIN_DISPLAY_NAME, {
        "max_output_tokens": BUILTIN_MAX_OUTPUT_TOKENS,
        "thinking": {"type": "disabled"},
    })
    save_config(cfg)
    save_catalog(cat)
    if changed:
        invalidate_codex_model_cache()
    return changed
