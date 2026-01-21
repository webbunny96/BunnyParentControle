"""Точка входу для GUI додатку."""

import sys
from pathlib import Path

# Додаємо корінь проекту до шляху для імпортів
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.gui.tray_app import TrayApp
from src.utils.logger import setup_logging, get_logger

# Налаштування логування
setup_logging(level=20)  # INFO level
logger = get_logger(__name__)


def main() -> None:
    """Головна функція для запуску GUI додатку."""
    logger.info("Запуск GUI додатку...")
    
    try:
        app = TrayApp()
        app.run()
    except KeyboardInterrupt:
        logger.info("GUI додаток зупинено (KeyboardInterrupt)")
    except Exception as e:
        logger.error(f"Критична помилка в GUI додатку: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()






