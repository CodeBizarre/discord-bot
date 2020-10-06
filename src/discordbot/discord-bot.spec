# -*- mode: python ; coding: utf-8 -*-
# Can be ran simply with pyinstaller --onefile discord-bot.spec
import os

block_cipher = None

# Note that the hidden import "xkcd" is required here, not entirely sure why as no other
# import had an issue
analysys = Analysis(
    ['main.py'],
    pathex=[os.path.abspath(SPECPATH)],
    binaries=[],
    datas=[("plugins/*.py", "plugins")],
    hiddenimports=[
        "core.discord_bot",
        "core.db_tools",
        "core.time_tools",
        "core.plugins.core",
        "core.plugins.plugin_manager",
        "xkcd"
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(analysys.pure, analysys.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    analysys.scripts,
    analysys.binaries,
    analysys.zipfiles,
    analysys.datas,
    [],
    name='discord-bot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True
)
