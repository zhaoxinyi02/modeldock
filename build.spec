# -*- mode: python ; coding: utf-8 -*-
import os
src_dir = os.path.join(os.path.abspath('.'), 'src')
a = Analysis(
    [os.path.join(src_dir, 'main.py')],
    pathex=[src_dir],
    binaries=[], datas=[], hiddenimports=['yaml'],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=[], noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='CodexGatewayManager', debug=False, strip=False,
    upx=True, console=False, argv_emulation=False,
)
