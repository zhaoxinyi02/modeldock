import os, re, datetime
from constants import *

def check_codex_config():
    issues = []
    if not os.path.exists(CODEX_CONFIG):
        issues.append("config.toml 不存在")
        return issues, True

    with open(CODEX_CONFIG, encoding='utf-8') as f:
        content = f.read()

    needs_fix = False
    has_provider = "cliproxyapi" in content
    if not has_provider:
        issues.append("config.toml 未配置 cliproxyapi provider")
        needs_fix = True

    m = re.search(r'model_provider\s*=\s*"([^"]*)"', content)
    if m:
        if m.group(1) != "cliproxyapi":
            issues.append("当前 model_provider = " + m.group(1) + "，应为 cliproxyapi")
            needs_fix = True
    else:
        issues.append("未设置 model_provider")
        needs_fix = True

    if "[model_providers.cliproxyapi]" not in content:
        issues.append("缺少 [model_providers.cliproxyapi] 配置段")
        needs_fix = True
    if "experimental_bearer_token" not in content and "env_key" in content:
        issues.append("cliproxyapi provider 使用 env_key，建议改为本地固定 token")
        needs_fix = True

    return issues, needs_fix

def repair_codex_config(requires_openai_auth=True):
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = CODEX_CONFIG + ".bak-repair-" + stamp
    os.makedirs(CODEX_HOME, exist_ok=True)
    if os.path.exists(CODEX_CONFIG):
        with open(CODEX_CONFIG, encoding='utf-8') as f:
            old = f.read()
    else:
        old = ""
    with open(backup, 'w', encoding='utf-8') as f:
        f.write(old)

    from config_manager import load_config
    cfg = load_config()
    host = cfg.get("host") or "127.0.0.1"
    port = cfg.get("port") or 8317
    gateway_url = "http://" + str(host) + ":" + str(port) + "/v1"

    provider_block = (
        '\n[model_providers.cliproxyapi]\n'
        'name = "CLIProxyAPI Local Gateway"\n'
        'base_url = "' + gateway_url + '"\n'
        'wire_api = "responses"\n'
        'experimental_bearer_token = "' + GATEWAY_KEY + '"\n'
        'requires_openai_auth = ' + ("true" if requires_openai_auth else "false") + '\n'
    )

    if "[model_providers.cliproxyapi]" not in old:
        old = old.rstrip() + "\n" + provider_block
    else:
        old = re.sub(
            r'\[model_providers\.cliproxyapi\][^\[]*?(?=\n\[|\nmodel|\Z)',
            provider_block.strip(),
            old, flags=re.DOTALL
        )

    if re.search(r'model_provider\s*=\s*"', old):
        old = re.sub(r'model_provider\s*=\s*"[^"]*"', 'model_provider = "cliproxyapi"', old)
    else:
        old = 'model_provider = "cliproxyapi"\n' + old

    with open(CODEX_CONFIG, 'w', encoding='utf-8') as f:
        f.write(old)

    return True, "修复完成，备份已保存到 " + backup


def switch_to_official_only():
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = CODEX_CONFIG + ".bak-official-" + stamp
    os.makedirs(CODEX_HOME, exist_ok=True)
    if os.path.exists(CODEX_CONFIG):
        with open(CODEX_CONFIG, encoding="utf-8") as f:
            old = f.read()
    else:
        old = ""
    with open(backup, "w", encoding="utf-8") as f:
        f.write(old)
    # Codex Desktop falls back to its official ChatGPT provider when no top-level
    # custom model_provider is selected. Keep the provider block as a dormant
    # reusable config; only remove the active selection line.
    new = re.sub(r'(?m)^\s*model_provider\s*=\s*"cliproxyapi"\s*\n?', "", old)
    with open(CODEX_CONFIG, "w", encoding="utf-8") as f:
        f.write(new)
    return True, "已切换为纯官方订阅。备份已保存到 " + backup


def read_effective_provider_state():
    if not os.path.exists(CODEX_CONFIG):
        return {"model_provider": "", "requires_openai_auth": None, "uses_gateway": False}
    text = open(CODEX_CONFIG, encoding="utf-8").read()
    m = re.search(r'(?m)^\s*model_provider\s*=\s*"([^"]*)"', text)
    r = re.search(r'requires_openai_auth\s*=\s*(true|false)', text, re.I)
    provider = m.group(1) if m else ""
    return {
        "model_provider": provider or "官方默认",
        "requires_openai_auth": (r.group(1).lower() == "true") if r else None,
        "uses_gateway": provider == "cliproxyapi",
    }
