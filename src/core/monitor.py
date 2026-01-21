"""Модуль моніторингу стану системи та логіки блокування."""

import asyncio
import time
from typing import Dict, Any, Optional, Callable

from src.core.config import load_config
from src.core.scheduler import is_within_schedule
from src.utils.logger import get_logger

logger = get_logger(__name__)


def should_block(config: Dict[str, Any]) -> bool:
    """Визначає, чи потрібно заблокувати комп'ютер на основі конфігурації.
    
    Перевіряє три умови блокування (у порядку пріоритету):
    1. Force block (примусове блокування з бота)
    2. Time limit (перевищення ліміту часу)
    3. Schedule (поточний час в межах активного розкладу)
    
    Args:
        config: Словник з конфігурацією системи
        
    Returns:
        bool: True якщо потрібно заблокувати, False інакше
        
    Example:
        >>> config = {"force_block": True, "time_limit_minutes": 0}
        >>> should_block(config)
        True
    """
    # 1. Перевіряємо force block (найвищий пріоритет)
    if config.get("force_block", False):
        logger.debug("Блокування через force_block")
        return True
    
    # 2. Перевіряємо time limit
    time_limit_minutes = config.get("time_limit_minutes", 0)
    if time_limit_minutes > 0:
        start_time = config.get("start_time", time.time())
        elapsed_minutes = (time.time() - start_time) / 60
        
        if elapsed_minutes >= time_limit_minutes:
            logger.debug(
                f"Блокування через перевищення ліміту часу "
                f"({elapsed_minutes:.1f} / {time_limit_minutes} хв)"
            )
            return True
    
    # 3. Перевіряємо розклад (тільки якщо попередні умови не виконані)
    schedule = config.get("schedule")
    if schedule and is_within_schedule(schedule):
        logger.debug("Блокування через розклад")
        return True
    
    return False


def get_time_remaining(config: Dict[str, Any]) -> Optional[float]:
    """Отримує залишок часу до блокування через ліміт часу.
    
    Args:
        config: Словник з конфігурацією системи
        
    Returns:
        Optional[float]: Залишок часу в хвилинах або None якщо ліміт не встановлено
        
    Example:
        >>> config = {"time_limit_minutes": 60, "start_time": time.time() - 1800}
        >>> # Залишилось 30 хвилин
        >>> get_time_remaining(config)
        30.0
    """
    time_limit_minutes = config.get("time_limit_minutes", 0)
    
    if time_limit_minutes <= 0:
        return None
    
    start_time = config.get("start_time", time.time())
    elapsed_minutes = (time.time() - start_time) / 60
    remaining = max(0.0, time_limit_minutes - elapsed_minutes)
    
    return remaining


async def monitor_logic(
    check_interval: float = 10.0,
    on_block_callback: Optional[Callable] = None,
    on_unblock_callback: Optional[Callable] = None
) -> None:
    """Основна логіка моніторингу стану системи.
    
    Периодично перевіряє конфігурацію та визначає, чи потрібно заблокувати
    комп'ютер. Викликає callback функції при зміні стану.
    
    Args:
        check_interval: Інтервал перевірки в секундах (за замовчуванням 10)
        on_block_callback: Функція для виклику при потребі блокування
        on_unblock_callback: Функція для виклику при потребі розблокування
        
    Note:
        Ця функція працює в циклі до переривання (KeyboardInterrupt або подібне).
        Callback функції повинні бути async або синхронними.
    """
    logger.info(f"Моніторинг запущено (інтервал перевірки: {check_interval}с)")
    
    previous_block_state = False
    
    try:
        while True:
            config = load_config()
            current_block_state = should_block(config)
            
            # Викликаємо callback при зміні стану
            if current_block_state != previous_block_state:
                if current_block_state:
                    logger.info("Стан змінився: потрібно заблокувати")
                    if on_block_callback:
                        try:
                            if asyncio.iscoroutinefunction(on_block_callback):
                                await on_block_callback(config)
                            else:
                                on_block_callback(config)
                        except Exception as e:
                            logger.error(f"Помилка при виклику on_block_callback: {e}")
                else:
                    logger.info("Стан змінився: потрібно розблокувати")
                    if on_unblock_callback:
                        try:
                            if asyncio.iscoroutinefunction(on_unblock_callback):
                                await on_unblock_callback(config)
                            else:
                                on_unblock_callback(config)
                        except Exception as e:
                            logger.error(f"Помилка при виклику on_unblock_callback: {e}")
                
                previous_block_state = current_block_state
            
            # Логуємо статус кожні N перевірок (щоб не засмічувати логи)
            if int(time.time()) % 60 == 0:  # Кожну хвилину
                time_remaining = get_time_remaining(config)
                if time_remaining is not None:
                    logger.debug(f"Залишок часу: {time_remaining:.1f} хв")
            
            await asyncio.sleep(check_interval)
            
    except asyncio.CancelledError:
        logger.info("Моніторинг зупинено")
        raise
    except KeyboardInterrupt:
        logger.info("Моніторинг зупинено (KeyboardInterrupt)")
        raise
    except Exception as e:
        logger.error(f"Помилка в моніторингу: {e}", exc_info=True)
        raise


def get_status_info(config: Dict[str, Any]) -> Dict[str, Any]:
    """Отримує інформацію про поточний стан системи.
    
    Args:
        config: Словник з конфігурацією системи
        
    Returns:
        Dict[str, Any]: Словник з інформацією про стан:
            - blocked: bool - чи заблоковано зараз
            - force_block: bool - чи активне force block
            - time_limit: Optional[float] - ліміт часу в хвилинах
            - time_remaining: Optional[float] - залишок часу в хвилинах
            - schedule_active: bool - чи активний розклад зараз
            
    Example:
        >>> config = {"force_block": True, "time_limit_minutes": 60}
        >>> status = get_status_info(config)
        >>> status["blocked"]
        True
    """
    blocked = should_block(config)
    time_limit = config.get("time_limit_minutes", 0)
    time_limit = time_limit if time_limit > 0 else None
    time_remaining = get_time_remaining(config)
    
    schedule = config.get("schedule")
    schedule_active = schedule and is_within_schedule(schedule) if schedule else False
    
    return {
        "blocked": blocked,
        "force_block": config.get("force_block", False),
        "time_limit": time_limit,
        "time_remaining": time_remaining,
        "schedule_active": schedule_active
    }

