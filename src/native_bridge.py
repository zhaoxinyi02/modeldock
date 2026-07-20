"""JSON command bridge for the native macOS SwiftUI frontend."""
import json
import os
import sys
import traceback
import urllib.request
from urllib.parse import urlparse

import account_info
import codex_control
import codex_repair
import config_manager
import conversation_guard
import gateway
import restore_manager
import runtime
from constants import APP_NAME, APP_VERSION

# Frozen console helpers inherit the active Windows code page. The native
# frontends always exchange JSON as UTF-8, including Chinese model names.
for stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def _after_config_change(name):
    config_manager.ensure_builtin_model()
    config_manager.synchronize_models()
    if account_info.get_account_info()["mode_key"] == "pure_official":
        gateway.stop()
        return True
    ok = gateway.restart()
    if ok and gateway.is_responding():
        restore_manager.create_restore_point("auto", name, "配置修改后自动保存")
    return ok


def snapshot():
    # The native UI polls this command. Keep polling read-mostly instead of
    # invalidating Codex caches on every refresh.
    runtime.ensure_cli_proxy_runtime()
    config_manager.ensure_base_files()
    config_manager.ensure_builtin_model()
    config_manager.synchronize_models()
    summary = config_manager.get_summary()
    models = sorted(summary["entries"], key=lambda item: (item.get("order", 10**9), item["number"]))
    return {
        "app_name": APP_NAME,
        "version": APP_VERSION,
        "account": account_info.get_account_info(),
        "gateway": gateway.get_status(),
        "codex": codex_control.get_status(),
        "conversation": conversation_guard.get_status(),
        "provider": codex_repair.read_effective_provider_state(),
        "autostart": gateway.get_scheduled_task_state(),
        "port": config_manager.get_port(),
        "models": models,
        "restore_points": restore_manager.list_restore_points(),
    }


def _switch_mode(mode):
    if mode not in ("pure_official", "official_plus_api", "api_only"):
        raise ValueError("未知模式。")
    was_running = codex_control.is_running()
    if was_running and not codex_control.stop():
        raise RuntimeError("无法安全停止 Codex，未切换模式。")
    try:
        if mode == "pure_official":
            conversation_guard.capture_state("before-official-switch")
            restore_manager.create_restore_point("auto", "before-official-only", "切换纯官方订阅前自动保存")
            migration = conversation_guard.migrate_desktop_conversations("openai")
            ok, message = codex_repair.switch_to_official_only()
            if not ok:
                conversation_guard.restore_provider_snapshot(migration["snapshot"])
                raise RuntimeError(message)
            gateway.disable_autostart()
            gateway.stop()
            restore_manager.create_restore_point("auto", "official-only", "切换纯官方订阅后自动保存")
            return message

        runtime.ensure_all()
        config_manager.expose_display_names_to_codex()
        config_manager.synchronize_models()
        requires_auth = mode == "official_plus_api"
        if requires_auth and not account_info.get_account_info().get("gateway_logged_in"):
            imported, message = gateway.import_desktop_codex_auth()
            if not imported:
                raise RuntimeError(message)
        if not gateway.start():
            raise RuntimeError("本地网关未能启动。")
        migration = conversation_guard.migrate_desktop_conversations("cliproxyapi")
        ok, message = codex_repair.repair_codex_config(requires_auth)
        if not ok:
            conversation_guard.restore_provider_snapshot(migration["snapshot"])
            gateway.stop()
            raise RuntimeError(message)
        restore_manager.create_restore_point("auto", "codex-mode-switch", "切换登录模式后自动保存")
        return message
    finally:
        if was_running:
            codex_control.start()


