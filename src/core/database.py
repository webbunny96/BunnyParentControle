"""Модуль для роботи з SQLite базою даних.

База даних зберігає конфігурацію та чутливі дані (пароль, токен бота).
Чутливі дані шифруються перед збереженням.
"""

import sqlite3
import threading
import hashlib
import base64
from pathlib import Path
from typing import Any, Dict, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src.utils.logger import get_logger
from src.utils.path_helper import get_base_path

logger = get_logger(__name__)

# Константи
DB_FILE = "parent_control.db"
DB_VERSION = 1

# Lock для синхронізації доступу до БД
_db_lock = threading.Lock()

# Глобальна змінна для зберігання ключа шифрування
_encryption_key: Optional[bytes] = None


def _get_db_path() -> Path:
    """Повертає шлях до файлу бази даних.
    
    Returns:
        Path: Шлях до parent_control.db поруч з exe або в корені проекту
    """
    return get_base_path() / DB_FILE


def _get_encryption_key() -> bytes:
    """Генерує або повертає ключ шифрування на основі унікальних даних системи.
    
    Ключ генерується один раз і зберігається в пам'яті.
    Він заснований на шляху до exe файлу та інших унікальних даних.
    
    Returns:
        bytes: Ключ шифрування Fernet
    """
    global _encryption_key
    
    if _encryption_key is not None:
        return _encryption_key
    
    # Генеруємо ключ на основі шляху до exe та інших унікальних даних
    import sys
    import os
    
    # Використовуємо шлях до exe як salt
    if hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS'):
        # Якщо запущено як exe
        salt = str(sys.executable).encode('utf-8')
    else:
        # Якщо запущено як скрипт
        salt = str(Path(__file__).parent.parent.parent).encode('utf-8')
    
    # Додаємо унікальні дані системи
    try:
        import platform
        machine_id = platform.node().encode('utf-8')
    except:
        machine_id = b'default'
    
    # Використовуємо PBKDF2 для генерації ключа
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt[:16] + machine_id[:16],  # Комбінуємо salt
        iterations=100000,
    )
    
    # Генеруємо ключ з фіксованого seed (щоб ключ був однаковим для однієї установки)
    seed = b'parent_control_secret_key_' + salt + machine_id
    _encryption_key = base64.urlsafe_b64encode(kdf.derive(seed))
    
    return _encryption_key


def _encrypt_value(value: str) -> str:
    """Шифрує значення перед збереженням в БД.
    
    Args:
        value: Значення для шифрування
        
    Returns:
        str: Зашифроване значення (base64)
    """
    if not value:
        return ""
    
    key = _get_encryption_key()
    fernet = Fernet(key)
    encrypted = fernet.encrypt(value.encode('utf-8'))
    return base64.urlsafe_b64encode(encrypted).decode('utf-8')


def _decrypt_value(encrypted_value: str) -> str:
    """Розшифровує значення з БД.
    
    Args:
        encrypted_value: Зашифроване значення (base64)
        
    Returns:
        str: Розшифроване значення
    """
    if not encrypted_value:
        return ""
    
    try:
        key = _get_encryption_key()
        fernet = Fernet(key)
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode('utf-8'))
        decrypted = fernet.decrypt(encrypted_bytes)
        return decrypted.decode('utf-8')
    except Exception as e:
        logger.error(f"Помилка розшифрування: {e}")
        return ""


