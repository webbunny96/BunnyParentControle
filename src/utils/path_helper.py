"""Допоміжний модуль для роботи з шляхами та визначення режиму запуску."""

import sys
from pathlib import Path


def is_frozen() -> bool:
    """Перевіряє, чи запущено програму як зібраний exe файл.
    
    Returns:
        bool: True якщо програма запущена як exe, False якщо як Python скрипт
    """
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_base_path() -> Path:
    """Повертає базовий шлях до програми.
    
    Якщо програма запущена як exe, повертає директорію з exe файлом.
    Якщо як Python скрипт, повертає директорію з main.py.
    
    Returns:
        Path: Базовий шлях до програми
    """
    if is_frozen():
        # Якщо зібрано в exe, sys.executable вказує на exe файл
        return Path(sys.executable).parent
    else:
        # Якщо запущено як скрипт, повертаємо директорію з main.py
        return Path(__file__).parent.parent.parent


def get_executable_name(script_name: str, relative_path: str = "") -> str:
    """Повертає ім'я exe файлу для скрипта.
    
    Args:
        script_name: Ім'я Python скрипта (наприклад, 'main.py', 'blocking_window.py')
        relative_path: Відносний шлях від кореня проекту (наприклад, 'src/gui/')
        
    Returns:
        str: Ім'я exe файлу (наприклад, 'main.exe', 'gui_main.exe', 'blocking_window.exe')
    """
    base_name = Path(script_name).stem
    
    # Спеціальна обробка для main.py в підпапках
    if base_name == "main" and relative_path:
        # Визначаємо назву exe на основі шляху
        path_parts = Path(relative_path).parts
        if len(path_parts) >= 2:
            # src/gui/main.py -> gui_main.exe
            # src/bot/main.py -> bot_main.exe
            folder_name = path_parts[-1]  # Остання частина шляху
            return f"{folder_name}_main.exe"
    
    return f"{base_name}.exe"


def get_script_path(script_name: str, relative_path: str = "") -> Path:
    """Повертає шлях до скрипта або exe файлу.
    
    Спочатку перевіряє чи існує exe файл, якщо ні - повертає шлях до Python скрипта.
    
    Args:
        script_name: Ім'я Python скрипта (наприклад, 'main.py', 'blocking_window.py')
        relative_path: Відносний шлях від кореня проекту (наприклад, 'src/gui/')
        
    Returns:
        Path: Шлях до exe файлу або Python скрипта
    """
    base_path = get_base_path()
    
    # Якщо запущено як exe, шукаємо exe файл
    if is_frozen():
        exe_name = get_executable_name(script_name, relative_path)
        exe_path = base_path / exe_name
        if exe_path.exists():
            return exe_path
    
    # Якщо exe не знайдено або запущено як скрипт, повертаємо шлях до Python скрипта
    if relative_path:
        return base_path / relative_path / script_name
    return base_path / script_name


def get_executable_command(script_name: str, relative_path: str = "") -> list[str]:
    """Повертає команду для запуску скрипта або exe файлу.
    
    Args:
        script_name: Ім'я Python скрипта (наприклад, 'main.py', 'blocking_window.py')
        relative_path: Відносний шлях від кореня проекту (наприклад, 'src/gui/')
        
    Returns:
        list[str]: Список аргументів для subprocess.Popen
                  Якщо знайдено exe: [шлях_до_exe]
                  Якщо скрипт: [sys.executable, шлях_до_скрипта]
    """
    script_path = get_script_path(script_name, relative_path)
    
    # Якщо це exe файл, запускаємо його напряму
    if script_path.suffix.lower() == '.exe':
        return [str(script_path)]
    
    # Інакше запускаємо як Python скрипт
    return [sys.executable, str(script_path)]

