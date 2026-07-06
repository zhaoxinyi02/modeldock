import os
import shutil
import sys

from constants import *


def _bundled_cli_proxy_path():
    candidates = []
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        candidates.append(os.path.join(base, "cli-proxy-api.exe"))
        candidates.append(os.path.join(base, "assets", "cli-proxy-api.exe"))
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(os.path.join(here, "assets", "cli-proxy-api.exe"))
    candidates.append(os.path.join(INSTALL_DIR, "cli-proxy-api.exe"))
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def ensure_cli_proxy_runtime():
    os.makedirs(INSTALL_DIR, exist_ok=True)
    os.makedirs(AUTH_DIR, exist_ok=True)
    bundled = _bundled_cli_proxy_path()
    if not bundled:
        return False, "未找到内置 cli-proxy-api.exe。"
    if os.path.abspath(bundled).lower() != os.path.abspath(EXE_PATH).lower():
        should_copy = not os.path.exists(EXE_PATH)
        if not should_copy:
            try:
                should_copy = os.path.getsize(EXE_PATH) != os.path.getsize(bundled)
            except OSError:
                should_copy = True
        if should_copy:
            shutil.copy2(bundled, EXE_PATH)
    return os.path.exists(EXE_PATH), EXE_PATH


def ensure_all():
    ok, msg = ensure_cli_proxy_runtime()
    if not ok:
        return False, msg
    from config_manager import ensure_base_files, ensure_builtin_model
    ensure_base_files()
    ensure_builtin_model()
    return True, "运行时已就绪。"
