"""Модуль для запуску вікна блокування."""

import threading
from typing import Optional

from src.gui.blocking_window import BlockingWindow
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BlockingWindowThread(threading.Thread):
    """Потік для запуску вікна блокування."""
    
    def __init__(self, countdown_seconds: int = 60, otp: Optional[str] = None, bot_url: Optional[str] = None):
        super().__init__(daemon=True)
        self.countdown_seconds = countdown_seconds
        self.otp = otp
        self.bot_url = bot_url
        self.window: Optional[BlockingWindow] = None
        self._stop_event = threading.Event()
    
    def run(self) -> None:
        """Запускає вікно блокування в потоці."""
        try:
            self.window = BlockingWindow(
                countdown_seconds=self.countdown_seconds,
                otp=self.otp,
                bot_url=self.bot_url
            )
            self.window.run()
        except Exception as e:
            logger.error(f"Помилка при роботі вікна блокування: {e}", exc_info=True)
        finally:
            self._stop_event.set()
    
    def stop(self) -> None:
        """Зупиняє вікно блокування."""
        if self.window and self.window.root:
            try:
                self.window.root.quit()
                self.window.root.destroy()
            except Exception as e:
                logger.error(f"Помилка при зупинці вікна блокування: {e}")
    
    def is_running(self) -> bool:
        """Перевіряє чи вікно блокування ще працює."""
        return self.is_alive() and not self._stop_event.is_set()


def run_blocking_window(countdown_seconds: int = 60, otp: Optional[str] = None, bot_url: Optional[str] = None) -> BlockingWindowThread:
    """Запускає вікно блокування в окремому потоці.
    
    Args:
        countdown_seconds: Кількість секунд до вимкнення
        otp: OTP код для відображення (опціонально)
        bot_url: URL бота для QR-коду (опціонально)
        
    Returns:
        BlockingWindowThread: Потік з вікном блокування
    """
    thread = BlockingWindowThread(countdown_seconds, otp, bot_url)
    thread.start()
    return thread


