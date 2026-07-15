# -*- mode: python ; coding: utf-8 -*-
import os
import sys
src_dir = os.path.join(os.path.abspath('.'), 'src')
version_ns = {}
with open(os.path.join(src_dir, 'constants.py'), encoding='utf-8') as version_file:
    exec(version_file.read(), version_ns)
app_version = version_ns['APP_VERSION'].lstrip('Vv')
runtime_name = 'cli-proxy-api.exe' if sys.platform == 'win32' else 'cli-proxy-api'
asset_runtime = os.path.join(os.path.abspath('.'), 'assets', runtime_name)
binaries = [(asset_runtime, '.')] if os.path.exists(asset_runtime) else []
datas = []
for name in ('app_icon.ico', 'app_icon.icns', 'app_icon_macos.png', 'menu_bar_iconTemplate.png', 'menu_bar_iconTemplate@2x.png', 'app_icon_dark.ico', 'app_icon_light.ico', 'app_logo_dark.png', 'app_logo_light.png', 'logo.png'):
    path = os.path.join(os.path.abspath('.'), 'assets', name)
    if os.path.exists(path):
        datas.append((path, 'assets'))
a = Analysis(
    [os.path.join(src_dir, 'main.py')],
    pathex=[src_dir],
    binaries=binaries, datas=datas, hiddenimports=['yaml'],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
if sys.platform == 'darwin':
    exe = EXE(
        pyz, a.scripts, [], exclude_binaries=True,
        name='ModelDock', debug=False, strip=False, upx=False,
        console=False, argv_emulation=False,
    )
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='ModelDock')
    app = BUNDLE(
        coll,
        name='ModelDock.app',
        icon=os.path.join(os.path.abspath('.'), 'assets', 'app_icon.icns'),
        bundle_identifier='com.modeldock.desktop',
        info_plist={
            'CFBundleDisplayName': 'ModelDock',
            'CFBundleShortVersionString': app_version,
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '12.0',
        },
    )
else:
    exe = EXE(
        pyz, a.scripts, a.binaries, a.datas, [],
        name='ModelDock', debug=False, strip=False,
        upx=True, console=False, argv_emulation=False,
        icon=os.path.join(os.path.abspath('.'), 'assets', 'app_icon.ico') if os.path.exists(os.path.join(os.path.abspath('.'), 'assets', 'app_icon.ico')) else None,
    )
