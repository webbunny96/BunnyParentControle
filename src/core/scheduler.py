"""Модуль для роботи з розкладом блокування."""

from datetime import datetime
from typing import Dict, Any

from src.utils.logger import get_logger

logger = get_logger(__name__)


def is_within_schedule(schedule_config: Dict[str, Dict[str, Any]]) -> bool:
    """Перевіряє, чи поточний час знаходиться в межах активного розкладу.
    
    Перевіряє розклад для поточного дня тижня та визначає, чи потрібно
    заблокувати комп'ютер за розкладом.
    
    Args:
        schedule_config: Словник з розкладом на тиждень.
            Формат: {day: {"start": "HH:MM", "end": "HH:MM", "enabled": bool}}
            де day - рядок від "0" до "6" (0=понеділок, 6=неділя)
        
    Returns:
        bool: True якщо поточний час в межах активного розкладу, False інакше
        
    Example:
        >>> schedule = {
        ...     "0": {"start": "22:00", "end": "07:00", "enabled": True},
        ...     "1": {"start": "22:00", "end": "07:00", "enabled": False}
        ... }
        >>> # Якщо зараз понеділок 23:00, поверне True
        >>> # Якщо зараз вівторок 23:00, поверне False
    """
    now = datetime.now()
    day_str = str(now.weekday())  # 0=Monday, 6=Sunday
    
    # Перевіряємо чи є розклад для поточного дня
    if day_str not in schedule_config:
        logger.debug(f"Розклад для дня {day_str} не знайдено")
        return False
    
    day_cfg = schedule_config[day_str]
    
    # Перевіряємо чи розклад увімкнено
    if not day_cfg.get("enabled", False):
        logger.debug(f"Розклад для дня {day_str} вимкнено")
        return False
    
    try:
        start_time = datetime.strptime(day_cfg["start"], "%H:%M").time()
        end_time = datetime.strptime(day_cfg["end"], "%H:%M").time()
        current_time = now.time()
    except (KeyError, ValueError) as e:
        logger.error(f"Помилка парсингу часу для дня {day_str}: {e}")
        return False
    
    # Обробляємо два випадки:
    # 1. Простий випадок: start < end (наприклад, 08:00 - 22:00)
    # 2. Нічний випадок: start > end (наприклад, 22:00 - 07:00)
    
    if start_time < end_time:
        # Простий випадок: час між start та end
        is_within = start_time <= current_time <= end_time
    else:
        # Нічний випадок: час після start АБО перед end
        is_within = current_time >= start_time or current_time <= end_time
    
    if is_within:
        logger.debug(
            f"Поточний час {current_time.strftime('%H:%M')} в межах розкладу "
            f"({start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')})"
        )
    else:
        logger.debug(
            f"Поточний час {current_time.strftime('%H:%M')} поза межами розкладу "
            f"({start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')})"
        )
    
    return is_within


def get_current_day_schedule(schedule_config: Dict[str, Dict[str, Any]]) -> Dict[str, Any] | None:
    """Отримує розклад для поточного дня тижня.
    
    Args:
        schedule_config: Словник з розкладом на тиждень
        
    Returns:
        Dict[str, Any] | None: Розклад для поточного дня або None якщо не знайдено
        
    Example:
        >>> schedule = {"0": {"start": "22:00", "end": "07:00", "enabled": True}}
        >>> # Якщо зараз понеділок, поверне {"start": "22:00", "end": "07:00", "enabled": True}
    """
    now = datetime.now()
    day_str = str(now.weekday())
    
    return schedule_config.get(day_str)


def validate_time_format(time_str: str) -> bool:
    """Валідує формат часу HH:MM.
    
    Args:
        time_str: Рядок з часом у форматі HH:MM
        
    Returns:
        bool: True якщо формат валідний, False інакше
        
    Example:
        >>> validate_time_format("22:00")
        True
        >>> validate_time_format("25:00")
        False
        >>> validate_time_format("22:60")
        False
    """
    try:
        time_obj = datetime.strptime(time_str, "%H:%M").time()
        # Перевіряємо межі (вже перевірено strptime, але для впевненості)
        return 0 <= time_obj.hour < 24 and 0 <= time_obj.minute < 60
    except (ValueError, AttributeError):
        return False


def validate_schedule(schedule_config: Dict[str, Dict[str, Any]]) -> bool:
    """Валідує структуру розкладу.
    
    Перевіряє, чи розклад містить всі необхідні поля та валідні значення.
    
    Args:
        schedule_config: Словник з розкладом на тиждень
        
    Returns:
        bool: True якщо розклад валідний, False інакше
    """
    if not isinstance(schedule_config, dict):
        logger.error("Розклад має бути словником")
        return False
    
    # Перевіряємо розклад для кожного дня тижня
    for day in range(7):
        day_str = str(day)
        
        if day_str not in schedule_config:
            logger.warning(f"Розклад для дня {day_str} відсутній")
            continue
        
        day_cfg = schedule_config[day_str]
        
        if not isinstance(day_cfg, dict):
            logger.error(f"Розклад для дня {day_str} має бути словником")
            return False
        
        # Перевіряємо наявність обов'язкових полів
        required_fields = ["start", "end", "enabled"]
        for field in required_fields:
            if field not in day_cfg:
                logger.error(f"Поле '{field}' відсутнє в розкладі для дня {day_str}")
                return False
        
        # Валідуємо формат часу
        if not validate_time_format(day_cfg["start"]):
            logger.error(f"Невірний формат часу 'start' для дня {day_str}: {day_cfg['start']}")
            return False
        
        if not validate_time_format(day_cfg["end"]):
            logger.error(f"Невірний формат часу 'end' для дня {day_str}: {day_cfg['end']}")
            return False
        
        # Валідуємо поле enabled
        if not isinstance(day_cfg["enabled"], bool):
            logger.error(f"Поле 'enabled' для дня {day_str} має бути булевим")
            return False
    
    logger.debug("Розклад валідний")
    return True







