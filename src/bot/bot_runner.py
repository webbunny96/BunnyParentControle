"""Модуль для запуску Telegram бота як async task."""

import asyncio
import sys
from aiogram import Bot, Dispatcher
from src.core.config import load_config
from src.utils.logger import get_logger
from src.utils.telegram_api import get_bot_token, validate_bot_token
from src.bot.handlers import register_handlers

logger = get_logger(__name__)


async def run_bot() -> None:
    """Запускає Telegram бота як async task.
    
    Ця функція призначена для запуску бота всередині основного asyncio event loop.
    """
    logger.info("run_bot() викликано")
    
    logger.info("Запуск Telegram бота...")
    
    # Завантажуємо конфігурацію
    logger.debug("Завантажуємо конфігурацію в bot_runner...")
    config = load_config()
    logger.info(f"OTP код: {config.get('otp')}")
    
    # Перевіряємо токен бота
    logger.debug("Перевіряємо BOT_TOKEN...")
    bot_token = get_bot_token()
    if not bot_token:
        logger.error("BOT_TOKEN не знайдено в БД!")
        logger.error("Бот не буде запущено. Введіть токен в налаштуваннях")
        raise ValueError("BOT_TOKEN не знайдено")
    
    logger.debug("Валідуємо BOT_TOKEN...")
    if not validate_bot_token(bot_token):
        logger.error("BOT_TOKEN невалідний!")
        logger.error("Бот не буде запущено. Перевірте правильність токену в налаштуваннях")
        raise ValueError("BOT_TOKEN невалідний")
    
    logger.info("BOT_TOKEN валідний, створюємо бота та dispatcher...")
    
    # Створюємо бота та dispatcher
    logger.debug("Створюємо Bot об'єкт...")
    bot = Bot(token=bot_token)
    logger.debug("Створюємо Dispatcher...")
    dp = Dispatcher()
    
    # Реєструємо обробники
    logger.debug("Реєструємо обробники...")
    register_handlers(dp, config)
    logger.info("Обробники зареєстровано")
    
    try:
        logger.info("Бот запущено, очікуємо повідомлення...")
        logger.info("Запускаємо polling...")
        await dp.start_polling(bot)
        logger.info("Polling завершено")
    except asyncio.CancelledError:
        logger.info("Бот зупинено (CancelledError)")
        raise
    except Exception as e:
        logger.error(f"Помилка при роботі бота: {e}", exc_info=True)
        raise
    finally:
        await bot.session.close()

