#!/bin/zsh
set -euo pipefail

ROOT="${0:A:h:h}"
cd "$ROOT"

ARCH="$(uname -m)"
APP="$ROOT/dist/ModelDock.app"
BACKEND_DIST="$ROOT/build/native-backend-dist"
BACKEND_WORK="$ROOT/build/native-backend-work"
SWIFT_BUILD="$ROOT/build/swift-native"
STAGE="$ROOT/build/native-dmg-stage"

if [[ ! -x .venv-macos/bin/pyinstaller ]]; then
  python3 -m venv .venv-macos
  .venv-macos/bin/pip install --upgrade pip
  .venv-macos/bin/pip install -r requirements.txt pyinstaller
fi

env -u QT_PLUGIN_PATH .venv-macos/bin/pyinstaller native-backend.spec \
  --noconfirm --distpath "$BACKEND_DIST" --workpath "$BACKEND_WORK"
swift build -c release --package-path native/macos --scratch-path "$SWIFT_BUILD"

python3 - "$APP" "$STAGE" <<'PY'
import shutil, sys
for path in sys.argv[1:]:
    shutil.rmtree(path, ignore_errors=True)
PY

mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources/Backend"
cp "$SWIFT_BUILD/release/ModelDockNative" "$APP/Contents/MacOS/ModelDock"
ditto "$BACKEND_DIST/ModelDockBackend" "$APP/Contents/Resources/Backend"
cp assets/app_icon.icns "$APP/Contents/Resources/ModelDock.icns"
cp assets/menu_bar_iconTemplate.png "$APP/Contents/Resources/"
cp assets/menu_bar_iconTemplate@2x.png "$APP/Contents/Resources/"
chmod +x "$APP/Contents/MacOS/ModelDock" "$APP/Contents/Resources/Backend/ModelDockBackend"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleDevelopmentRegion</key><string>zh_CN</string>
  <key>CFBundleDisplayName</key><string>ModelDock</string>
  <key>CFBundleExecutable</key><string>ModelDock</string>
  <key>CFBundleIconFile</key><string>ModelDock</string>
  <key>CFBundleIdentifier</key><string>com.modeldock.desktop</string>
  <key>CFBundleInfoDictionaryVersion</key><string>6.0</string>
  <key>CFBundleName</key><string>ModelDock</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>2026.07.20b</string>
  <key>CFBundleVersion</key><string>202607202</string>
  <key>LSMinimumSystemVersion</key><string>26.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSPrincipalClass</key><string>NSApplication</string>
</dict></plist>
PLIST

codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict --verbose=2 "$APP"

VERSION="$(.venv-macos/bin/python -c 'import sys; sys.path.insert(0,"src"); from constants import APP_VERSION; print(APP_VERSION)')"
DMG="$ROOT/dist/ModelDock_${VERSION}_macOS_${ARCH}.dmg"
python3 - "$DMG" <<'PY'
import os, sys
try: os.unlink(sys.argv[1])
except FileNotFoundError: pass
PY
mkdir -p "$STAGE"
ditto "$APP" "$STAGE/ModelDock.app"
ln -s /Applications "$STAGE/Applications"
hdiutil create -volname ModelDock -srcfolder "$STAGE" -ov -format UDZO "$DMG"
echo "Built: $APP"
echo "Built: $DMG"
