# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec file for Tantra Online Farmer Macro.
Bundles the application into a standalone Windows executable.
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

added_files = [
    ('assets', 'assets'),
    ('config.json', '.'),
    ('README.md', '.'),
]

hidden_imports = [
    'cv2',
    'numpy',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'pytesseract',
    'mss',
    'pyautogui',
    'pydirectinput',
    'keyboard',
    'win32gui',
    'win32con',
    'win32process',
    'win32api',
    'tkinter',
    'tkinter.ttk',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'hashlib',
    'threading',
    'time',
    'json',
    'math',
    're',
    'area_selector',
    'auth',
    'config',
    'farmer_bot',
    'input_controller',
    'ocr_engine',
    'screen',
    'skill_controller',
    'template_matcher',
    'updater',
    'window_manager',
]

a = Analysis(
    ['gui.py'],
    pathex=['.'],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'unittest'],
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
    name='TantraFarmer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No cmd popup window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TantraFarmer',
)
