# -*- mode: python -*-
import os
import sys

block_cipher = None
binaries = []
dlls_dir = os.path.join(sys.base_prefix, 'DLLs')
for name in ('sqlite3.dll', '_sqlite3.pyd'):
    p = os.path.join(dlls_dir, name)
    if os.path.exists(p):
        binaries.append((p, '.'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=[],
    hiddenimports=[
        'tkinter', 'tkinter.ttk', 'tkinter.messagebox',
        'sqlite3', '_sqlite3', 'hashlib', 'csv', 'uuid',
        'src', 'src.config', 'src.database', 'src.utils',
        'src.ui', 'src.ui.login', 'src.ui.window',
        'src.ui.modules_eleveurs', 'src.ui.modules_ventes',
        'src.ui.modules_autres',
    ],
    excludes=['matplotlib', 'numpy', 'PIL', 'PyQt5'],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='CentreCollecteLait',
    debug=False,
    console=False,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    name='CentreCollecteLait',
)
