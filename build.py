"""Скрипт для збірки всіх компонентів в exe файли за допомогою PyInstaller."""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Виконує команду та виводить результат.
    
    Args:
        cmd: Список аргументів команди
        description: Опис того, що виконується
        
    Returns:
        bool: True якщо команда виконалась успішно, False інакше
    """
    print(f"\n{'='*60}")
    print(f"Збірка: {description}")
    print(f"Команда: {' '.join(cmd)}")
    print(f"{'='*60}\n")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✓ {description} - успішно!\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Помилка при збірці {description}: {e}\n")
        return False
    except FileNotFoundError:
        print(f"✗ PyInstaller не знайдено! Встановіть його: pip install pyinstaller\n")
        return False


def main():
    """Головна функція для збірки всього проекту в один exe файл."""
    print("="*60)
    print("Збірка Parent Control в один exe файл")
    print("="*60)
    
    # Перевіряємо чи PyInstaller встановлено
    try:
        import PyInstaller
    except ImportError:
        print("Помилка: PyInstaller не встановлено!")
        print("Встановіть його: pip install pyinstaller")
        sys.exit(1)
    
    # Збираємо все в один файл
    spec_file = "parent_control.spec"
    
    if not Path(spec_file).exists():
        print(f"Помилка: {spec_file} не знайдено!")
        sys.exit(1)
    
    description = "Parent Control (parent_control.exe)"
    cmd = ["pyinstaller", "--clean", spec_file]
    
    if run_command(cmd, description):
        print("\n" + "="*60)
        print("Підсумок збірки:")
        print("="*60)
        print("✓ Проект успішно зібрано в один exe файл!")
        print("\nЗібраний exe файл знаходиться в директорії 'dist/':")
        print("  - dist/parent_control.exe")
        print("\nДля запуску скопіюйте exe файл разом з:")
        print("  - config.json (або створіть новий при першому запуску)")
        print("  - .env файл з BOT_TOKEN")
        print("\nЗапуск:")
        print("  parent_control.exe")
        print("  або")
        print("  parent_control.exe --no-gui  # без GUI")
    else:
        print("\n" + "="*60)
        print("Помилка збірки!")
        print("="*60)
        sys.exit(1)


if __name__ == "__main__":
    main()

