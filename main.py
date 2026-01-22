"""Головний сервіс моніторингу та блокування комп'ютера.

Цей модуль запускає моніторинг стану системи та бота Telegram.
"""

import asyncio
import subprocess
import sys
import ctypes
from pathlib import Path
from typing import Optional

from src.core.config import load_config
from src.core.monitor import monitor_logic, should_block
from src.core.otp_manager import start_otp_updates, stop_otp_updates
from src.utils.logger import setup_logging, get_logger
from src.utils.telegram_api import get_bot_token, get_bot_username
from src.utils.qr_generator import print_qr_code_ascii, create_auth_url
from src.utils.path_helper import get_executable_command, is_frozen
from src.bot.bot_runner import run_bot
from src.gui.gui_runner import run_gui_thread
from src.gui.blocking_runner import run_blocking_window, BlockingWindowThread
from src.utils.bot_signal import check_bot_start_signal


def _enable_console() -> None:
    """Відкриває консоль для Windows GUI додатку."""
    try:
        # Відкриваємо консоль
        ctypes.windll.kernel32.AllocConsole()
        # Перенаправляємо stdout та stderr на консоль
        sys.stdout = open('CONOUT$', 'w', encoding='utf-8')
        sys.stderr = open('CONOUT$', 'w', encoding='utf-8')
    except Exception as e:
        # Якщо не вдалося відкрити консоль, просто ігноруємо помилку
        pass


# Перевіряємо аргументи командного рядка
DEBUG_MODE = '--debug' in sys.argv or '-d' in sys.argv

# Якщо режим debug, відкриваємо консоль та встановлюємо DEBUG рівень логування
if DEBUG_MODE:
    _enable_console()
    setup_logging(level=10)  # DEBUG level
else:
    setup_logging(level=20)  # INFO level

logger = get_logger(__name__)


# Глобальна змінна для зберігання поточного вікна блокування
_blocking_window_thread: Optional[BlockingWindowThread] = None

# Event для сигналізації про необхідність запуску бота
_bot_start_event = asyncio.Event()


async def on_block_callback(config: dict) -> None:
    """Callback функція, яка викликається при потребі блокування.
    
    Args:
        config: Конфігурація системи
    """
    global _blocking_window_thread
    
    logger.warning("Потрібно заблокувати комп'ютер")
    
    # Отримуємо bot username для URL
    token = get_bot_token()
    bot_username = get_bot_username(token, timeout=2)
    
    otp = None
    auth_url = None
    
    if bot_username:
        auth_url = create_auth_url(bot_username, config.get("otp", ""))
        
        # Додаємо OTP та URL якщо адміністратор не зареєстрований
        if not config.get("admin_ids") and config.get("otp"):
            otp = config["otp"]
            logger.info(f"Запускаємо вікно блокування з OTP: {otp}")
    else:
        logger.warning("Не вдалося отримати bot username, запускаємо вікно без URL")
    
    # Запускаємо вікно блокування в окремому потоці
    _blocking_window_thread = run_blocking_window(
        countdown_seconds=60,
        otp=otp,
        bot_url=auth_url
    )
    
    # Моніторимо потік та перевіряємо чи потрібно розблокувати
    while _blocking_window_thread and _blocking_window_thread.is_running():
        await asyncio.sleep(5)
        current_config = load_config()
        
        # Перевіряємо чи потрібно розблокувати
        if not should_block(current_config):
            logger.info("Розблокування запитується, закриваємо вікно блокування...")
            if _blocking_window_thread:
                _blocking_window_thread.stop()
            break


async def on_unblock_callback(config: dict) -> None:
    """Callback функція, яка викликається при потребі розблокування.
    
    Args:
        config: Конфігурація системи
    """
    logger.info("Комп'ютер розблоковано")


