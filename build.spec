# -*- mode: python ; coding: utf-8 -*-

import os
import customtkinter

block_cipher = None
base_dir = os.path.dirname(os.path.abspath(SPEC))
ctk_path = os.path.dirname(customtkinter.__file__)

a = Analysis(
    ['main.py'],
    pathex=[base_dir],
    binaries=[],
    datas=[
        ('bin', 'bin'),
        ('blood', 'blood'),
        (ctk_path, 'customtkinter'),
    ],
    hiddenimports=[
        'pycaw',
        'pycaw.pycaw',
        'comtypes',
        'psutil',
        'win32api',
        'win32con',
        'customtkinter',
        'darkdetect',
        'pystray',
        'pystray._win32',
        'PIL',
        'PIL.Image',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='HiddenDisplay',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='bin/icon.ico',
)