def dispatch(command, payload):
    if command == "snapshot":
        return snapshot()
    if command == "fetch_models":
        base = str(payload.get("base_url") or "").strip().rstrip("/")
        key = str(payload.get("api_key") or "").strip()
        api_type = str(payload.get("api_type") or "responses")
        if not base or not key:
            raise ValueError("请先填写 API Base URL 和 API Key。")
        candidates = [base + "/models"]
        host = (urlparse(base).hostname or "").lower()
        if host == "ark.cn-beijing.volces.com":
            candidates.append("https://ark.cn-beijing.volces.com/api/v3/models")
        if api_type == "claude" and "anthropic.com" in host:
            candidates.append("https://api.anthropic.com/v1/models")
        headers = {"User-Agent": APP_NAME}
        if api_type == "claude":
            headers.update({"x-api-key": key, "anthropic-version": "2023-06-01"})
        else:
            headers["Authorization"] = "Bearer " + key
        last_error = None
        for url in dict.fromkeys(candidates):
            try:
                request = urllib.request.Request(url, headers=headers)
                data = json.loads(urllib.request.urlopen(request, timeout=20).read().decode("utf-8"))
                records = data.get("data") or data.get("models") or []
                ids = sorted({str(item.get("id") or item.get("name")) for item in records
                              if isinstance(item, dict) and (item.get("id") or item.get("name"))})
                if ids:
                    return {"models": ids}
            except Exception as error:
                last_error = error
        raise RuntimeError("该接口未返回模型列表：{}".format(last_error or "未知错误"))
    if command == "add_model":
        config_manager.add_model(**payload)
        return {"ok": _after_config_change("add-model")}
    if command == "modify_model":
        number = int(payload.pop("number"))
        config_manager.modify_model(number, **payload)
        return {"ok": _after_config_change("modify-model")}
    if command == "remove_model":
        config_manager.remove_model(int(payload["number"]))
        return {"ok": _after_config_change("remove-model")}
    if command == "move_model":
        return {"moved": config_manager.move_model(int(payload["number"]), int(payload["direction"]))}
    if command == "gateway_action":
        action = payload["action"]
        return {"ok": {"start": gateway.start, "stop": gateway.stop, "restart": gateway.restart}[action]()}
    if command == "codex_action":
        action = payload["action"]
        return {"ok": {"start": codex_control.start, "stop": codex_control.stop, "restart": codex_control.restart}[action]()}
    if command == "switch_mode":
        return {"message": _switch_mode(payload["mode"])}
    if command == "login":
        ok, message = gateway.run_codex_login(bool(payload.get("device")))
        return {"ok": ok, "message": message}
    if command == "set_port":
        config_manager.set_port(int(payload["port"]))
        return {"ok": gateway.restart() if account_info.get_account_info()["mode_key"] != "pure_official" else True}
    if command == "autostart":
        return {"ok": gateway.enable_autostart() if payload["enabled"] else gateway.disable_autostart()}
    if command == "create_restore":
        return {"path": restore_manager.create_restore_point("manual", payload.get("name"), payload.get("notes", ""))}
    if command == "restore":
        restore_manager.restore(payload["id"])
        if account_info.get_account_info()["mode_key"] == "pure_official":
            gateway.stop()
        else:
            gateway.restart()
        return {"ok": True}
    if command == "conversation_snapshot":
        conversation_guard.snapshot("manual")
        return {"ok": True}
    if command == "conversation_repair":
        was_running = codex_control.is_running()
        if was_running and not codex_control.stop():
            raise RuntimeError("无法安全停止 Codex。")
        try:
            target = "openai" if account_info.get_account_info()["mode_key"] == "pure_official" else "cliproxyapi"
            conversation_guard.migrate_desktop_conversations(target)
            conversation_guard.rebuild_visible_index()
            return {"ok": True}
        finally:
            if was_running:
                codex_control.start()
    if command == "redacted_config":
        return {"text": config_manager.get_redacted_config()}
    raise ValueError("未知命令：" + command)


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "snapshot"
    payload = {}
    raw = sys.stdin.read()
    if raw.strip():
        payload = json.loads(raw)
    try:
        result = dispatch(command, payload)
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, separators=(",", ":")))
    except Exception as error:
        print(json.dumps({
            "ok": False,
            "error": str(error),
            "detail": traceback.format_exc(limit=8),
        }, ensure_ascii=False, separators=(",", ":")))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
