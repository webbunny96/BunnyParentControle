"""Модуль для роботи з .env файлом."""

import os
from pathlib import Path
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)

ENV_FILE = ".env"


def get_bot_token_from_env() -> Optional[str]:
    """Отримує токен бота з .env файлу.
    
    Returns:
        Optional[str]: Токен бота або None якщо не знайдено
    """
    if not os.path.exists(ENV_FILE):
        return None
    
    try:
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("BOT_TOKEN="):
                    token = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return token
    except (IOError, ValueError) as e:
        logger.error(f"Помилка читання .env файлу: {e}")
    
    return None


def save_bot_token_to_env(token: str) -> bool:
    """Зберігає токен бота в .env файл.
    
    Args:
        token: Токен бота для збереження
        
    Returns:
        bool: True якщо успішно збережено, False інакше
    """
    if not token or not token.strip():
        logger.warning("Спроба зберегти порожній токен")
        return False
    
    token = token.strip()
    env_content = []
    token_found = False
    
    # Читаємо існуючий файл якщо він є
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("BOT_TOKEN="):
                        env_content.append(f'BOT_TOKEN="{token}"\n')
                        token_found = True
                    else:
                        env_content.append(line)
        except IOError as e:
            logger.error(f"Помилка читання .env файлу: {e}")
            return False
    
    # Додаємо токен якщо не знайдено
    if not token_found:
        env_content.append(f'BOT_TOKEN="{token}"\n')
    
    # Зберігаємо файл
    try:
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.writelines(env_content)
        logger.info("Токен бота збережено в .env файл")
        return True
    except IOError as e:
        logger.error(f"Помилка запису в .env файл: {e}")
        return False






