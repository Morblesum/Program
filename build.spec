# TOPCON眼科数据管理系统 - PyInstaller打包配置
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# 自动收集所有子模块（避免遗漏）
streamlit_hidden = collect_submodules('streamlit')
watchdog_hidden = collect_submodules('watchdog')
starlette_hidden = collect_submodules('starlette')

hiddenimports = (
    streamlit_hidden +
    watchdog_hidden +
    starlette_hidden +
    [
        'openpyxl',
        'lxml',
        'lxml.etree',
        'yaml',
        'pydantic',
        'pydantic_core',
        'uvicorn',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'sqlalchemy',
        'sqlalchemy.orm',
        'sqlalchemy.ext.declarative',
        'sqlalchemy.dialects.sqlite',
        'pandas',
        'fastapi',
        'fastapi.middleware.cors',
    ]
)

a = Analysis(
    ['app/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('config.yaml', '.'),
        ('app/streamlit_app.py', 'app'),
        ('streamlit_static.zip', '.'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'jinja2',
        'PIL',
        'pytest',
        'unittest',
        'xmlrpc',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TOPCON眼科数据管理系统',
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
    version=None,
    icon=None,
)
