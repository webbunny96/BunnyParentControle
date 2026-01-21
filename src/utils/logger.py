"""Модуль для налаштування логування."""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """Налаштовує систему логування.
    
    Args:
        level: Рівень логування (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Шлях до файлу для збереження логів (опціонально)
        format_string: Формат повідомлень логування (опціонально)
        
    Returns:
        logging.Logger: Налаштований логер
    """
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout)
    ]
    
    # Додаємо файловий handler якщо вказано
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        handlers.append(file_handler)
    
    # Налаштовуємо базове логування
    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=handlers,
        force=True  # Перезаписуємо існуючу конфігурацію
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Логування налаштовано (рівень: {logging.getLevelName(level)})")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Отримує логер для конкретного модуля.
    
    Args:
        name: Ім'я модуля (зазвичай __name__)
        
    Returns:
        logging.Logger: Логер для модуля
    """
    return logging.getLogger(name)







