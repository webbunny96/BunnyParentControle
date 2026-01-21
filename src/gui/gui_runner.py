"""Модуль для запуску GUI додатку в окремому потоці."""

import threading
import sys
from typing import Optional

from src.gui.tray_app import TrayApp
from src.utils.logger import setup_logging, get_logger

# Налаштування логування
setup_logging(level=20)  # INFO level
logger = get_logger(__name__)


class GUIThread(threading.Thread):
    """Потік для запуску GUI додатку."""
    
    def __init__(self):
        super().__init__(daemon=True)
        self.app: Optional[TrayApp] = None
        self._stop_event = threading.Event()
    
    def run(self) -> None:
        """Запускає GUI додаток в потоці."""
        logger.info("Запуск GUI додатку в окремому потоці...")
        
        try:
            logger.debug("Створюємо TrayApp...")
            self.app = TrayApp()
            logger.info("TrayApp створено, запускаємо run()...")
            self.app.run()
            logger.info("GUI додаток завершив роботу")
        except KeyboardInterrupt:
            logger.info("GUI додаток зупинено (KeyboardInterrupt)")
        except Exception as e:
            logger.error(f"Критична помилка в GUI додатку: {e}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        finally:
            logger.debug("Встановлюємо stop_event")
            self._stop_event.set()
    
    def stop(self) -> None:
        """Зупиняє GUI додаток."""
        if self.app:
            try:
                self.app.quit_app()
            except Exception as e:
                logger.error(f"Помилка при зупинці GUI: {e}")
    
    def is_running(self) -> bool:
        """Перевіряє чи GUI додаток ще працює."""
        # Перевіряємо тільки чи потік живий
        # _stop_event може бути встановлено навіть якщо GUI працює нормально
        return self.is_alive()


def run_gui_thread() -> GUIThread:
    """Запускає GUI додаток в окремому потоці.
    
    Returns:
        GUIThread: Потік з GUI додатком
    """
    gui_thread = GUIThread()
    gui_thread.start()
    return gui_thread

