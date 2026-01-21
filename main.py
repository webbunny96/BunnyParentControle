"""Головний сервіс моніторингу та блокування комп'ютера.

Цей модуль запускає моніторинг стану системи та бота Telegram.
"""

import asyncio
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.core.config import load_config
from src.core.monitor import monitor_logic, should_block
from src.utils.logger import setup_logging, get_logger
from src.utils.telegram_api import get_bot_token, get_bot_username
from src.utils.qr_generator import print_qr_code_ascii, create_auth_url

# Налаштування логування
setup_logging(level=20)  # INFO level
logger = get_logger(__name__)


async def on_block_callback(config: dict) -> None:
    """Callback функція, яка викликається при потребі блокування.
    
    Args:
        config: Конфігурація системи
    """
    logger.warning("Потрібно заблокувати комп'ютер")
    
    # Запускаємо вікно блокування як окремий процес
    blocking_window_path = Path(__file__).parent / "src" / "gui" / "blocking_window.py"
    args = [sys.executable, str(blocking_window_path)]
    
    # Отримуємо bot username для URL
    token = get_bot_token()
    bot_username = get_bot_username(token, timeout=2)
    
    if bot_username:
        auth_url = create_auth_url(bot_username, config.get("otp", ""))
        
        # Додаємо OTP та URL якщо адміністратор не зареєстрований
        if not config.get("admin_ids") and config.get("otp"):
            args.extend(["--otp", config["otp"], "--url", auth_url])
        
        logger.info(f"Запускаємо вікно блокування з OTP: {config.get('otp')}")
    else:
        logger.warning("Не вдалося отримати bot username, запускаємо вікно без URL")
    
    # Запускаємо процес
    proc = subprocess.Popen(args)
    
    # Моніторимо процес та перевіряємо чи потрібно розблокувати
    while proc.poll() is None:
        await asyncio.sleep(5)
        current_config = load_config()
        
        # Перевіряємо чи потрібно розблокувати
        if not should_block(current_config):
            logger.info("Розблокування запитується, закриваємо вікно блокування...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
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
    # Завантажуємо змінні середовища
    load_dotenv()
    
    logger.info("Запуск сервісу батьківського контролю...")
    
    # Запускаємо GUI додаток як окремий процес (якщо потрібно)
    gui_proc = None
    if launch_gui:
        try:
            gui_path = Path(__file__).parent / "src" / "gui" / "main.py"
            gui_proc = subprocess.Popen([sys.executable, str(gui_path)])
            logger.info("GUI додаток запущено")
        except Exception as e:
            logger.warning(f"Не вдалося запустити GUI додаток: {e}")
    
    # Завантажуємо конфігурацію
    config = load_config()
    
    # Виводимо інформацію про реєстрацію
    if config.get("otp"):
        token = get_bot_token()
        bot_username = "YOUR_BOT_USERNAME"  # Fallback
        
        if token:
            bot_username = get_bot_username(token, timeout=5)
            if bot_username:
                logger.info(f"Bot username: @{bot_username}")
            else:
                logger.warning("Не вдалося отримати bot username")
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
    
    # Запускаємо бота як окремий процес
    bot_path = Path(__file__).parent / "src" / "bot" / "main.py"
    bot_proc = subprocess.Popen([sys.executable, str(bot_path)])
    logger.info("Telegram бот запущено")
    
    # Створюємо Event для сигналізації про закриття GUI
    gui_closed_event = asyncio.Event()
    gui_monitor_task = None
    
    async def monitor_gui_process():
        """Моніторить стан GUI процесу та сигналізує про закриття."""
        if not gui_proc:
            return
        
        while True:
            await asyncio.sleep(2)  # Перевіряємо кожні 2 секунди
            
            # Перевіряємо чи GUI процес ще працює
            if gui_proc.poll() is not None:
                logger.info("GUI додаток закрито, завершуємо сервіс...")
                # Сигналізуємо про закриття GUI
                gui_closed_event.set()
                return
    
    # Запускаємо моніторинг GUI в окремому таску (якщо GUI запущено)
    if gui_proc:
        gui_monitor_task = asyncio.create_task(monitor_gui_process())
    
    try:
        # Запускаємо моніторинг з callback функціями
        monitor_task = asyncio.create_task(
            monitor_logic(
                check_interval=10.0,
                on_block_callback=on_block_callback,
                on_unblock_callback=on_unblock_callback
            )
        )
        
        # Очікуємо поки GUI закриється або моніторинг завершиться
        if gui_proc:
            # Створюємо таск для очікування закриття GUI
            gui_wait_task = asyncio.create_task(gui_closed_event.wait())
            
            done, pending = await asyncio.wait(
                [monitor_task, gui_wait_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Якщо GUI закрито, скасовуємо моніторинг
            if gui_closed_event.is_set():
                monitor_task.cancel()
                gui_wait_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
                try:
                    await gui_wait_task
                except asyncio.CancelledError:
                    pass
                raise SystemExit("GUI додаток закрито")
        else:
            # Якщо GUI не запущено, просто очікуємо моніторинг
            await monitor_task
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
        bot_proc.terminate()
        try:
            bot_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            bot_proc.kill()
        logger.info("Бот зупинено")
        
        # Зупиняємо GUI якщо запущений (тільки якщо не вже закритий)
        if gui_proc and gui_proc.poll() is None:
            logger.info("Зупинка GUI додатку...")
            gui_proc.terminate()
            try:
                gui_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                gui_proc.kill()
            logger.info("GUI додаток зупинено")
        
        if isinstance(e, SystemExit):
            sys.exit(0)
    except Exception as e:
        logger.error(f"Критична помилка в сервісі: {e}", exc_info=True)
        
        # Скасовуємо таск моніторингу GUI якщо він запущений
        if gui_monitor_task and not gui_monitor_task.done():
            gui_monitor_task.cancel()
        
        bot_proc.terminate()
        if gui_proc:
            gui_proc.terminate()
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
    args = parser.parse_args()
    
    try:
        asyncio.run(main(launch_gui=not args.no_gui))
    except KeyboardInterrupt:
        logger.info("Сервіс зупинено")
    except Exception as e:
        logger.error(f"Критична помилка: {e}", exc_info=True)
        sys.exit(1)