def _hash_password(password: str) -> str:
    """Хешує пароль для безпечного збереження.
    
    Args:
        password: Пароль для хешування
        
    Returns:
        str: Хеш пароля (SHA256)
    """
    if not password:
        return ""
    
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def _get_connection() -> sqlite3.Connection:
    """Створює підключення до БД.
    
    Returns:
        sqlite3.Connection: Підключення до БД
    """
    db_path = _get_db_path()
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_database() -> None:
    """Ініціалізує базу даних, створюючи необхідні таблиці."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        
        # Таблиця для звичайних конфігураційних значень
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        # Таблиця для зашифрованих чутливих даних
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS secrets (
                key TEXT PRIMARY KEY,
                encrypted_value TEXT NOT NULL
            )
        """)
        
        # Таблиця для версії БД
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS db_info (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        # Встановлюємо версію БД якщо не встановлена
        cursor.execute("""
            INSERT OR IGNORE INTO db_info (key, value) VALUES ('version', ?)
        """, (str(DB_VERSION),))
        
        conn.commit()
        logger.debug("База даних ініціалізована")
    finally:
        conn.close()


def get_config_value(key: str, default: Any = None) -> Any:
    """Отримує значення конфігурації з БД.
    
    Args:
        key: Ключ конфігурації
        default: Значення за замовчуванням якщо ключ не знайдено
        
    Returns:
        Any: Значення конфігурації або default
    """
    lock_acquired = _db_lock.acquire(timeout=5.0)
    if not lock_acquired:
        logger.error("Не вдалося отримати lock для БД за 5 секунд!")
        return default
    
    try:
        conn = _get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return row[0]
            return default
        finally:
            conn.close()
    finally:
        _db_lock.release()


def set_config_value(key: str, value: Any) -> None:
    """Встановлює значення конфігурації в БД.
    
    Args:
        key: Ключ конфігурації
        value: Значення для збереження (буде перетворено в рядок)
    """
    lock_acquired = _db_lock.acquire(timeout=5.0)
    if not lock_acquired:
        logger.error("Не вдалося отримати lock для БД за 5 секунд!")
        raise RuntimeError("Не вдалося отримати lock для БД")
    
    try:
        conn = _get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)
            """, (key, str(value)))
            conn.commit()
            logger.debug(f"Значення конфігурації '{key}' збережено")
        finally:
            conn.close()
    finally:
        _db_lock.release()


def get_secret_value(key: str, default: str = "") -> str:
    """Отримує зашифроване значення з БД.
    
    Args:
        key: Ключ секретного значення
        default: Значення за замовчуванням якщо ключ не знайдено
        
    Returns:
        str: Розшифроване значення
    """
    lock_acquired = _db_lock.acquire(timeout=5.0)
    if not lock_acquired:
        logger.error("Не вдалося отримати lock для БД за 5 секунд!")
        return default
    
    try:
        conn = _get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT encrypted_value FROM secrets WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return _decrypt_value(row[0])
            return default
        finally:
            conn.close()
    finally:
        _db_lock.release()


def set_secret_value(key: str, value: str) -> None:
    """Зберігає зашифроване значення в БД.
    
    Args:
        key: Ключ секретного значення
        value: Значення для шифрування та збереження
    """
    lock_acquired = _db_lock.acquire(timeout=5.0)
    if not lock_acquired:
        logger.error("Не вдалося отримати lock для БД за 5 секунд!")
        raise RuntimeError("Не вдалося отримати lock для БД")
    
    try:
        conn = _get_connection()
        try:
            cursor = conn.cursor()
            encrypted = _encrypt_value(value)
            cursor.execute("""
                INSERT OR REPLACE INTO secrets (key, encrypted_value) VALUES (?, ?)
            """, (key, encrypted))
            conn.commit()
            logger.debug(f"Секретне значення '{key}' збережено")
        finally:
            conn.close()
    finally:
        _db_lock.release()


def set_password_hash(key: str, password: str) -> None:
    """Зберігає хеш пароля в БД.
    
    Args:
        key: Ключ для пароля (наприклад, 'parent_password')
        password: Пароль для хешування та збереження
    """
    password_hash = _hash_password(password)
    set_secret_value(key, password_hash)


def verify_password(key: str, password: str) -> bool:
    """Перевіряє пароль проти збереженого хешу.
    
    Args:
        key: Ключ для пароля
        password: Пароль для перевірки
        
    Returns:
        bool: True якщо пароль правильний, False інакше
    """
    stored_hash = get_secret_value(key)
    if not stored_hash:
        return False
    
    password_hash = _hash_password(password)
    return stored_hash == password_hash


def get_all_config() -> Dict[str, Any]:
    """Отримує всі значення конфігурації з БД.
    
    Returns:
        Dict[str, Any]: Словник з усією конфігурацією
    """
    lock_acquired = _db_lock.acquire(timeout=5.0)
    if not lock_acquired:
        logger.error("Не вдалося отримати lock для БД за 5 секунд!")
        return {}
    
    try:
        conn = _get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM config")
            rows = cursor.fetchall()
            config = {}
            for row in rows:
                key = row[0]
                value = row[1]
                # Спробуємо перетворити в число або bool якщо можливо
                try:
                    if value.lower() == 'true':
                        config[key] = True
                    elif value.lower() == 'false':
                        config[key] = False
                    elif value.isdigit():
                        config[key] = int(value)
                    else:
                        try:
                            config[key] = float(value)
                        except ValueError:
                            config[key] = value
                except:
                    config[key] = value
            return config
        finally:
            conn.close()
    finally:
        _db_lock.release()


# Ініціалізуємо БД при імпорті модуля
_init_database()


