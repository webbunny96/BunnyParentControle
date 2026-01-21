"""Модуль з обробниками команд та callback для Telegram бота."""

import os
import time
from datetime import datetime
from typing import Dict, Any

from aiogram import Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from src.core.config import load_config, save_config
from src.core.monitor import get_status_info
from src.bot.keyboards import (
    get_main_keyboard,
    get_time_keyboard,
    get_schedule_keyboard,
    get_day_config_keyboard,
    get_confirmation_keyboard,
    get_cancel_keyboard,
    DAY_NAMES_FULL
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


def is_admin(user_id: int, config: Dict[str, Any] | None = None) -> bool:
    """Перевіряє, чи користувач є адміністратором.
    
    Args:
        user_id: ID користувача Telegram
        config: Конфігурація системи (якщо None, завантажується автоматично)
        
    Returns:
        bool: True якщо користувач є адміністратором, False інакше
    """
    if config is None:
        config = load_config()
    
    admin_ids = config.get("admin_ids", [])
    return user_id in admin_ids


async def cmd_start_handler(message: Message, command: Command) -> None:
    """Обробник команди /start.
    
    Обробляє реєстрацію адміністратора через QR-код або код.
    
    Args:
        message: Повідомлення від користувача
        command: Об'єкт команди з аргументами
        bot: Об'єкт бота
    """
    config = load_config()
    user_id = message.from_user.id
    
    # Перевіряємо deep link реєстрацію через QR-код
    if command.args and command.args == config.get("otp"):
        if not is_admin(user_id, config):
            config["admin_ids"].append(user_id)
            save_config(config)
            logger.info(f"Користувач {user_id} зареєстрований через QR-код")
            await message.answer("Вітаю! Ви тепер зареєстровані як адміністратор через QR-код.")
            await message.answer("Виберіть дію:", reply_markup=get_main_keyboard())
            return
        else:
            await message.answer("Ви вже є адміністратором.")
            await message.answer("Виберіть дію:", reply_markup=get_main_keyboard())
            return
    
    # Перевіряємо чи користувач вже адміністратор
    if is_admin(user_id, config):
        await message.answer("Привіт, батьку! Виберіть дію:", reply_markup=get_main_keyboard())
    else:
        await message.answer(
            "Привіт! Щоб стати адміністратором, відскануйте QR-код на екрані "
            "комп'ютера або надішліть код реєстрації."
        )


async def register_admin_handler(message: Message) -> None:
    """Обробник реєстрації адміністратора через текстовий код.
    
    Args:
        message: Повідомлення від користувача з кодом
        bot: Об'єкт бота
    """
    config = load_config()
    user_id = message.from_user.id
    otp_code = config.get("otp")
    
    if message.text == otp_code:
        if not is_admin(user_id, config):
            config["admin_ids"].append(user_id)
            save_config(config)
            logger.info(f"Користувач {user_id} зареєстрований через код")
            await message.answer("Вітаю! Ви тепер зареєстровані як адміністратор.")
            await message.answer("Виберіть дію:", reply_markup=get_main_keyboard())
        else:
            await message.answer("Ви вже зареєстровані.")


async def cmd_status_handler(message: Message) -> None:
    """Обробник команди /status.
    
    Args:
        message: Повідомлення від користувача
        bot: Об'єкт бота
    """
    config = load_config()
    
    if not is_admin(message.from_user.id, config):
        return
    
    status_info = get_status_info(config)
    
    status_msg = "📊 Статус системи:\n"
    status_msg += f"- Блокування: {'🔴 ТАК' if status_info['blocked'] else '🟢 НІ'}\n"
    status_msg += f"- Force block: {'Так' if status_info['force_block'] else 'Ні'}\n"
    
    # Інформація про розклад
    now = datetime.now()
    day_idx = str(now.weekday())
    schedule = config.get("schedule", {})
    day_cfg = schedule.get(day_idx, {})
    
    if day_cfg.get("enabled"):
        status_msg += (
            f"- Сьогоднішній розклад: {day_cfg.get('start')} - {day_cfg.get('end')} "
            f"(Активний)\n"
        )
    else:
        status_msg += "- Сьогоднішній розклад: Вимкнено\n"
    
    # Інформація про ліміт часу
    if status_info['time_limit']:
        time_remaining = status_info['time_remaining']
        if time_remaining is not None:
            status_msg += f"- Ліміт: {status_info['time_limit']} хв\n"
            status_msg += f"- Залишилось: {int(time_remaining)} хв\n"
    else:
        status_msg += "- Ліміт: відсутній\n"
    
    await message.answer(status_msg)


async def cmd_shutdown_handler(message: Message) -> None:
    """Обробник команди /shutdown.
    
    Args:
        message: Повідомлення від користувача
        bot: Об'єкт бота
    """
    if not is_admin(message.from_user.id):
        return
    
    await message.answer("Вимикаю комп'ютер...")
    logger.warning(f"Комп'ютер вимикається командою від користувача {message.from_user.id}")
    os.system("shutdown /s /t 1 /f")


async def cmd_restart_handler(message: Message) -> None:
    """Обробник команди /restart.
    
    Args:
        message: Повідомлення від користувача
        bot: Об'єкт бота
    """
    if not is_admin(message.from_user.id):
        return
    
    await message.answer("Перезавантажую комп'ютер...")
    logger.warning(f"Комп'ютер перезавантажується командою від користувача {message.from_user.id}")
    os.system("shutdown /r /t 1 /f")


async def cmd_block_handler(message: Message) -> None:
    """Обробник команди /block.
    
    Args:
        message: Повідомлення від користувача
        bot: Об'єкт бота
    """
    if not is_admin(message.from_user.id):
        return
    
    config = load_config()
    config["force_block"] = True
    save_config(config)
    logger.info(f"Force block активовано користувачем {message.from_user.id}")
    await message.answer("Активуємо вікно блокування...")


async def cmd_unblock_handler(message: Message) -> None:
    """Обробник команди /unblock.
    
    Args:
        message: Повідомлення від користувача
        bot: Об'єкт бота
    """
    if not is_admin(message.from_user.id):
        return
    
    config = load_config()
    config["force_block"] = False
    save_config(config)
    logger.info(f"Force block деактивовано користувачем {message.from_user.id}")
    await message.answer("Розблоковано!")


async def process_callbacks_handler(callback: CallbackQuery) -> None:
    """Основний обробник callback запитів.
    
    Args:
        callback: Об'єкт callback запиту
        bot: Об'єкт бота
    """
    config = load_config()
    
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Ви не маєте прав доступу.")
        return
    
    data = callback.data
    
    try:
        # Головне меню
        if data == "main_menu":
            await callback.message.edit_text("Виберіть дію:", reply_markup=get_main_keyboard())
        
        # Статус
        elif data == "status":
            await handle_status_callback(callback, config)
        
        # Блокування/Розблокування
        elif data == "block":
            await handle_block_callback(callback, config)
        elif data == "unblock":
            await handle_unblock_callback(callback, config)
        
        # Розклад
        elif data == "schedule_menu":
            await callback.message.edit_text(
                "📅 Розклад блокування (час сну):",
                reply_markup=get_schedule_keyboard(config)
            )
        elif data.startswith("day_"):
            await handle_day_callback(callback, data, config)
        elif data.startswith("toggle_"):
            await handle_toggle_callback(callback, data, config)
        elif data.startswith("edit_start_") or data.startswith("edit_end_"):
            await handle_edit_time_callback(callback, data, config)
        
        # Ліміт часу
        elif data.startswith("time_"):
            await handle_time_limit_callback(callback, data, config)
        
        # Підтвердження вимкнення/перезавантаження
        elif data == "confirm_shutdown":
            await callback.message.edit_text(
                "⚠️ Ви впевнені, що хочете ВИМКНУТИ комп'ютер?",
                reply_markup=get_confirmation_keyboard("shutdown")
            )
        elif data == "confirm_restart":
            await callback.message.edit_text(
                "⚠️ Ви впевнені, що хочете ПЕРЕЗАВАНТАЖИТИ комп'ютер?",
                reply_markup=get_confirmation_keyboard("restart")
            )
        elif data == "shutdown_now":
            await handle_shutdown_callback(callback)
        elif data == "restart_now":
            await handle_restart_callback(callback)
        
        # Зміна пароля
        elif data == "change_password":
            await handle_change_password_callback(callback, config)
        elif data == "cancel_password_change":
            await handle_cancel_password_callback(callback, config)
        
        else:
            logger.warning(f"Невідомий callback: {data}")
            await callback.answer("Невідома команда")
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Помилка обробки callback {data}: {e}", exc_info=True)
        await callback.answer("Сталася помилка при обробці запиту")


async def handle_status_callback(callback: CallbackQuery, config: Dict[str, Any]) -> None:
    """Обробник callback для статусу."""
    status_info = get_status_info(config)
    
    status_msg = "📊 Статус системи:\n"
    status_msg += f"- Блокування: {'🔴 ТАК' if status_info['blocked'] else '🟢 НІ'}\n"
    
    # Розклад
    now = datetime.now()
    day_idx = str(now.weekday())
    schedule = config.get("schedule", {})
    day_cfg = schedule.get(day_idx, {})
    
    if day_cfg.get("enabled"):
        status_msg += (
            f"- Сьогоднішній розклад: {day_cfg.get('start')} - {day_cfg.get('end')} "
            f"(Активний)\n"
        )
    else:
        status_msg += "- Сьогоднішній розклад: Вимкнено\n"
    
    # Ліміт часу
    if status_info['time_limit']:
        time_remaining = status_info['time_remaining']
        if time_remaining is not None:
            status_msg += f"- Ліміт: {status_info['time_limit']} хв\n"
            status_msg += f"- Залишилось: {int(time_remaining)} хв\n"
    else:
        status_msg += "- Ліміт: відсутній\n"
    
    await callback.message.edit_text(status_msg, reply_markup=get_main_keyboard())


async def handle_block_callback(callback: CallbackQuery, config: Dict[str, Any]) -> None:
    """Обробник callback для блокування."""
    config["force_block"] = True
    save_config(config)
    logger.info(f"Force block активовано через callback від {callback.from_user.id}")
    await callback.message.edit_text("🔒 Комп'ютер заблоковано!", reply_markup=get_main_keyboard())


async def handle_unblock_callback(callback: CallbackQuery, config: Dict[str, Any]) -> None:
    """Обробник callback для розблокування."""
    config["force_block"] = False
    save_config(config)
    logger.info(f"Force block деактивовано через callback від {callback.from_user.id}")
    await callback.message.edit_text("🔓 Комп'ютер розблоковано!", reply_markup=get_main_keyboard())


async def handle_day_callback(callback: CallbackQuery, data: str, config: Dict[str, Any]) -> None:
    """Обробник callback для вибору дня тижня."""
    day_idx = data.split("_")[1]
    day_name = DAY_NAMES_FULL[int(day_idx)] if day_idx.isdigit() and 0 <= int(day_idx) < 7 else f"День {day_idx}"
    await callback.message.edit_text(
        f"Налаштування для: {day_name}",
        reply_markup=get_day_config_keyboard(day_idx, config)
    )


async def handle_toggle_callback(callback: CallbackQuery, data: str, config: Dict[str, Any]) -> None:
    """Обробник callback для перемикання стану дня розкладу."""
    day_idx = data.split("_")[1]
    schedule = config.get("schedule", {})
    day_cfg = schedule.get(day_idx, {})
    day_cfg["enabled"] = not day_cfg.get("enabled", False)
    schedule[day_idx] = day_cfg
    config["schedule"] = schedule
    save_config(config)
    logger.info(f"Розклад для дня {day_idx} {'увімкнено' if day_cfg['enabled'] else 'вимкнено'}")
    await callback.message.edit_reply_markup(reply_markup=get_day_config_keyboard(day_idx, config))


async def handle_edit_time_callback(callback: CallbackQuery, data: str, config: Dict[str, Any]) -> None:
    """Обробник callback для редагування часу розкладу."""
    parts = data.split("_")
    mode = parts[1]  # start or end
    day_idx = parts[2]
    
    mode_text = "початку" if mode == "start" else "кінця"
    await callback.message.answer(
        f"Введіть час у форматі HH:MM (наприклад, 22:30) для дня {day_idx} ({mode_text}):"
    )
    
    config["awaiting_time"] = {"day": day_idx, "mode": mode}
    save_config(config)


async def handle_time_limit_callback(callback: CallbackQuery, data: str, config: Dict[str, Any]) -> None:
    """Обробник callback для встановлення ліміту часу."""
    minutes = int(data.split("_")[1])
    config["time_limit_minutes"] = minutes
    config["start_time"] = time.time()
    save_config(config)
    
    text = (
        f"✅ Час роботи встановлено на {minutes} хв."
        if minutes > 0
        else "✅ Ліміт часу видалено."
    )
    logger.info(f"Ліміт часу встановлено: {minutes} хв")
    await callback.message.edit_text(text, reply_markup=get_main_keyboard())


async def handle_shutdown_callback(callback: CallbackQuery) -> None:
    """Обробник callback для вимкнення комп'ютера."""
    await callback.message.edit_text("🛑 Вимикання...")
    logger.warning(f"Комп'ютер вимикається через callback від {callback.from_user.id}")
    os.system("shutdown /s /t 1 /f")


async def handle_restart_callback(callback: CallbackQuery) -> None:
    """Обробник callback для перезавантаження комп'ютера."""
    await callback.message.edit_text("🔄 Перезавантаження...")
    logger.warning(f"Комп'ютер перезавантажується через callback від {callback.from_user.id}")
    os.system("shutdown /r /t 1 /f")


async def handle_change_password_callback(callback: CallbackQuery, config: Dict[str, Any]) -> None:
    """Обробник callback для зміни пароля."""
    config["awaiting_password"] = True
    save_config(config)
    await callback.message.edit_text(
        "🔑 Введіть новий батьківський пароль:\n\n"
        "Пароль буде використовуватися для доступу до налаштувань на комп'ютері.",
        reply_markup=get_cancel_keyboard()
    )


async def handle_cancel_password_callback(callback: CallbackQuery, config: Dict[str, Any]) -> None:
    """Обробник callback для скасування зміни пароля."""
    config["awaiting_password"] = False
    save_config(config)
    await callback.message.edit_text("Виберіть дію:", reply_markup=get_main_keyboard())


async def process_time_input_handler(message: Message) -> None:
    """Обробник введення часу для розкладу.
    
    Args:
        message: Повідомлення з часом у форматі HH:MM
        bot: Об'єкт бота
    """
    if not is_admin(message.from_user.id):
        return
    
    config = load_config()
    awaiting = config.get("awaiting_time")
    
    if not awaiting:
        await message.answer("Час введено, але я не очікував налаштувань. Скористайтесь меню.")
        return
    
    day_idx = awaiting["day"]
    mode = awaiting["mode"]
    
    # Валідація формату часу (вже перевірено regex, але для впевненості)
    time_str = message.text.strip()
    
    schedule = config.get("schedule", {})
    day_cfg = schedule.get(day_idx, {})
    day_cfg[mode] = time_str
    schedule[day_idx] = day_cfg
    config["schedule"] = schedule
    config["awaiting_time"] = None
    save_config(config)
    
    mode_text = "початку" if mode == "start" else "кінця"
    logger.info(f"Час {mode_text} для дня {day_idx} оновлено: {time_str}")
    
    await message.answer(
        f"✅ Час {mode_text} оновлено для дня {day_idx}: {time_str}",
        reply_markup=get_day_config_keyboard(day_idx, config)
    )


async def process_password_input_handler(message: Message) -> None:
    """Обробник введення нового пароля.
    
    Args:
        message: Повідомлення з новим паролем
        bot: Об'єкт бота
    """
    if not is_admin(message.from_user.id):
        return
    
    config = load_config()
    
    if not config.get("awaiting_password"):
        return
    
    new_password = message.text.strip()
    
    if len(new_password) < 4:
        await message.answer("❌ Пароль повинен містити мінімум 4 символи. Спробуйте ще раз:")
        return
    
    config["parent_password"] = new_password
    config["awaiting_password"] = False
    save_config(config)
    
    logger.info(f"Батьківський пароль змінено користувачем {message.from_user.id}")
    await message.answer("✅ Батьківський пароль успішно змінено!", reply_markup=get_main_keyboard())


def register_handlers(dp: Dispatcher, config: Dict[str, Any]) -> None:
    """Реєструє всі обробники в dispatcher.
    
    Args:
        dp: Dispatcher для реєстрації обробників
        config: Конфігурація системи
    """
    # Команди
    dp.message.register(cmd_start_handler, Command("start"))
    dp.message.register(cmd_status_handler, Command("status"))
    dp.message.register(cmd_shutdown_handler, Command("shutdown"))
    dp.message.register(cmd_restart_handler, Command("restart"))
    dp.message.register(cmd_block_handler, Command("block"))
    dp.message.register(cmd_unblock_handler, Command("unblock"))
    
    # Реєстрація через код
    otp_code = config.get("otp")
    if otp_code:
        dp.message.register(register_admin_handler, F.text == otp_code)
    
    # Введення часу (регулярний вираз для HH:MM)
    dp.message.register(
        process_time_input_handler,
        F.text.regexp(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    )
    
    # Введення пароля (будь-який текст, якщо очікується пароль)
    dp.message.register(process_password_input_handler, F.text.len() > 0)
    
    # Callback запити
    dp.callback_query.register(process_callbacks_handler)
    
    logger.info("Обробники зареєстровано")

