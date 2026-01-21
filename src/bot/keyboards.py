"""Модуль з клавіатурами для Telegram бота."""

from typing import Dict, Any
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from src.core.config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Константи для назв днів тижня
DAY_NAMES_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
DAY_NAMES_FULL = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Повертає головну клавіатуру з основними діями.
    
    Returns:
        InlineKeyboardMarkup: Клавіатура з кнопками:
            - Заблокувати / Розблокувати
            - Розклад / Статус
            - Змінити батьківський пароль
            - Перезавантажити / Вимкнути ПК
    """
    buttons = [
        [
            InlineKeyboardButton(text="🔒 Заблокувати", callback_data="block"),
            InlineKeyboardButton(text="🔓 Розблокувати", callback_data="unblock")
        ],
        [
            InlineKeyboardButton(text="📅 Розклад", callback_data="schedule_menu"),
            InlineKeyboardButton(text="📊 Статус", callback_data="status")
        ],
        [
            InlineKeyboardButton(text="🔑 Змінити батьківський пароль", callback_data="change_password")
        ],
        [
            InlineKeyboardButton(text="🔄 Перезавантажити", callback_data="confirm_restart"),
            InlineKeyboardButton(text="🛑 Вимкнути ПК", callback_data="confirm_shutdown")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_time_keyboard() -> InlineKeyboardMarkup:
    """Повертає клавіатуру для вибору ліміту часу.
    
    Returns:
        InlineKeyboardMarkup: Клавіатура з опціями:
            - 15 хв, 30 хв, 60 хв
            - 2 год, Без ліміту
            - Назад
    """
    buttons = [
        [
            InlineKeyboardButton(text="15 хв", callback_data="time_15"),
            InlineKeyboardButton(text="30 хв", callback_data="time_30"),
            InlineKeyboardButton(text="60 хв", callback_data="time_60")
        ],
        [
            InlineKeyboardButton(text="2 год", callback_data="time_120"),
            InlineKeyboardButton(text="Без ліміту", callback_data="time_0")
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_schedule_keyboard(config: Dict[str, Any] | None = None) -> InlineKeyboardMarkup:
    """Повертає клавіатуру для вибору дня тижня в розкладі.
    
    Args:
        config: Конфігурація системи (якщо None, завантажується автоматично)
        
    Returns:
        InlineKeyboardMarkup: Клавіатура з кнопками днів тижня та статусом (✅/❌)
    """
    if config is None:
        config = get_config()
    
    schedule = config.get("schedule", {})
    buttons = []
    
    # Перший рядок: Пн-Чт (4 дні)
    row1 = []
    for i in range(4):
        day_str = str(i)
        day_schedule = schedule.get(day_str, {})
        status = "✅" if day_schedule.get("enabled", False) else "❌"
        row1.append(
            InlineKeyboardButton(
                text=f"{DAY_NAMES_SHORT[i]} {status}",
                callback_data=f"day_{i}"
            )
        )
    buttons.append(row1)
    
    # Другий рядок: Пт-Нд (3 дні)
    row2 = []
    for i in range(4, 7):
        day_str = str(i)
        day_schedule = schedule.get(day_str, {})
        status = "✅" if day_schedule.get("enabled", False) else "❌"
        row2.append(
            InlineKeyboardButton(
                text=f"{DAY_NAMES_SHORT[i]} {status}",
                callback_data=f"day_{i}"
            )
        )
    buttons.append(row2)
    
    # Кнопка "Назад"
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_day_config_keyboard(day_idx: str | int, config: Dict[str, Any] | None = None) -> InlineKeyboardMarkup:
    """Повертає клавіатуру для налаштування конкретного дня тижня.
    
    Args:
        day_idx: Індекс дня тижня (0-6, 0=понеділок, 6=неділя)
        config: Конфігурація системи (якщо None, завантажується автоматично)
        
    Returns:
        InlineKeyboardMarkup: Клавіатура з опціями:
            - Увімкнути/Вимкнути розклад
            - Налаштування часу початку/кінця
            - Назад до розкладу
    """
    if config is None:
        config = get_config()
    
    day_str = str(day_idx)
    schedule = config.get("schedule", {})
    day_cfg = schedule.get(day_str, {"start": "22:00", "end": "07:00", "enabled": False})
    
    enabled_text = "🔴 Вимкнути" if day_cfg.get("enabled", False) else "🟢 Увімкнути"
    
    buttons = [
        [InlineKeyboardButton(text=enabled_text, callback_data=f"toggle_{day_str}")],
        [
            InlineKeyboardButton(
                text=f"⏰ Початок: {day_cfg.get('start', '22:00')}",
                callback_data=f"edit_start_{day_str}"
            ),
            InlineKeyboardButton(
                text=f"⏰ Кінець: {day_cfg.get('end', '07:00')}",
                callback_data=f"edit_end_{day_str}"
            )
        ],
        [InlineKeyboardButton(text="⬅️ До розкладу", callback_data="schedule_menu")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirmation_keyboard(action: str = "shutdown") -> InlineKeyboardMarkup:
    """Повертає клавіатуру підтвердження для небезпечних дій.
    
    Args:
        action: Тип дії ("shutdown" або "restart")
        
    Returns:
        InlineKeyboardMarkup: Клавіатура з кнопками підтвердження та скасування
    """
    if action == "shutdown":
        confirm_text = "✅ ТАК, вимкнути"
        confirm_callback = "shutdown_now"
    elif action == "restart":
        confirm_text = "✅ ТАК, перезавантажити"
        confirm_callback = "restart_now"
    else:
        confirm_text = "✅ ТАК"
        confirm_callback = "confirm"
    
    buttons = [
        [InlineKeyboardButton(text=confirm_text, callback_data=confirm_callback)],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="main_menu")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Повертає клавіатуру тільки з кнопкою "Скасувати".
    
    Returns:
        InlineKeyboardMarkup: Клавіатура з однією кнопкою "Скасувати"
    """
    buttons = [
        [InlineKeyboardButton(text="⬅️ Скасувати", callback_data="cancel_password_change")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)







