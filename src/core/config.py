"""Модуль для управління конфігурацією системи.

Модуль надає функції для завантаження, збереження та валідації конфігурації.
Використовує SQLite базу даних замість JSON файлу.
"""

import json
import secrets
import threading
from typing import Any, Dict, Optional

from src.core.database import (
    get_config_value, set_config_value, get_secret_value, set_secret_value,
    set_password_hash, verify_password, get_all_config
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Константи
DEFAULT_SCHEDULE = {str(i): {"start": "22:00", "end": "07:00", "enabled": False} for i in range(7)}

# Lock для синхронізації доступу до конфігурації
_config_lock = threading.Lock()


def load_config() -> Dict[str, Any]:
    """Завантажує конфігурацію з БД або створює нову за замовчуванням.
    
    Returns:
        Dict[str, Any]: Словник з конфігурацією системи
    """
    logger.info("Отримуємо lock для завантаження конфігурації...")
    lock_acquired = _config_lock.acquire(timeout=5.0)
    if not lock_acquired:
        logger.error("Не вдалося отримати lock для конфігурації за 5 секунд!")
        raise RuntimeError("Не вдалося отримати lock для конфігурації")
    
    try:
        logger.info("Lock отримано, завантажуємо конфігурацію...")
        
        # Перевіряємо чи є конфігурація в БД
        config = get_all_config()
        
        # Якщо конфігурація порожня, створюємо нову
        if not config:
            logger.info("Конфігурація не знайдена в БД, створюємо нову...")
            new_config = create_default_config()
            _save_config_internal(new_config)
            logger.info("Нова конфігурація створена")
            return new_config
        
        # Нормалізуємо конфігурацію (додаємо відсутні поля)
        logger.debug("Нормалізуємо конфігурацію...")
        config = normalize_config(config)
        
        # Перевіряємо чи потрібно зберегти оновлену конфігурацію
        # (якщо були додані відсутні поля)
        _save_config_internal(config)
        
        logger.info("Конфігурація завантажена успішно")
        return config
    finally:
        logger.info("Звільняємо lock для config...")
        _config_lock.release()


def normalize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Нормалізує конфігурацію, додаючи відсутні поля.
    
    Args:
        config: Поточна конфігурація
        
    Returns:
        Dict[str, Any]: Нормалізована конфігурація
    """
    normalized = config.copy()
    changed = False
    
    # Міграція зі старого формату (admin_id -> admin_ids)
    if "admin_id" in normalized and "admin_ids" not in normalized:
        if normalized["admin_id"]:
            normalized["admin_ids"] = [normalized["admin_id"]]
        else:
            normalized["admin_ids"] = []
        changed = True
    
    # Додаємо відсутні поля
    if "admin_ids" not in normalized:
        normalized["admin_ids"] = []
        changed = True
    
    if "otp" not in normalized or not normalized.get("otp"):
        normalized["otp"] = secrets.token_hex(4).upper()
        changed = True
    
    # parent_password зберігається окремо в secrets таблиці
    # Перевіряємо чи є хеш пароля
    if "parent_password" not in normalized:
        # Перевіряємо чи є пароль в secrets
        password_hash = get_secret_value("parent_password")
        if password_hash:
            normalized["parent_password"] = "***"  # Плейсхолдер
        else:
            normalized["parent_password"] = None
        changed = True
    
    if "time_limit_minutes" not in normalized:
        normalized["time_limit_minutes"] = 0
        changed = True
    
    if "force_block" not in normalized:
        normalized["force_block"] = False
        changed = True
    
    if "start_time" not in normalized:
        normalized["start_time"] = 0
        changed = True
    
    if "schedule" not in normalized:
        normalized["schedule"] = DEFAULT_SCHEDULE.copy()
        changed = True
    else:
        # Якщо schedule збережено як рядок JSON, парсимо його
        if isinstance(normalized["schedule"], str):
            try:
                normalized["schedule"] = json.loads(normalized["schedule"])
            except json.JSONDecodeError:
                normalized["schedule"] = DEFAULT_SCHEDULE.copy()
                changed = True
        
        # Переконуємося, що розклад має правильну структуру
        schedule = normalized["schedule"]
        for day in range(7):
            day_str = str(day)
            if day_str not in schedule:
                schedule[day_str] = {"start": "22:00", "end": "07:00", "enabled": False}
                changed = True
            else:
                day_cfg = schedule[day_str]
                if "start" not in day_cfg:
                    day_cfg["start"] = "22:00"
                    changed = True
                if "end" not in day_cfg:
                    day_cfg["end"] = "07:00"
                    changed = True
                if "enabled" not in day_cfg:
                    day_cfg["enabled"] = False
                    changed = True
    
    return normalized


def create_default_config() -> Dict[str, Any]:
    """Створює конфігурацію з дефолтними значеннями.
    
    Returns:
        Dict[str, Any]: Нова конфігурація з дефолтними значеннями
    """
    return {
        "admin_ids": [],
        "otp": secrets.token_hex(4).upper(),
        "parent_password": None,
        "time_limit_minutes": 0,
        "force_block": False,
        "start_time": 0,
        "schedule": DEFAULT_SCHEDULE.copy()
    }


def _save_config_internal(config: Dict[str, Any]) -> None:
    """Внутрішня функція для збереження конфігурації без lock.
    
    Використовується всередині функцій, які вже мають lock.
    
    Args:
        config: Словник з конфігурацією для збереження
    """
    validated_config = validate_config(config)
    
    # Зберігаємо кожне поле окремо в БД
    for key, value in validated_config.items():
        if key == "parent_password":
            # Пароль зберігається окремо в secrets таблиці
            # Якщо це плейсхолдер "***", не зберігаємо
            if value and value != "***":
                set_password_hash("parent_password", value)
            continue
        
        if key == "schedule":
            # Зберігаємо schedule як JSON рядок
            set_config_value(key, json.dumps(value))
        elif key == "admin_ids":
            # Зберігаємо список як JSON рядок
            set_config_value(key, json.dumps(value))
        else:
            # Зберігаємо інші значення як рядки
            set_config_value(key, str(value))
    
    logger.debug("Конфігурація збережена в БД")


def save_config(config: Dict[str, Any]) -> None:
    """Зберігає конфігурацію в БД.
    
    Args:
        config: Словник з конфігурацією для збереження
    """
    lock_acquired = _config_lock.acquire(timeout=5.0)
    if not lock_acquired:
        logger.error("Не вдалося отримати lock для конфігурації за 5 секунд!")
        raise RuntimeError("Не вдалося отримати lock для конфігурації")
    
    try:
        _save_config_internal(config)
    finally:
        _config_lock.release()


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Валідує конфігурацію та виправляє помилки.
    
    Args:
        config: Конфігурація для валідації
        
    Returns:
        Dict[str, Any]: Валідна конфігурація
    """
    # Нормалізуємо конфігурацію
    validated = normalize_config(config)
    
    # Перевіряємо типи
    if "admin_ids" in validated:
        if isinstance(validated["admin_ids"], str):
            try:
                validated["admin_ids"] = json.loads(validated["admin_ids"])
            except json.JSONDecodeError:
                validated["admin_ids"] = []
        elif not isinstance(validated["admin_ids"], list):
            validated["admin_ids"] = []
    
    if "otp" not in validated or not isinstance(validated["otp"], str) or len(validated["otp"]) < 4:
        validated["otp"] = secrets.token_hex(4).upper()
    
    if validated.get("parent_password") is not None:
        if not isinstance(validated["parent_password"], str) or validated["parent_password"] == "***":
            validated["parent_password"] = None
    
    if "time_limit_minutes" in validated:
        try:
            validated["time_limit_minutes"] = int(validated["time_limit_minutes"])
            if validated["time_limit_minutes"] < 0:
                validated["time_limit_minutes"] = 0
        except (ValueError, TypeError):
            validated["time_limit_minutes"] = 0
    
    if "force_block" in validated:
        if isinstance(validated["force_block"], str):
            validated["force_block"] = validated["force_block"].lower() == "true"
        elif not isinstance(validated["force_block"], bool):
            validated["force_block"] = False
    
    if "start_time" in validated:
        try:
            validated["start_time"] = float(validated["start_time"])
            if validated["start_time"] < 0:
                validated["start_time"] = 0
        except (ValueError, TypeError):
            validated["start_time"] = 0
    
    return validated


def get_config() -> Dict[str, Any]:
    """Повертає поточну конфігурацію.
    
    Returns:
        Dict[str, Any]: Поточна конфігурація
    """
    return load_config()


def check_password(password: str) -> bool:
    """Перевіряє пароль батьківського контролю.
    
    Args:
        password: Пароль для перевірки
        
    Returns:
        bool: True якщо пароль правильний, False інакше
    """
    return verify_password("parent_password", password)


def set_password(password: str) -> None:
    """Встановлює пароль батьківського контролю.
    
    Args:
        password: Новий пароль
    """
    set_password_hash("parent_password", password)
    logger.info("Пароль батьківського контролю збережено")


def has_password() -> bool:
    """Перевіряє чи встановлено пароль батьківського контролю.
    
    Returns:
        bool: True якщо пароль встановлено, False інакше
    """
    password_hash = get_secret_value("parent_password")
    return bool(password_hash)
