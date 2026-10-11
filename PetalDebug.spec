# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:/Petal/ui/petal_ui.py'],
    pathex=['D:/Petal/engine', 'D:/Petal/tools', 'D:/Petal'],
    binaries=[],
    datas=[('D:/Petal/ui/qml/Main.qml', 'qml')],
    hiddenimports=['petal_router', 'windows_tool', 'shared_llm'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PetalDebug',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['D:/Petal/petal.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PetalDebug',
)
