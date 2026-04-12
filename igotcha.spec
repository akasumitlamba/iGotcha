from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


project_dir = Path(SPECPATH)
icon_path = project_dir / "igotcha.ico"

hiddenimports = []
datas = []

for package_name in (
    "pyautogui",
    "mouseinfo",
    "pymsgbox",
    "pyscreeze",
    "pygetwindow",
    "pytweening",
):
    hiddenimports += collect_submodules(package_name)
    datas += collect_data_files(package_name)

datas.append((str(icon_path), "."))


a = Analysis(
    ["igotcha.py"],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name="iGotcha",
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
    icon=str(icon_path),
)
