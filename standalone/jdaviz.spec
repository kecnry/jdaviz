# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path
import os

from PyInstaller.building.build_main import Analysis
from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.osx import BUNDLE
from PyInstaller.utils.hooks import copy_metadata

import jdaviz
from jdaviz.configs import Specviz, Specviz2d, Cubeviz, Mosviz, Imviz
codesign_identity = os.environ.get("DEVELOPER_ID_APPLICATION")

# this copies over the nbextensions enabling json and the js assets
# for all the widgets
datas = [
    (Path(sys.prefix) / "share" / "jupyter", "./share/jupyter"),
    (Path(sys.prefix) / "etc" / "jupyter", "./etc/jupyter")] + \
    copy_metadata('echo') 

block_cipher = None

icon_file = '../assets/app.ico' if sys.platform == 'win32' else '../assets/app.icns' 

a = Analysis(
    ["jdaviz-cli-entrypoint.py"],
    # PyInstaller analyzes the entrypoint from the standalone directory. Add the
    # repository root explicitly so imports resolve to the source checkout and
    # hook-jdaviz.py can collect its modules and data.
    pathex=[str(Path(SPECPATH).resolve().parent.parent)],
    binaries=[],
    datas=datas,
    hiddenimports=["rich.logging", 'glue.plugins.coordinate_helpers',
                   'glue.plugins.coordinate_helpers.link_helpers', 'AppKit', 'Foundation', 'objc',
                   'jdaviz.cli', 'jdaviz.core.open_file_requests'],
    hookspath=["hooks"],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    [],
    exclude_binaries=True,
    # executable name: dist/jdaviz/jdaviz-cli
    # note: cannot be called jdaviz, because there is a directory called jdaviz
    name="jdaviz-cli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=codesign_identity,
    entitlements_file="entitlements.plist",
    icon=icon_file if sys.platform.startswith('win') else None, # Windows
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    # directory name: dist/jdaviz
    name="jdaviz",
)
# macOS Info.plist additions to register FITS document types
plist = {
    'NSPrincipalClass': 'NSApplication',
    'NSAppleScriptEnabled': True,
    'CFBundleDocumentTypes': [
        {
            'CFBundleTypeExtensions': ['fits', 'fit', 'fts', 'fitz', 'ftz', 'fz', 'asdf'],
            'CFBundleTypeName': 'FITS and ASDF files',
            'CFBundleTypeRole': 'Viewer'
        }
    ]
}

app = BUNDLE(
    exe,
    coll,
    name="Jdaviz.app",
    icon=icon_file if sys.platform.startswith('darwin') else None,
    entitlements_file="entitlements.plist",
    bundle_identifier="edu.stsci.jdaviz",
    version=jdaviz.__version__,
    argv_emulation=True,
    info_plist=plist
)