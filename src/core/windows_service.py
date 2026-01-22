"""Модуль для роботи як Windows служба.

Цей модуль забезпечує інтеграцію з Windows Service Control Manager.
"""

import sys
import os
import asyncio
import threading
from pathlib import Path

# Додаємо шлях до кореня проекту в sys.path для імпортів
if __name__ == "__main__":
    # Якщо запущено як служба, потрібно додати шлях до проекту
    exe_dir = Path(sys.executable).parent
    project_root = exe_dir
    if project_root not in sys.path:
        sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logging, get_logger
from src.utils.path_helper import get_base_path

# Налаштовуємо логування для служби
log_file = get_base_path() / "service.log"
setup_logging(level=20, log_file=log_file)  # INFO level

logger = get_logger(__name__)

try:
    import win32serviceutil
    import win32service
    
    class ParentControlService(win32serviceutil.ServiceFramework):
        """Клас Windows служби для батьківського контролю."""
        
        _svc_name_ = "ParentControlService"
        _svc_display_name_ = "Parent Control Service"
        _svc_description_ = "Служба батьківського контролю для управління часом використання комп'ютера"
        
        def __init__(self, args):
            """Ініціалізує службу."""
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = threading.Event()
            self.main_task = None
            self.loop = None
            self.service_thread = None
            
        def SvcStop(self):
            """Зупиняє службу."""
            logger.info("Зупинка служби батьківського контролю...")
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            
            self.stop_event.set()
            
            if self.loop and not self.loop.is_closed():
                # Скасовуємо всі задачі
                if self.main_task and not self.main_task.done():
                    self.loop.call_soon_threadsafe(self.main_task.cancel)
            
            logger.info("Служба зупинена")
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)
        
        def SvcDoRun(self):
            """Запускає службу."""
            logger.info("Запуск служби батьківського контролю...")
            
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            
            # Створюємо новий event loop в окремому потоці
            def run_service():
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                
                try:
                    # Імпортуємо main функцію
                    from main import main
                    
                    # Запускаємо main без GUI
                    self.main_task = self.loop.create_task(main(launch_gui=False))
                    
                    # Запускаємо event loop
                    self.loop.run_until_complete(self.main_task)
                    
                except Exception as e:
                    logger.error(f"Помилка в службі: {e}", exc_info=True)
                finally:
                    if self.loop and not self.loop.is_closed():
                        self.loop.close()
            
            # Запускаємо службу в окремому потоці
            self.service_thread = threading.Thread(target=run_service, daemon=False)
            self.service_thread.start()
            
            # Чекаємо поки потік не завершиться
            self.service_thread.join()
            
            logger.info("Служба завершена")

except ImportError:
    # Якщо pywin32 не встановлено, створюємо заглушку
    class ParentControlService:
        """Заглушка для ParentControlService якщо pywin32 не встановлено."""
        pass


def main():
    """Головна функція для запуску як служби Windows."""
    try:
        import win32serviceutil
        
        # Запускаємо службу через win32serviceutil
        win32serviceutil.HandleCommandLine(ParentControlService)
        
    except ImportError:
        logger.error("Модуль pywin32 не встановлено. Встановіть його: pip install pywin32")
        # Якщо pywin32 не встановлено, запускаємо як звичайну програму
        from main import main as main_func
        asyncio.run(main_func(launch_gui=False))
    except Exception as e:
        logger.error(f"Помилка запуску служби: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # Якщо запущено з аргументом --service, запускаємо як службу
    if "--service" in sys.argv:
        main()
    else:
        # Інакше запускаємо звичайну програму
        from main import main as main_func
        asyncio.run(main_func(launch_gui=True))
