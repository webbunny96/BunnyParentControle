# -*- mode: python ; coding: utf-8 -*-
# Spec файл для збірки всього проекту в один exe файл

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.example.json', '.'),
        ('config.example.md', '.'),
        # Вбудовуємо шаблони файлів в exe для ініціалізації при першому запуску
        # Ці файли будуть доступні через sys._MEIPASS
    ],
    hiddenimports=[
        # Core modules
        'src.core.config',
        'src.core.monitor',
        'src.core.scheduler',
        
        # Bot modules
        'src.bot.main',
        'src.bot.bot_runner',
        'src.bot.handlers',
        'src.bot.keyboards',
        
        # GUI modules
        'src.gui.main',
        'src.gui.gui_runner',
        'src.gui.blocking_runner',
        'src.gui.tray_app',
        'src.gui.settings_window',
        'src.gui.password_dialog',
        'src.gui.blocking_window',
        
        # Utils
        'src.utils.logger',
        'src.utils.path_helper',
        'src.utils.qr_generator',
        'src.utils.telegram_api',
        'src.utils.env_manager',
        'src.utils.bot_signal',
        
        # Database
        'src.core.database',
        'sqlite3',
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        
        # External libraries
        'aiogram',
        'aiogram.fsm',
        'aiogram.fsm.storage.memory',
        'aiohttp',
        'aiofiles',
        'qrcode',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'pystray',
        'pystray._win32',
        'schedule',
        'paramiko',
        'dotenv',
        'requests',
        'asyncio',
        'tkinter',
        'tkinter.messagebox',
        'tkinter.ttk',
        'ctypes',
        'threading',
        'subprocess',
        'argparse',
    ],
    hookspath=[],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='parent_control',
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
    icon=None,
)

