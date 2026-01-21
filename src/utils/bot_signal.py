"""Модуль для сигналізації про необхідність запуску бота."""

import os
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger(__name__)

SIGNAL_FILE = ".bot_start_signal"


def signal_bot_start() -> None:
    """Сигналізує про необхідність запуску бота."""
    try:
        Path(SIGNAL_FILE).touch()
        logger.debug("Сигнал запуску бота встановлено")
    except Exception as e:
        logger.error(f"Помилка встановлення сигналу: {e}")


def check_bot_start_signal() -> bool:
    """Перевіряє чи є сигнал про необхідність запуску бота.
    
    Returns:
        bool: True якщо сигнал є, False інакше
    """
    if not os.path.exists(SIGNAL_FILE):
        return False
    
    try:
        # Видаляємо сигнал після перевірки
        os.remove(SIGNAL_FILE)
        return True
    except Exception as e:
        logger.error(f"Помилка видалення сигналу: {e}")
        return False

