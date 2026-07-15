import os, subprocess, time, json, urllib.request, urllib.error, datetime, signal, shlex, plistlib, re, tempfile
from constants import *
import runtime

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

def is_running():
    if not IS_WINDOWS:
        return get_pid() is not None
    try:
        r = subprocess.run(
            ["tasklist", "/fi", "imagename eq cli-proxy-api.exe", "/fo", "csv", "/nh"],
            capture_output=True, text=True, timeout=5, creationflags=NO_WINDOW)
        return "cli-proxy-api.exe" in r.stdout.lower()
    except Exception:
        return False

def get_pid():
    if not IS_WINDOWS:
        try:
            r = subprocess.run(
                ["ps", "-axo", "pid=,command="], capture_output=True, text=True, timeout=5
            )
            expected_paths = {EXE_PATH, os.path.abspath(EXE_PATH), os.path.realpath(EXE_PATH)}
            for line in r.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                pid_text, _, command = line.partition(" ")
                if any(command == path or command.startswith(path + " ") for path in expected_paths):
                    return int(pid_text)
            return None
        except Exception:
            return None
    try:
        r = subprocess.run(
            ["tasklist", "/fi", "imagename eq cli-proxy-api.exe", "/fo", "csv", "/nh"],
            capture_output=True, text=True, timeout=5, creationflags=NO_WINDOW)
        for line in r.stdout.strip().splitlines():
            parts = [p.strip('"') for p in line.split('","')]
            if parts and parts[0].lower() == "cli-proxy-api.exe":
                return int(parts[1])
        return None
    except Exception:
        return None


def get_process_info():
    pid = get_pid()
    if not pid:
        return None
    try:
        if not IS_WINDOWS:
            r = subprocess.run(
                ["ps", "-p", str(pid), "-o", "command="],
                capture_output=True, text=True, timeout=5,
            )
            command = r.stdout.strip()
            return {
                "pid": pid,
                "path": EXE_PATH if command.startswith(EXE_PATH) else "",
                "command_line": command,
            }
        ps = (
            "Get-CimInstance Win32_Process -Filter \"ProcessId=" + str(pid) + "\" | "
            "Select-Object ProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress"
        )
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=8, creationflags=NO_WINDOW)
        if r.returncode != 0 or not r.stdout.strip():
            return {"pid": pid, "path": "", "command_line": ""}
        data = json.loads(r.stdout)
        return {
            "pid": pid,
            "path": data.get("ExecutablePath") or "",
            "command_line": data.get("CommandLine") or "",
        }
    except Exception:
        return {"pid": pid, "path": "", "command_line": ""}


