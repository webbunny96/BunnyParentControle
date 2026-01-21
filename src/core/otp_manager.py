"""Модуль для управління OTP кодами та їх періодичного оновлення."""

import secrets
import threading
import time
from typing import Callable, Optional

from src.core.config import load_config, save_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Глобальна змінна для зберігання callback функцій для сповіщення про зміну OTP
_otp_change_callbacks: list[Callable[[str], None]] = []

# Lock для синхронізації
_otp_lock = threading.Lock()

# Таймер для оновлення OTP
_otp_timer: Optional[threading.Timer] = None

# Час останнього оновлення OTP
_last_otp_update_time: Optional[float] = None

# Інтервал оновлення OTP (10 хвилин = 600 секунд)
OTP_UPDATE_INTERVAL = 600  # 10 хвилин


def generate_new_otp() -> str:
    """Генерує новий OTP код.
    
    Returns:
        str: Новий OTP код (8 символів, великі літери та цифри)
    """
    return secrets.token_hex(4).upper()


def update_otp() -> str:
    """Оновлює OTP код в конфігурації.
    
    Returns:
        str: Новий OTP код
    """
    global _last_otp_update_time
    
    with _otp_lock:
        config = load_config()
        new_otp = generate_new_otp()
        config["otp"] = new_otp
        save_config(config)
        
        # Зберігаємо час оновлення
        _last_otp_update_time = time.time()
        
        logger.info(f"OTP код оновлено: {new_otp}")
        
        # Сповіщаємо всіх підписників про зміну OTP
        for callback in _otp_change_callbacks:
            try:
                callback(new_otp)
            except Exception as e:
                logger.error(f"Помилка виклику callback для зміни OTP: {e}")
        
        return new_otp


def _schedule_otp_update() -> None:
    """Планує наступне оновлення OTP."""
    global _otp_timer
    
    # Оновлюємо OTP
    update_otp()
    
    # Плануємо наступне оновлення
    _otp_timer = threading.Timer(OTP_UPDATE_INTERVAL, _schedule_otp_update)
    _otp_timer.daemon = True
    _otp_timer.start()
    
    logger.debug(f"Наступне оновлення OTP заплановано через {OTP_UPDATE_INTERVAL} секунд")


def start_otp_updates() -> None:
    """Запускає періодичне оновлення OTP коду."""
    global _otp_timer, _last_otp_update_time
    
    with _otp_lock:
        # Зупиняємо попередній таймер якщо він існує
        if _otp_timer:
            _otp_timer.cancel()
        
        # Встановлюємо час останнього оновлення (поточний час)
        _last_otp_update_time = time.time()
        
        # Запускаємо перше оновлення через інтервал
        _otp_timer = threading.Timer(OTP_UPDATE_INTERVAL, _schedule_otp_update)
        _otp_timer.daemon = True
        _otp_timer.start()
        
        logger.info(f"Періодичне оновлення OTP запущено (інтервал: {OTP_UPDATE_INTERVAL} секунд)")


def stop_otp_updates() -> None:
    """Зупиняє періодичне оновлення OTP коду."""
    global _otp_timer
    
    with _otp_lock:
        if _otp_timer:
            _otp_timer.cancel()
            _otp_timer = None
            logger.info("Періодичне оновлення OTP зупинено")


def register_otp_change_callback(callback: Callable[[str], None]) -> None:
    """Реєструє callback функцію, яка буде викликатися при зміні OTP.
    
    Args:
        callback: Функція, яка приймає новий OTP код як аргумент
    """
    with _otp_lock:
        if callback not in _otp_change_callbacks:
            _otp_change_callbacks.append(callback)
            logger.debug(f"Зареєстровано callback для зміни OTP: {callback}")


def unregister_otp_change_callback(callback: Callable[[str], None]) -> None:
    """Видаляє callback функцію зі списку підписників.
    
    Args:
        callback: Функція для видалення
    """
    with _otp_lock:
        if callback in _otp_change_callbacks:
            _otp_change_callbacks.remove(callback)
            logger.debug(f"Видалено callback для зміни OTP: {callback}")


def get_time_until_next_update() -> int:
    """Повертає кількість секунд до наступного оновлення OTP.
    
    Returns:
        int: Кількість секунд до наступного оновлення (0 якщо невідомо)
    """
    global _last_otp_update_time
    
    with _otp_lock:
        if _last_otp_update_time is None:
            return 0
        
        elapsed = time.time() - _last_otp_update_time
        remaining = max(0, int(OTP_UPDATE_INTERVAL - elapsed))
        return remaining

