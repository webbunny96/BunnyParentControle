"""Модуль для управління Windows службою.

Модуль надає функції для встановлення, видалення та перевірки статусу служби Windows.
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Optional

from src.utils.logger import get_logger
from src.utils.path_helper import get_base_path, is_frozen

logger = get_logger(__name__)

# Назва служби Windows
SERVICE_NAME = "ParentControlService"
SERVICE_DISPLAY_NAME = "Parent Control Service"
SERVICE_DESCRIPTION = "Служба батьківського контролю для управління часом використання комп'ютера"


def is_admin() -> bool:
    """Перевіряє чи запущено з правами адміністратора.
    
    Returns:
        bool: True якщо є права адміністратора
    """
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def get_service_executable_path() -> Path:
    """Отримує шлях до exe файлу для служби.
    
    Returns:
        Path: Шлях до exe файлу
    """
    if is_frozen():
        # Якщо запущено як exe, використовуємо поточний exe
        return Path(sys.executable)
    else:
        # Якщо запущено як скрипт, використовуємо pythonw.exe
        python_exe = Path(sys.executable)
        # Замінюємо python.exe на pythonw.exe для запуску без консолі
        if python_exe.name == "python.exe":
            pythonw_exe = python_exe.parent / "pythonw.exe"
            if pythonw_exe.exists():
                return pythonw_exe
        return python_exe


def install_service() -> bool:
    """Встановлює службу Windows.
    
    Returns:
        bool: True якщо служба встановлена успішно
    """
    if not is_admin():
        logger.error("Для встановлення служби потрібні права адміністратора")
        return False
    
    try:
        logger.info(f"Встановлення служби {SERVICE_NAME}...")
        
        exe_path = get_service_executable_path()
        
        # Якщо це exe файл, використовуємо sc.exe для встановлення служби
        if is_frozen():
            # Для exe файлу використовуємо sc.exe з правильними параметрами
            # Exe файл буде запускатися з аргументом --no-gui для роботи без GUI
            service_path = str(exe_path)
            
            # Створюємо команду для sc.exe
            # Важливо: між = та значенням має бути пробіл
            # Аргументи мають бути всередині binPath= в лапках
            # Формат: sc.exe create ServiceName binPath= "path\to\exe --no-gui" start= auto DisplayName= "Name"
            # Всі аргументи мають бути всередині лапок binPath
            bin_path_with_args = f'"{service_path} --no-gui"'
            
            # Формуємо команду як один рядок для shell=True
            # Використовуємо правильний синтаксис sc.exe
            cmd_line = (
                f'sc.exe create {SERVICE_NAME} '
                f'binPath= {bin_path_with_args} '
                f'start= auto '
                f'DisplayName= "{SERVICE_DISPLAY_NAME}"'
            )
            
            logger.info(f"Виконуємо команду: {cmd_line}")
            result = subprocess.run(cmd_line, capture_output=True, text=True, shell=True)
            
            if result.returncode != 0:
                # Перевіряємо чи служба вже існує
                error_text = result.stderr.lower()
                if "уже існує" in error_text or "already exists" in error_text or "уже существует" in error_text:
                    logger.warning(f"Служба {SERVICE_NAME} вже існує")
                    return True
                
                logger.error(f"Помилка встановлення служби: {result.stderr}")
                if result.stdout:
                    logger.info(f"Вивід команди: {result.stdout}")
                return False
            
            logger.info("Служба успішно встановлена через sc.exe")
            
            # Додаємо опис служби
            try:
                desc_cmd = [
                    "sc.exe",
                    "description",
                    SERVICE_NAME,
                    SERVICE_DESCRIPTION
                ]
                desc_result = subprocess.run(desc_cmd, capture_output=True, text=True, shell=True)
                if desc_result.returncode != 0:
                    logger.warning(f"Не вдалося встановити опис служби: {desc_result.stderr}")
            except Exception as e:
                logger.warning(f"Не вдалося встановити опис служби: {e}")
            
            return True
        else:
            # Для скрипта використовуємо win32serviceutil через Python
            try:
                import win32serviceutil
                import win32service
                
                module_path = str(get_base_path() / "src" / "core" / "windows_service.py")
                class_name = "ParentControlService"
                
                logger.info(f"Модуль служби: {module_path}:{class_name}")
                
                # Шукаємо python.exe в системі
                import shutil
                python_exe = shutil.which("python.exe")
                if not python_exe:
                    logger.error("Не знайдено python.exe в системі. Потрібен Python для встановлення служби.")
                    return False
                
                cmd = [
                    python_exe,
                    "-m", "win32serviceutil",
                    "install",
                    f"{module_path}:{class_name}"
                ]
                
                logger.info(f"Виконуємо команду: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(get_base_path()))
                
                if result.returncode != 0:
                    logger.error(f"Помилка встановлення служби: {result.stderr}")
                    if result.stdout:
                        logger.info(f"Вивід команди: {result.stdout}")
                    return False
                
                logger.info("Служба успішно встановлена через командний рядок")
                return True
            except ImportError:
                logger.error("Модуль pywin32 не встановлено. Встановіть його: pip install pywin32")
                return False
        
    except Exception as e:
        logger.error(f"Помилка встановлення служби: {e}", exc_info=True)
        return False


def uninstall_service() -> bool:
    """Видаляє службу Windows.
    
    Returns:
        bool: True якщо служба видалена успішно
    """
    if not is_admin():
        logger.error("Для видалення служби потрібні права адміністратора")
        return False
    
    try:
        logger.info(f"Видалення служби {SERVICE_NAME}...")
        
        # Використовуємо sc.exe для видалення служби (працює для exe та скриптів)
        cmd = [
            "sc.exe",
            "delete",
            SERVICE_NAME
        ]
        
        logger.info(f"Виконуємо команду: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        
        if result.returncode != 0:
            # Перевіряємо чи служба не існує
            error_text = result.stderr.lower()
            if "не існує" in error_text or "does not exist" in error_text or "не существует" in error_text:
                logger.warning(f"Служба {SERVICE_NAME} не існує")
                return True
            
            logger.error(f"Помилка видалення служби: {result.stderr}")
            if result.stdout:
                logger.info(f"Вивід команди: {result.stdout}")
            
            # Спробуємо через win32serviceutil якщо доступний
            try:
                import win32serviceutil
                win32serviceutil.RemoveService(SERVICE_NAME)
                logger.info(f"Служба {SERVICE_NAME} успішно видалена через win32serviceutil")
                return True
            except ImportError:
                pass
            
            return False
        
        logger.info(f"Служба {SERVICE_NAME} успішно видалена через sc.exe")
        return True
        
    except Exception as e:
        logger.error(f"Помилка видалення служби: {e}", exc_info=True)
        return False


def is_service_installed() -> bool:
    """Перевіряє чи встановлена служба.
    
    Returns:
        bool: True якщо служба встановлена
    """
    try:
        # Використовуємо sc.exe для перевірки (працює для exe та скриптів)
        cmd = [
            "sc.exe",
            "query",
            SERVICE_NAME
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        
        if result.returncode == 0:
            return True
        
        # Спробуємо через win32serviceutil якщо доступний
        try:
            import win32serviceutil
            win32serviceutil.QueryServiceStatus(SERVICE_NAME)
            return True
        except ImportError:
            pass
        except Exception:
            pass
        
        return False
            
    except Exception:
        return False


def is_service_running() -> bool:
    """Перевіряє чи запущена служба.
    
    Returns:
        bool: True якщо служба запущена
    """
    try:
        # Використовуємо sc.exe для перевірки статусу
        cmd = [
            "sc.exe",
            "query",
            SERVICE_NAME
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        
        if result.returncode == 0:
            # Перевіряємо чи в виводі є "RUNNING"
            output = result.stdout.upper()
            return "RUNNING" in output
        
        # Спробуємо через win32serviceutil якщо доступний
        try:
            import win32serviceutil
            status = win32serviceutil.QueryServiceStatus(SERVICE_NAME)
            # Статус 4 означає що служба запущена
            return status[1] == 4
        except ImportError:
            pass
        except Exception:
            pass
        
        return False
        
    except Exception:
        return False


def start_service() -> bool:
    """Запускає службу.
    
    Returns:
        bool: True якщо служба запущена успішно
    """
    if not is_admin():
        logger.error("Для запуску служби потрібні права адміністратора")
        return False
    
    try:
        logger.info(f"Запуск служби {SERVICE_NAME}...")
        
        # Використовуємо sc.exe для запуску служби
        cmd = [
            "sc.exe",
            "start",
            SERVICE_NAME
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        
        if result.returncode != 0:
            logger.error(f"Помилка запуску служби: {result.stderr}")
            if result.stdout:
                logger.info(f"Вивід команди: {result.stdout}")
            
            # Спробуємо через win32serviceutil якщо доступний
            try:
                import win32serviceutil
                win32serviceutil.StartService(SERVICE_NAME)
                logger.info(f"Служба {SERVICE_NAME} запущена через win32serviceutil")
                return True
            except ImportError:
                pass
            
            return False
        
        logger.info(f"Служба {SERVICE_NAME} запущена через sc.exe")
        return True
        
    except Exception as e:
        logger.error(f"Помилка запуску служби: {e}", exc_info=True)
        return False


def stop_service() -> bool:
    """Зупиняє службу.
    
    Returns:
        bool: True якщо служба зупинена успішно
    """
    if not is_admin():
        logger.error("Для зупинки служби потрібні права адміністратора")
        return False
    
    try:
        logger.info(f"Зупинка служби {SERVICE_NAME}...")
        
        # Використовуємо sc.exe для зупинки служби
        cmd = [
            "sc.exe",
            "stop",
            SERVICE_NAME
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        
        if result.returncode != 0:
            logger.error(f"Помилка зупинки служби: {result.stderr}")
            if result.stdout:
                logger.info(f"Вивід команди: {result.stdout}")
            
            # Спробуємо через win32serviceutil якщо доступний
            try:
                import win32serviceutil
                win32serviceutil.StopService(SERVICE_NAME)
                logger.info(f"Служба {SERVICE_NAME} зупинена через win32serviceutil")
                return True
            except ImportError:
                pass
            
            return False
        
        logger.info(f"Служба {SERVICE_NAME} зупинена через sc.exe")
        return True
        
    except Exception as e:
        logger.error(f"Помилка зупинки служби: {e}", exc_info=True)
        return False
