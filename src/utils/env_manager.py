"""Модуль для роботи з токеном бота.

Токен зберігається в зашифрованому вигляді в SQLite базі даних.
"""

from typing import Optional

from src.core.database import get_secret_value, set_secret_value
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Ключ для збереження токену бота в БД
BOT_TOKEN_KEY = "bot_token"


def get_bot_token_from_env() -> Optional[str]:
    """Отримує токен бота з БД.
    
    Returns:
        Optional[str]: Токен бота або None якщо не знайдено
    """
    token = get_secret_value(BOT_TOKEN_KEY)
    if token:
        logger.debug("Токен бота отримано з БД")
        return token
    return None


def save_bot_token_to_env(token: str) -> bool:
    """Зберігає токен бота в БД.
    
    Args:
        token: Токен бота для збереження
        
    Returns:
        bool: True якщо успішно збережено, False інакше
    """
    if not token or not token.strip():
        logger.warning("Спроба зберегти порожній токен")
        return False
    
    try:
        set_secret_value(BOT_TOKEN_KEY, token.strip())
        logger.info("Токен бота збережено в БД")
        return True
    except Exception as e:
        logger.error(f"Помилка збереження токену бота: {e}")
        return False
