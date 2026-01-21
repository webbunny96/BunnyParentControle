"""Точка входу для Telegram бота."""

import asyncio
import sys
from pathlib import Path

# Додаємо корінь проекту до шляху для імпортів
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from src.core.config import load_config
from src.utils.logger import setup_logging, get_logger
from src.utils.telegram_api import get_bot_token, validate_bot_token
from src.bot.handlers import register_handlers

# Налаштування логування
setup_logging(level=20)  # INFO level
logger = get_logger(__name__)


async def main() -> None:
    """Головна функція для запуску бота.
    
    Завантажує конфігурацію, перевіряє токен, ініціалізує бота та запускає polling.
    """
    # Завантажуємо змінні середовища
    load_dotenv()
    
    logger.info("Запуск Telegram бота...")
    
    # Завантажуємо конфігурацію
    config = load_config()
    logger.info(f"OTP код: {config.get('otp')}")
    
    # Перевіряємо токен бота
    bot_token = get_bot_token()
    if not bot_token:
        logger.error("BOT_TOKEN не знайдено в .env файлі!")
        sys.exit(1)
    
    if not validate_bot_token(bot_token):
        logger.error("BOT_TOKEN невалідний!")
        sys.exit(1)
    
    # Створюємо бота та dispatcher
    bot = Bot(token=bot_token)
    dp = Dispatcher()
    
    # Реєструємо обробники
    register_handlers(dp, config)
    
    try:
        logger.info("Бот запущено, очікуємо повідомлення...")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Бот зупинено (KeyboardInterrupt)")
    except Exception as e:
        logger.error(f"Помилка при роботі бота: {e}", exc_info=True)
        raise
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот зупинено")
    except Exception as e:
        logger.error(f"Критична помилка: {e}", exc_info=True)
        sys.exit(1)







