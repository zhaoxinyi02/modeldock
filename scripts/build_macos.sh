#!/bin/zsh
set -euo pipefail

ROOT="${0:A:h:h}"
cd "$ROOT"

ARCH="$(uname -m)"
case "$ARCH" in
  arm64) RELEASE_ARCH="aarch64" ;;
  x86_64) RELEASE_ARCH="amd64" ;;
  *) echo "Unsupported macOS architecture: $ARCH" >&2; exit 1 ;;
esac

python3 -m venv .venv-macos
source .venv-macos/bin/activate
python -m pip install --upgrade pip
python -m pip install --retries 10 --timeout 120 -r requirements.txt

mkdir -p assets build/macos-runtime
RUNTIME_URL="$(python - "$RELEASE_ARCH" <<'PY'
import json, sys, urllib.request
arch = sys.argv[1]
request = urllib.request.Request(
    "https://api.github.com/repos/router-for-me/CLIProxyAPI/releases/latest",
    headers={"Accept": "application/vnd.github+json", "User-Agent": "ModelDock-build"},
)
release = json.load(urllib.request.urlopen(request, timeout=30))
suffix = "_darwin_{}.tar.gz".format(arch)
for asset in release.get("assets", []):
    if asset.get("name", "").endswith(suffix):
        print(asset["browser_download_url"])
        break
else:
    raise SystemExit("CLIProxyAPI macOS runtime not found for " + arch)
PY
)"
curl --fail --location "$RUNTIME_URL" --output build/macos-runtime/cliproxy.tar.gz
tar -xzf build/macos-runtime/cliproxy.tar.gz -C build/macos-runtime
RUNTIME_BIN="$(find build/macos-runtime -type f -name cli-proxy-api | head -n 1)"
test -n "$RUNTIME_BIN"
cp "$RUNTIME_BIN" assets/cli-proxy-api
chmod +x assets/cli-proxy-api

ICONSET="build/ModelDock.iconset"
rm -rf "$ICONSET"
mkdir -p "$ICONSET"
for spec in "16 icon_16x16.png" "32 icon_16x16@2x.png" "32 icon_32x32.png" \
            "64 icon_32x32@2x.png" "128 icon_128x128.png" "256 icon_128x128@2x.png" \
            "256 icon_256x256.png" "512 icon_256x256@2x.png" "512 icon_512x512.png" \
            "1024 icon_512x512@2x.png"; do
  size="${spec%% *}"
  name="${spec#* }"
  sips -z "$size" "$size" assets/app_icon_macos.png --out "$ICONSET/$name" >/dev/null
done
iconutil -c icns "$ICONSET" -o assets/app_icon.icns

rm -rf build/ModelDock dist/ModelDock dist/ModelDock.app
pyinstaller build.spec --noconfirm

VERSION="$(python -c 'import sys; sys.path.insert(0,"src"); from constants import APP_VERSION; print(APP_VERSION)')"
DMG="dist/ModelDock_${VERSION}_macOS_${ARCH}.dmg"
STAGE="build/dmg-stage"
rm -rf "$STAGE" "$DMG"
mkdir -p "$STAGE"
cp -R dist/ModelDock.app "$STAGE/"
ln -s /Applications "$STAGE/Applications"
hdiutil create -volname "ModelDock" -srcfolder "$STAGE" -ov -format UDZO "$DMG"
echo "Built: $ROOT/$DMG"