def _write_managed_state(pid=None):
    os.makedirs(APP_RUNTIME_DIR, exist_ok=True)
    data = {
        "pid": pid or get_pid(),
        "exe_path": EXE_PATH,
        "config_path": CONFIG_PATH,
        "started_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "managed_by": APP_NAME,
        "version": APP_VERSION,
    }
    with open(MANAGED_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_managed_running():
    info = get_process_info()
    if not info:
        return False
    try:
        with open(MANAGED_STATE_PATH, encoding="utf-8") as f:
            state = json.load(f)
        if int(state.get("pid") or 0) != int(info.get("pid") or 0):
            return False
        return os.path.abspath(state.get("exe_path") or "").lower() == os.path.abspath(info.get("path") or EXE_PATH).lower()
    except Exception:
        return False


def running_config_path():
    info = get_process_info()
    if not info:
        return None
    cmd = info.get("command_line") or ""
    if not IS_WINDOWS:
        marker = " -config "
        if marker in cmd:
            value = cmd.split(marker, 1)[1]
            # CLIProxyAPI options begin with a dash; paths may contain spaces.
            return value.split(" -", 1)[0].strip()
        return CONFIG_PATH
    try:
        parts = shlex.split(cmd, posix=not IS_WINDOWS)
    except Exception:
        parts = cmd.split()
    for i, part in enumerate(parts):
        if part.strip('"').lower() == "-config" and i + 1 < len(parts):
            return parts[i + 1].strip('"')
    return CONFIG_PATH

def get_gateway_url():
    import yaml
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        host = cfg.get("host") or "127.0.0.1"
        port = cfg.get("port") or GATEWAY_DEFAULT_PORT
        return f"http://{host}:{port}"
    except Exception:
        return f"http://{GATEWAY_DEFAULT_HOST}:{GATEWAY_DEFAULT_PORT}"

def get_gateway_key():
    try:
        import yaml
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        keys = cfg.get("api-keys") or []
        return keys[0] if keys else GATEWAY_KEY
    except Exception:
        return GATEWAY_KEY

def is_responding():
    url = get_gateway_url()
    key = get_gateway_key()
    try:
        req = urllib.request.Request(
            f"{url}/v1/models",
            headers={"Authorization": f"Bearer {key}"})
        urllib.request.urlopen(req, timeout=3)
        return True
    except Exception:
        return False


def _configured_codex_model():
    try:
        if not os.path.exists(CODEX_CONFIG):
            return ""
        text = open(CODEX_CONFIG, encoding="utf-8").read()
        import re
        match = re.search(r'(?m)^\s*model\s*=\s*"([^"]+)"', text)
        return match.group(1) if match else ""
    except Exception:
        return ""


def probe_official_subscription():
    """Verify the local gateway can make one minimal official Codex request."""
    if not is_responding():
        return False, "网关未响应。"
    # `gpt-5.3-codex-spark` may appear in the model catalogue even though
    # ChatGPT subscription accounts cannot invoke it. It is not an auth error.
    unsupported_subscription_models = {"gpt-5.3-codex-spark"}
    candidates = [_configured_codex_model(), "gpt-5.6-sol", "gpt-5.5", "gpt-5.4"]
    seen = set()
    last_error = ""
    ignored_unsupported = False
    for model in candidates:
        model = (model or "").strip()
        if not model or model in seen or model.lower() in unsupported_subscription_models:
            ignored_unsupported = ignored_unsupported or model.lower() in unsupported_subscription_models
            continue
        seen.add(model)
        body = json.dumps({
            "model": model,
            "input": "Reply with exactly: ok",
            "max_output_tokens": 16,
            "store": False,
        }).encode("utf-8")
        req = urllib.request.Request(
            get_gateway_url() + "/v1/responses",
            data=body,
            method="POST",
            headers={
                "Authorization": "Bearer " + get_gateway_key(),
                "Content-Type": "application/json",
            },
        )
        try:
            response = json.loads(urllib.request.urlopen(req, timeout=45).read().decode("utf-8"))
            if response.get("id") or response.get("output"):
                return True, "官方订阅凭据预检成功（" + model + "）。"
            last_error = "官方模型未返回有效响应。"
        except urllib.error.HTTPError as ex:
            try:
                detail = ex.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                detail = ""
            lowered = detail.lower()
            if ex.code == 400 and (
                "model is not supported when using codex with a chatgpt account" in lowered
                or "not supported" in lowered and "chatgpt account" in lowered
            ):
                ignored_unsupported = True
                continue
            last_error = "HTTP {} {}".format(ex.code, detail)
        except Exception as ex:
            last_error = str(ex)
    if ignored_unsupported and not last_error:
        return True, "官方订阅凭据已读取；已忽略订阅账户不支持的目录模型。"
    return False, "官方订阅凭据预检失败：" + (last_error or "未找到可用官方模型。")

def get_status():
    runtime.ensure_all()
    running = is_running()
    responding = is_responding() if running else False
    pid = get_pid() if running else None
    url = get_gateway_url()
    models = []
    if responding:
        key = get_gateway_key()
        try:
            req = urllib.request.Request(
                f"{url}/v1/models",
                headers={"Authorization": f"Bearer {key}"})
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            models = [m.get("id", "") for m in data.get("data", [])]
            models.sort()
        except Exception:
            pass
    return {
        "running": running,
        "responding": responding,
        "pid": pid,
        "url": url,
        "models": models,
    }

def _write_vbs():
    if not IS_WINDOWS:
        return
    os.makedirs(INSTALL_DIR, exist_ok=True)
    content = (
        "' CLIProxyAPI hidden launcher\n"
        'Set sh = CreateObject("WScript.Shell")\n'
        'sh.Run """" & "' + EXE_PATH.replace("\\", "\\\\") + '" & """ -config ""' +
        CONFIG_PATH.replace("\\", "\\\\") + '""", 0, False\n'
    )
    with open(VBS_PATH, 'w', encoding='ascii') as f:
        f.write(content)

def start():
    ok, _ = runtime.ensure_all()
    if not ok:
        return False
    if is_running():
        return True
    if not os.path.exists(EXE_PATH):
        return False
    runtime.update_cli_proxy_runtime_if_possible()
    if IS_WINDOWS:
        _write_vbs()
        subprocess.Popen(
            ["wscript.exe", VBS_PATH],
            creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        subprocess.Popen(
            [EXE_PATH, "-config", CONFIG_PATH],
            cwd=INSTALL_DIR,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    for _ in range(40):
        time.sleep(0.5)
        if is_responding():
            _write_managed_state()
            return True
    ok = is_running()
    if ok:
        _write_managed_state()
    return ok

def stop():
    pid = get_pid()
    if pid:
        try:
            if IS_WINDOWS:
                subprocess.run(["taskkill", "/pid", str(pid), "/f"],
                               capture_output=True, timeout=10, creationflags=NO_WINDOW)
            else:
                os.kill(pid, signal.SIGTERM)
                for _ in range(30):
                    if get_pid() is None:
                        break
                    time.sleep(0.1)
                if get_pid() is not None:
                    os.kill(pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass
    time.sleep(1)
    stopped = not is_running()
    if stopped:
        try:
            if os.path.exists(MANAGED_STATE_PATH):
                os.remove(MANAGED_STATE_PATH)
        except OSError:
            pass
    return stopped

def restart():
    stop()
    time.sleep(1)
    return start()

def get_scheduled_task_state():
    if not IS_WINDOWS:
        if not os.path.exists(LAUNCH_AGENT_PATH):
            return "not_found"
        r = subprocess.run(
            ["launchctl", "print", "gui/{}/{}".format(os.getuid(), LAUNCH_AGENT_LABEL)],
            capture_output=True, text=True,
        )
        return "running" if r.returncode == 0 else "ready"
    for task_name in (AUTOSTART_TASK_NAME, *LEGACY_AUTOSTART_TASK_NAMES):
        try:
            r = subprocess.run(
                ["schtasks", "/query", "/tn", task_name, "/fo", "list"],
                capture_output=True, text=True, timeout=5, creationflags=NO_WINDOW)
            if r.returncode != 0:
                continue
            if "Ready" in r.stdout:
                return "ready"
            elif "Running" in r.stdout:
                return "running"
            elif "Disabled" in r.stdout:
                return "disabled"
            return "unknown"
        except Exception:
            pass
    return "not_found"

def enable_autostart():
    runtime.ensure_all()
    if not IS_WINDOWS:
        os.makedirs(os.path.dirname(LAUNCH_AGENT_PATH), exist_ok=True)
        payload = {
            "Label": LAUNCH_AGENT_LABEL,
            "ProgramArguments": [EXE_PATH, "-config", CONFIG_PATH],
            "WorkingDirectory": INSTALL_DIR,
            "RunAtLoad": True,
            "KeepAlive": False,
            "StandardOutPath": os.path.join(INSTALL_DIR, "gateway.log"),
            "StandardErrorPath": os.path.join(INSTALL_DIR, "gateway-error.log"),
        }
        with open(LAUNCH_AGENT_PATH, "wb") as handle:
            plistlib.dump(payload, handle)
        domain = "gui/{}".format(os.getuid())
        subprocess.run(["launchctl", "bootout", domain + "/" + LAUNCH_AGENT_LABEL], capture_output=True)
        r = subprocess.run(["launchctl", "bootstrap", domain, LAUNCH_AGENT_PATH], capture_output=True)
        return r.returncode == 0
    _write_vbs()
    # Delete old task first
    for task_name in (AUTOSTART_TASK_NAME, *LEGACY_AUTOSTART_TASK_NAMES):
        subprocess.run(["schtasks", "/delete", "/tn", task_name, "/f"], capture_output=True, creationflags=NO_WINDOW)
    # Create new task with wscript + VBS (hidden window)
    cmd = (
        f'schtasks /create /tn "{AUTOSTART_TASK_NAME}" '
        f'/tr "wscript.exe \"{VBS_PATH}\"" '
        f'/sc onlogon /rl limited /f'
    )
    r = subprocess.run(cmd, capture_output=True, text=True, creationflags=NO_WINDOW)
    return r.returncode == 0

def disable_autostart():
    if not IS_WINDOWS:
        existed = os.path.exists(LAUNCH_AGENT_PATH)
        subprocess.run(
            ["launchctl", "bootout", "gui/{}/{}".format(os.getuid(), LAUNCH_AGENT_LABEL)],
            capture_output=True,
        )
        try:
            os.remove(LAUNCH_AGENT_PATH)
        except FileNotFoundError:
            pass
        return existed
    ok = False
    for task_name in (AUTOSTART_TASK_NAME, *LEGACY_AUTOSTART_TASK_NAMES):
        r = subprocess.run(
            ["schtasks", "/delete", "/tn", task_name, "/f"],
            capture_output=True, text=True, creationflags=NO_WINDOW)
        ok = ok or r.returncode == 0
    return ok


def _import_desktop_codex_auth():
    """Import the existing Codex Desktop login into CLIProxyAPI on macOS."""
    source = os.path.join(CODEX_HOME, "auth.json")
    try:
        with open(source, encoding="utf-8") as handle:
            desktop_auth = json.load(handle)
        tokens = desktop_auth.get("tokens") or {}
        required = ("id_token", "access_token", "refresh_token")
        if not isinstance(tokens, dict) or any(not tokens.get(key) for key in required):
            return False, "未找到可导入的 Codex Desktop 官方登录凭据。"

        import account_info
        import restore_manager
        details = account_info._official_auth_details(desktop_auth)
        access_claims = account_info._jwt_claims(tokens.get("access_token"))
        email = details.get("email") or "official-user"
        plan = (details.get("plan") or "unknown").lower()
        account_id = tokens.get("account_id") or details.get("account_id") or ""
        if not account_id:
            return False, "官方登录凭据缺少账户标识，无法安全导入。"

        expires_at = ""
        if access_claims.get("exp"):
            expires_at = datetime.datetime.fromtimestamp(
                int(access_claims["exp"]), datetime.timezone.utc
            ).isoformat().replace("+00:00", "Z")
        last_refresh = desktop_auth.get("last_refresh") or datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat().replace("+00:00", "Z")
        payload = {
            "id_token": tokens["id_token"],
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "account_id": account_id,
            "last_refresh": last_refresh,
            "email": email,
            "type": "codex",
            "expired": expires_at,
        }

        os.makedirs(AUTH_DIR, exist_ok=True)
        restore_manager.create_restore_point(
            kind="auto",
            name="before-official-auth-import",
            notes="导入 Codex Desktop 官方登录凭据前自动创建。",
        )
        safe_email = re.sub(r"[^A-Za-z0-9@._+-]+", "_", email)[:100]
        safe_plan = re.sub(r"[^a-z0-9_-]+", "_", plan)[:30]
        destination = os.path.join(AUTH_DIR, "codex-{}-{}.json".format(safe_email, safe_plan))
        fd, temp_path = tempfile.mkstemp(prefix=".codex-auth-", suffix=".json", dir=AUTH_DIR)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.chmod(temp_path, 0o600)
            os.replace(temp_path, destination)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        return True, "已从本机 Codex Desktop 导入官方 {} 订阅凭据，无需重新打开浏览器。".format(
            details.get("plan") or ""
        ).replace("官方  订阅", "官方订阅")
    except FileNotFoundError:
        return False, "本机尚未登录 Codex Desktop，请先在 Codex 中完成官方登录。"
    except Exception as ex:
        return False, "导入官方登录凭据失败：{}".format(ex)


def run_codex_login(device=False):
    ok, _ = runtime.ensure_all()
    if not ok:
        return False, "网关运行环境未准备完成。"
    if IS_MACOS:
        return _import_desktop_codex_auth()
    flag = "-codex-device-login" if device else "-codex-login"
    kwargs = {"cwd": INSTALL_DIR}
    if IS_WINDOWS:
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    subprocess.Popen([EXE_PATH, "-config", CONFIG_PATH, flag], **kwargs)
    return True, "已启动 Codex 官方登录流程，请按浏览器提示完成授权。"