async def main(launch_gui: bool = True) -> None:
    """Головна функція для запуску сервісу.
    
    Args:
        launch_gui: Чи запускати GUI додаток (за замовчуванням True)
    """
    logger.info("Запуск сервісу батьківського контролю...")
    
    # Запускаємо GUI додаток в окремому потоці (якщо потрібно)
    gui_thread = None
    if launch_gui:
        try:
            gui_thread = run_gui_thread()
            logger.info("GUI додаток запущено в окремому потоці")
            
            # Даємо час на ініціалізацію GUI
            import time
            time.sleep(0.5)
            
            # Перевіряємо чи GUI дійсно запустився
            if not gui_thread.is_alive():
                logger.warning("GUI потік завершився одразу після запуску, продовжуємо без GUI")
                gui_thread = None  # Встановлюємо в None, щоб не моніторити
            else:
                logger.info(f"GUI потік працює (is_alive={gui_thread.is_alive()})")
        except Exception as e:
            logger.error(f"Не вдалося запустити GUI додаток: {e}", exc_info=True)
    
    # Завантажуємо конфігурацію
    logger.info("Завантажуємо конфігурацію...")
    config = load_config()
    logger.info("Конфігурація завантажена")
    
    # Запускаємо періодичне оновлення OTP коду (кожні 10 хвилин)
    try:
        start_otp_updates()
        logger.info("Сервіс оновлення OTP запущено (інтервал: 10 хвилин)")
    except Exception as e:
        logger.error(f"Не вдалося запустити сервіс оновлення OTP: {e}", exc_info=True)
    
    # Виводимо інформацію про реєстрацію
    if config.get("otp"):
        logger.info("OTP знайдено, виводимо інформацію про реєстрацію...")
        token = get_bot_token()
        bot_username = "YOUR_BOT_USERNAME"  # Fallback
        
        if token:
            logger.info("Спроба отримати bot username...")
            try:
                # Виконуємо в executor, щоб не блокувати event loop
                loop = asyncio.get_event_loop()
                bot_username = await loop.run_in_executor(
                    None, 
                    lambda: get_bot_username(token, timeout=3)
                )
                if bot_username:
                    logger.info(f"Bot username: @{bot_username}")
                else:
                    logger.warning("Не вдалося отримати bot username")
            except Exception as e:
                logger.warning(f"Помилка при отриманні bot username: {e}")
        else:
            logger.warning("BOT_TOKEN не встановлено в .env")
        
        auth_url = create_auth_url(bot_username, config["otp"])
        
        logger.info("=" * 50)
        logger.info(f"REGISTRATION CODE: {config['otp']}")
        logger.info(f"URL: {auth_url}")
        logger.info("=" * 50)
        
        # Виводимо QR-код в консоль
        try:
            print_qr_code_ascii(auth_url)
        except Exception as e:
            logger.warning(f"Не вдалося вивести QR-код в ASCII (консоль занадто мала?): {e}")
        
        logger.info("=" * 50)
        logger.info("Інформація про реєстрацію виведена")
    else:
        logger.info("OTP не знайдено в конфігурації")
    
    # Перевіряємо чи є валідний токен перед запуском бота
    logger.info("Перевіряємо наявність токену перед запуском бота...")
    token = get_bot_token()
    
    bot_task = None
    
    # Якщо GUI запущено, чекаємо на сигнал від GUI про збереження токену
    # Якщо GUI не запущено, запускаємо бота одразу якщо токен є
    if gui_thread and gui_thread.is_alive():
        logger.info("GUI запущено. Бот буде запущено після введення та збереження токену в GUI")
        # Не запускаємо бота одразу, чекаємо на сигнал від GUI
    elif token:
        # GUI не запущено, але токен є - запускаємо бота одразу
        logger.info("GUI не запущено, але токен знайдено. Валідуємо та запускаємо бота...")
        try:
            loop = asyncio.get_event_loop()
            is_valid = await loop.run_in_executor(
                None,
                lambda: get_bot_username(token, timeout=3) is not None
            )
            
            if is_valid:
                logger.info("Токен валідний, запускаємо бота...")
                try:
                    bot_task = asyncio.create_task(run_bot())
                    logger.info("Telegram бот запущено як async task")
                    
                    # Перевіряємо чи бот task не завершився одразу через помилку
                    await asyncio.sleep(0.5)  # Даємо час на ініціалізацію
                    if bot_task.done():
                        try:
                            result = await bot_task
                            logger.warning(f"Бот task завершився одразу. Результат: {result}")
                        except Exception as e:
                            logger.error(f"Бот завершився з помилкою: {e}", exc_info=True)
                            bot_task = None
                    else:
                        logger.info("Бот task працює нормально")
                except Exception as e:
                    logger.error(f"Не вдалося запустити бота: {e}", exc_info=True)
                    bot_task = None
            else:
                logger.warning("Токен невалідний, бот не буде запущено")
        except Exception as e:
            logger.warning(f"Помилка валідації токену: {e}. Бот не буде запущено")
    else:
        logger.info("Токен не знайдено. Введіть токен в GUI для запуску бота")
    
    # Створюємо Event для сигналізації про закриття GUI
    gui_closed_event = asyncio.Event()
    gui_monitor_task = None
    
    async def monitor_bot_start():
        """Моніторить події запуску бота після збереження токену."""
        nonlocal bot_task
        
        while True:
            await asyncio.sleep(2)  # Перевіряємо кожні 2 секунди
            
            # Перевіряємо чи є сигнал про необхідність запуску бота
            if not check_bot_start_signal():
                continue
            
            # Перевіряємо чи бот вже запущений
            if bot_task and not bot_task.done():
                logger.info("Бот вже запущений")
                continue
            
            # Перевіряємо токен
            token = get_bot_token()
            if not token:
                logger.warning("Токен не знайдено після сигналу запуску")
                continue
            
            # Валідуємо та запускаємо бота
            logger.info("Отримано сигнал запуску бота, перевіряємо токен...")
            try:
                loop = asyncio.get_event_loop()
                is_valid = await loop.run_in_executor(
                    None,
                    lambda: get_bot_username(token, timeout=3) is not None
                )
                
                if is_valid:
                    logger.info("Токен валідний, запускаємо бота...")
                    bot_task = asyncio.create_task(run_bot())
                    logger.info("Бот запущено після збереження токену")
                else:
                    logger.warning("Токен невалідний, бот не запущено")
            except Exception as e:
                logger.error(f"Помилка запуску бота: {e}", exc_info=True)
    
    async def monitor_gui_thread():
        """Моніторить стан GUI потоку та сигналізує про закриття."""
        if not gui_thread:
            return
        
        logger.info("Моніторинг GUI потоку запущено")
        
        # Даємо час GUI на повну ініціалізацію перед початком моніторингу
        await asyncio.sleep(3)
        
        # Перевіряємо чи GUI дійсно запустився
        if not gui_thread.is_alive():
            logger.warning("GUI потік не запустився, продовжуємо роботу без GUI")
            return
        
        logger.info("GUI потік працює нормально, моніторимо його стан...")
        
        while True:
            await asyncio.sleep(5)  # Перевіряємо кожні 5 секунд
            
            # Перевіряємо чи GUI потік ще працює
            if not gui_thread.is_alive():
                logger.warning("GUI додаток завершився, але продовжуємо роботу сервісу")
                # Не закриваємо сервіс, якщо GUI падає - продовжуємо роботу
                # gui_closed_event.set()  # Закоментовано - не закриваємо сервіс
                return
    
    # Запускаємо моніторинг GUI в окремому таску (якщо GUI запущено)
    if gui_thread:
        gui_monitor_task = asyncio.create_task(monitor_gui_thread())
    
    # Запускаємо моніторинг запуску бота
    bot_start_monitor_task = asyncio.create_task(monitor_bot_start())
    
    try:
        # Запускаємо моніторинг з callback функціями
        monitor_task = asyncio.create_task(
            monitor_logic(
                check_interval=10.0,
                on_block_callback=on_block_callback,
                on_unblock_callback=on_unblock_callback
            )
        )
        
        # Очікуємо поки моніторинг або бот завершаться
        # GUI тепер опціональний - якщо він падає, сервіс продовжує працювати
        tasks_to_wait = [monitor_task]
        if bot_task:
            tasks_to_wait.append(bot_task)
        
        logger.info(f"Очікуємо завершення задач: monitor_task, bot_task")
        
        done, pending = await asyncio.wait(
            tasks_to_wait,
            return_when=asyncio.FIRST_COMPLETED
        )
        
        logger.info("Одна з задач завершилась")
    except (KeyboardInterrupt, SystemExit) as e:
        if isinstance(e, SystemExit):
            logger.info("GUI додаток закрито, завершуємо сервіс...")
        else:
            logger.info("Сервіс зупинено (KeyboardInterrupt)")
        
        # Скасовуємо таск моніторингу GUI якщо він запущений
        if gui_monitor_task and not gui_monitor_task.done():
            gui_monitor_task.cancel()
            try:
                await gui_monitor_task
            except asyncio.CancelledError:
                pass
        
        # Зупиняємо бота
        if bot_task and not bot_task.done():
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                pass
        logger.info("Бот зупинено")
        
        # Зупиняємо GUI якщо запущений
        if gui_thread and gui_thread.is_alive():
            logger.info("Зупинка GUI додатку...")
            try:
                gui_thread.stop()
            except Exception as e:
                logger.warning(f"Помилка при зупинці GUI: {e}")
            logger.info("GUI додаток зупинено")
        
        if isinstance(e, SystemExit):
            sys.exit(0)
    except Exception as e:
        logger.error(f"Критична помилка в сервісі: {e}", exc_info=True)
        
        # Скасовуємо таск моніторингу GUI якщо він запущений
        if gui_monitor_task and not gui_monitor_task.done():
            gui_monitor_task.cancel()
        
        # Зупиняємо бота
        if bot_task and not bot_task.done():
            bot_task.cancel()
        
        # Зупиняємо GUI
        if gui_thread and gui_thread.is_alive():
            try:
                gui_thread.stop()
            except Exception as e:
                logger.warning(f"Помилка при зупинці GUI: {e}")
        raise


