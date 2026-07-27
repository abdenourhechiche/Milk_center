# -*- mode: python -*-
# PyInstaller spec - Centre Collecte Lait
# Compatible Windows 7 32/64 bits (Python 3.8 32 bits)

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'sqlite3',
        'hashlib',
        'csv',
        'uuid',
        'src',
        'src.config',
        'src.database',
        'src.utils',
        'src.ui',
        'src.ui.login',
        'src.ui.window',
        'src.ui.modules_eleveurs',
        'src.ui.modules_ventes',
        'src.ui.modules_autres',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'PIL',
        'PyQt5',
        'PySide2',
        'django',
        'flask',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CentreCollecteLait',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='CentreCollecteLait',
)
