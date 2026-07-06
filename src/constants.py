APP_NAME = "Codex Gateway Manager"
APP_VERSION = "V2026.07.06"
GITHUB_OWNER = "zhaoxinyi02"
GITHUB_REPO = "codex-gateway-manager"

import os, tempfile
LOCAL_APPDATA = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
INSTALL_DIR = os.path.join(LOCAL_APPDATA, "CLIProxyAPI")
EXE_PATH = os.path.join(INSTALL_DIR, "cli-proxy-api.exe")
CONFIG_PATH = os.path.join(INSTALL_DIR, "config.yaml")
VBS_PATH = os.path.join(INSTALL_DIR, "start-hidden.vbs")
AUTH_DIR = os.path.join(INSTALL_DIR, "auth")

CODEX_HOME = os.path.join(os.path.expanduser("~"), ".codex")
CODEX_CONFIG = os.path.join(CODEX_HOME, "config.toml")
CATALOG_PATH = os.path.join(CODEX_HOME, "custom-model-catalog.json")

GATEWAY_KEY = "codex-local-cliproxy"
GATEWAY_DEFAULT_PORT = 8317
GATEWAY_DEFAULT_HOST = "127.0.0.1"
