"""Модуль для роботи з Telegram Bot API."""

import os
from typing import Optional
import requests
from dotenv import load_dotenv

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Завантажуємо змінні середовища
load_dotenv()

# Константи
TELEGRAM_API_BASE_URL = "https://api.telegram.org/bot"
DEFAULT_TIMEOUT = 5


def get_bot_token() -> Optional[str]:
    """Отримує токен бота з змінних середовища.
    
    Returns:
        Optional[str]: Токен бота або None якщо не знайдено
    """
    token = os.getenv("BOT_TOKEN")
    
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        return None
    
    return token


def get_bot_username(token: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT) -> Optional[str]:
    """Отримує username Telegram бота через API.
    
    Args:
        token: Токен бота (якщо None, отримується з змінних середовища)
        timeout: Таймаут запиту в секундах
        
    Returns:
        Optional[str]: Username бота (без @) або None якщо не вдалося отримати
        
    Raises:
        requests.RequestException: Якщо виникла помилка при HTTP запиті
    """
    if token is None:
        token = get_bot_token()
    
    if not token:
        logger.warning("Токен бота не знайдено")
        return None
    
    url = f"{TELEGRAM_API_BASE_URL}{token}/getMe"
    
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("ok"):
            username = data["result"]["username"]
            logger.info(f"Username бота отримано: @{username}")
            return username
        else:
            error_description = data.get("description", "Невідома помилка")
            logger.error(f"Помилка отримання username: {error_description}")
            return None
            
    except requests.Timeout:
        logger.error(f"Таймаут при отриманні username бота (timeout={timeout}s)")
        return None
    except requests.RequestException as e:
        logger.error(f"Помилка HTTP запиту до Telegram API: {e}")
        return None
    except (KeyError, ValueError) as e:
        logger.error(f"Помилка парсингу відповіді від Telegram API: {e}")
        return None


def validate_bot_token(token: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT) -> bool:
    """Перевіряє валідність токену бота.
    
    Args:
        token: Токен бота (якщо None, отримується з змінних середовища)
        timeout: Таймаут запиту в секундах
        
    Returns:
        bool: True якщо токен валідний, False інакше
    """
    username = get_bot_username(token, timeout)
    return username is not None