if __name__ == "__main__":
    import argparse
    
    # Парсинг аргументів командного рядка
    parser = argparse.ArgumentParser(description="Сервіс батьківського контролю")
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Не запускати GUI додаток (тільки сервіс моніторингу та бот)"
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Відкрити консоль та встановити DEBUG рівень логування"
    )
    parser.add_argument(
        "--service",
        action="store_true",
        help="Запустити як Windows службу"
    )
    args = parser.parse_args()
    
    # Якщо передано --service, запускаємо як службу
    if args.service:
        try:
            from src.core.windows_service import main as service_main
            service_main()
            sys.exit(0)
        except Exception as e:
            logger.error(f"Помилка запуску як служби: {e}", exc_info=True)
            sys.exit(1)
    
    # Перевіряємо чи потрібно встановити службу при першому запуску
    if is_frozen() and not args.no_gui:
        try:
            from src.core.config import has_password
            from src.utils.service_manager import (
                is_service_installed, 
                install_service,
                is_admin
            )
            
            # Перевіряємо чи це перший запуск (немає пароля)
            if not has_password():
                # Перевіряємо чи служба вже встановлена
                if not is_service_installed():
                    # Перевіряємо чи є права адміністратора
                    if is_admin():
                        logger.info("Перший запуск - спроба встановити службу Windows...")
                        if install_service():
                            logger.info("Служба Windows успішно встановлена")
                        else:
                            logger.warning("Не вдалося встановити службу Windows")
                    else:
                        logger.info("Для встановлення служби потрібні права адміністратора")
                        logger.info("Запустіть програму від імені адміністратора для автоматичного встановлення служби")
                else:
                    logger.info("Служба Windows вже встановлена")
        except Exception as e:
            logger.warning(f"Не вдалося перевірити/встановити службу: {e}")
    
    # Якщо передано --debug, перевіряємо ще раз (на випадок якщо перевірка на початку не спрацювала)
    if args.debug and not DEBUG_MODE:
        _enable_console()
        setup_logging(level=10)  # DEBUG level
        logger = get_logger(__name__)
        logger.debug("Режим DEBUG увімкнено через аргумент командного рядка")
    
    try:
        asyncio.run(main(launch_gui=not args.no_gui))
    except KeyboardInterrupt:
        logger.info("Сервіс зупинено")
    except Exception as e:
        logger.error(f"Критична помилка: {e}", exc_info=True)
        sys.exit(1)
