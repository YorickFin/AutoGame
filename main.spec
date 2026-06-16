# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

block_cipher = None

# 收集数据文件
datas = []

# 添加 data 目录
data_dir = Path('data')
if data_dir.exists():
    datas.append((str(data_dir), 'data'))

# 添加 plugins 目录
plugins_dir = Path('plugins')
if plugins_dir.exists():
    datas.append((str(plugins_dir), 'plugins'))

# 添加 frontend/dist 目录（前端构建产物）
frontend_dist_dir = Path('frontend') / 'dist'
if frontend_dist_dir.exists():
    datas.append((str(frontend_dist_dir), 'frontend/dist'))

# 添加 pyproject.toml
pyproject_file = Path('pyproject.toml')
if pyproject_file.exists():
    datas.append((str(pyproject_file), '.'))

# 添加 README.md
readme_file = Path('README.md')
if readme_file.exists():
    datas.append((str(readme_file), '.'))

# 添加 LICENSE
license_file = Path('LICENSE')
if license_file.exists():
    datas.append((str(license_file), '.'))

# 添加 update.exe（软件更新工具）
update_exe = Path('update/dist/update.exe')
if update_exe.exists():
    datas.append((str(update_exe), '.'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PIL._tkinter_finder',
        'numpy.core._multiarray_umath',
        'onnxruntime',
        'cv2',
        'autoxkit',
        'autoxkit.window',
        'autoxkit.mousekey',
        'autoxkit.match',
        'autoxkit.constants',
        'autoxkit.hook',
        'autoxkit.android',
        'autoxkit.android.adb',
        'shapely',
        'shapely.geometry',
        'shapely.geometry.polygon',
        'pyclipper',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AutoGame',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    icon=['data\\logo\\logo_tray.png'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='AutoGame',
)
