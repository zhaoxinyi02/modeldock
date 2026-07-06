import os, re, datetime
from constants import *

def check_codex_config():
    issues = []
    if not os.path.exists(CODEX_CONFIG):
        issues.append("config.toml 不存在")
        return issues, False

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

    return issues, needs_fix

def repair_codex_config():
    issues, needs_fix = check_codex_config()
    if not needs_fix:
        return True, "Codex 配置已正常，无需修复。"

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = CODEX_CONFIG + ".bak-repair-" + stamp
    with open(CODEX_CONFIG, encoding='utf-8') as f:
        old = f.read()
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
        'env_key = "CLI_PROXY_API_KEY"\n'
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
