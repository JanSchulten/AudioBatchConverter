# -*- mode: python ; coding: utf-8 -*-

# One-DIR build: the ffmpeg binaries (~240 MB) make a one-file exe impractical
# (it would re-extract on every launch). Distribute the dist/SampleTool folder
# as a ZIP instead.

datas = [
    ('vinyl_mixer.ico', '.'),
    ('ShareTechMono-Regular.ttf', '.'),
    ('ffmpeg', 'ffmpeg'),          # bundled ffmpeg/ffprobe/ffplay + shared dlls
]

a = Analysis(
    ['SampleTool.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    # audioop is provided by the audioop-lts backport on Python 3.13+.
    hiddenimports=['audioop'],
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
    name='SampleTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['vinyl_mixer.ico'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SampleTool',
)
