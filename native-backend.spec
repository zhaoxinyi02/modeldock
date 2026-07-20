# -*- mode: python ; coding: utf-8 -*-
import os
import sys

root = os.path.abspath('.')
src = os.path.join(root, 'src')
runtime_name = 'cli-proxy-api.exe' if sys.platform == 'win32' else 'cli-proxy-api'
runtime_path = os.path.join(root, 'assets', runtime_name)
binaries = [(runtime_path, '.')] if os.path.exists(runtime_path) else []

a = Analysis(
    [os.path.join(src, 'native_bridge.py')],
    pathex=[src], binaries=binaries, datas=[], hiddenimports=['yaml'],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=['PySide6'], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name='ModelDockBackend', debug=False, strip=False, upx=False, console=True,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='ModelDockBackend')
