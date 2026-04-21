# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for building the standalone Autopilot agent binary.

Build with:
    python -m PyInstaller agent.spec --noconfirm
"""

a = Analysis(
    ['entry.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'watchdog.observers',
        'watchdog.events',
        'sentence_transformers',
        'torch',
        'numpy',
        'scipy',
        'sklearn',
        'transformers',
        'tokenizers',
        'huggingface_hub',
        'PIL',
    ],
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
    a.binaries,
    a.datas,
    [],
    name='autopilot-agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
