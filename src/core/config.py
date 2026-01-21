"""Модуль для управління конфігурацією системи.

Модуль надає функції для завантаження, збереження та валідації конфігурації.
"""

import json
import os
import secrets
from pathlib import Path
from typing import Any, Dict, Optional

# Константи
CONFIG_FILE = "config.json"
DEFAULT_SCHEDULE = {str(i): {"start": "22:00", "end": "07:00", "enabled": False} for i in range(7)}


def get_config_path() -> Path:
    """Повертає шлях до файлу конфігурації.
    
    Returns:
        Path: Шлях до config.json в корені проекту
    """
    # Повертаємо шлях відносно кореня проекту
    return Path(CONFIG_FILE)


def load_config() -> Dict[str, Any]:
    """Завантажує конфігурацію з файлу або створює нову за замовчуванням.
    
    Якщо файл не існує або містить невалідні дані, створюється нова конфігурація
    з дефолтними значеннями.
    
    Returns:
        Dict[str, Any]: Словник з конфігурацією системи
        
    Raises:
        ValueError: Якщо файл конфігурації пошкоджений і не може бути прочитаний
    """
    config_path = get_config_path()
    
    if not config_path.exists():
        # Створюємо нову конфігурацію
        new_config = create_default_config()
        save_config(new_config)
        return new_config
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        raise ValueError(f"Помилка читання конфігурації: {e}") from e
    
    # Нормалізуємо конфігурацію (додаємо відсутні поля)
    config = normalize_config(config)
    
    # Зберігаємо оновлену конфігурацію якщо були додані поля
    save_config(config)
    
    return config


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
    
    if "parent_password" not in normalized:
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


def save_config(config: Dict[str, Any]) -> None:
    """Зберігає конфігурацію у файл.
    
    Args:
        config: Словник з конфігурацією для збереження
        
    Raises:
        IOError: Якщо не вдалося записати файл
        ValueError: Якщо конфігурація невалідна
    """
    # Валідуємо конфігурацію перед збереженням
    validated_config = validate_config(config)
    
    config_path = get_config_path()
    
    # Створюємо атомарне збереження (спочатку в тимчасовий файл)
    temp_path = config_path.with_suffix('.tmp')
    
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(validated_config, f, indent=4, ensure_ascii=False)
        
        # Переміщуємо файл атомарно
        temp_path.replace(config_path)
    except IOError as e:
        # Видаляємо тимчасовий файл у разі помилки
        if temp_path.exists():
            temp_path.unlink()
        raise IOError(f"Помилка збереження конфігурації: {e}") from e


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Валідує конфігурацію та виправляє помилки.
    
    Args:
        config: Конфігурація для валідації
        
    Returns:
        Dict[str, Any]: Валідна конфігурація
        
    Raises:
        ValueError: Якщо конфігурація містить критичні помилки
    """
    # Нормалізуємо конфігурацію
    validated = normalize_config(config)
    
    # Перевіряємо типи
    if not isinstance(validated["admin_ids"], list):
        validated["admin_ids"] = []
    
    if not isinstance(validated["otp"], str) or len(validated["otp"]) < 4:
        validated["otp"] = secrets.token_hex(4).upper()
    
    if validated["parent_password"] is not None and not isinstance(validated["parent_password"], str):
        validated["parent_password"] = None
    
    if not isinstance(validated["time_limit_minutes"], (int, float)) or validated["time_limit_minutes"] < 0:
        validated["time_limit_minutes"] = 0
    
    if not isinstance(validated["force_block"], bool):
        validated["force_block"] = False
    
    if not isinstance(validated["start_time"], (int, float)) or validated["start_time"] < 0:
        validated["start_time"] = 0
    
    return validated


def get_config() -> Dict[str, Any]:
    """Повертає поточну конфігурацію (cached для продуктивності).
    
    Note:
        Це проста функція-обгортка для load_config().
        В майбутньому можна додати кешування.
        
    Returns:
        Dict[str, Any]: Поточна конфігурація
    """
    return load_config()







