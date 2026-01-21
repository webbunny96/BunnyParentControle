"""Модуль для генерації QR-кодів."""

import qrcode
from typing import Optional
from PIL import Image

from src.utils.logger import get_logger

logger = get_logger(__name__)


def generate_qr_code(
    data: str,
    version: int = 1,
    box_size: int = 5,
    border: int = 4,
    fill_color: str = "black",
    back_color: str = "white"
) -> Image.Image:
    """Генерує QR-код як PIL Image.
    
    Args:
        data: Дані для кодування в QR-код
        version: Версія QR-коду (1-40, вищий номер = більший розмір)
        box_size: Розмір кожного квадрата в пікселях
        border: Розмір border (мінімум 4)
        fill_color: Колір заповнення
        back_color: Колір фону
        
    Returns:
        Image.Image: Зображення QR-коду
        
    Raises:
        ValueError: Якщо параметри невалідні
        Exception: Якщо не вдалося згенерувати QR-код
    """
    try:
        qr = qrcode.QRCode(
            version=version,
            box_size=box_size,
            border=border
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        qr_image = qr.make_image(
            fill_color=fill_color,
            back_color=back_color
        )
        
        return qr_image
    except Exception as e:
        logger.error(f"Помилка генерації QR-коду: {e}")
        raise


def generate_qr_code_resized(
    data: str,
    size: tuple[int, int] = (150, 150),
    version: int = 1,
    box_size: int = 5,
    border: int = 4,
    fill_color: str = "black",
    back_color: str = "white"
) -> Image.Image:
    """Генерує QR-код та змінює його розмір.
    
    Args:
        data: Дані для кодування в QR-код
        size: Розмір вихідного зображення (width, height)
        version: Версія QR-коду
        box_size: Розмір кожного квадрата
        border: Розмір border
        fill_color: Колір заповнення
        back_color: Колір фону
        
    Returns:
        Image.Image: Зображення QR-коду з заданим розміром
        
    Raises:
        ValueError: Якщо параметри невалідні
        Exception: Якщо не вдалося згенерувати QR-код
    """
    qr_image = generate_qr_code(
        data=data,
        version=version,
        box_size=box_size,
        border=border,
        fill_color=fill_color,
        back_color=back_color
    )
    
    try:
        resized_image = qr_image.resize(size, Image.Resampling.LANCZOS)
        return resized_image
    except Exception as e:
        logger.error(f"Помилка зміни розміру QR-коду: {e}")
        raise


def print_qr_code_ascii(data: str) -> None:
    """Виводить QR-код в ASCII форматі в консоль.
    
    Args:
        data: Дані для кодування в QR-код
        
    Raises:
        Exception: Якщо не вдалося вивести QR-код (наприклад, консоль занадто мала)
    """
    try:
        qr = qrcode.QRCode()
        qr.add_data(data)
        qr.make()
        qr.print_ascii()
    except Exception as e:
        logger.warning(f"Не вдалося вивести QR-код в ASCII (консоль занадто мала?): {e}")
        raise


def create_auth_url(bot_username: str, otp_code: str) -> str:
    """Створює URL для авторизації через Telegram бота.
    
    Args:
        bot_username: Username Telegram бота (без @)
        otp_code: OTP код для авторизації
        
    Returns:
        str: URL для авторизації
        
    Example:
        >>> create_auth_url("mybot", "ABCD1234")
        'https://t.me/mybot?start=ABCD1234'
    """
    return f"https://t.me/{bot_username}?start={otp_code}"







