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

if [[ ! -f assets/app_icon.icns ]]; then
  ICONSET="$ROOT/build/ModelDock.iconset"
  python3 - "$ICONSET" <<'PY'
import shutil, sys
shutil.rmtree(sys.argv[1], ignore_errors=True)
PY
  mkdir -p "$ICONSET"
  for spec in "16 icon_16x16.png" "32 icon_16x16@2x.png" "32 icon_32x32.png" \
              "64 icon_32x32@2x.png" "128 icon_128x128.png" "256 icon_128x128@2x.png" \
              "256 icon_256x256.png" "512 icon_256x256@2x.png" "512 icon_512x512.png" \
              "1024 icon_512x512@2x.png"; do
    size="${spec%% *}"; name="${spec#* }"
    sips -z "$size" "$size" assets/app_icon_macos.png --out "$ICONSET/$name" >/dev/null
  done
  iconutil -c icns "$ICONSET" -o assets/app_icon.icns
fi

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
