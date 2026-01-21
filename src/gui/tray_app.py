"""Модуль system tray додатку."""

import os
import signal
import threading
import tkinter as tk
from tkinter import messagebox
from typing import Optional

from PIL import Image as PILImage
import pystray

from src.core.config import load_config
from src.gui.password_dialog import PasswordDialog
from src.gui.settings_window import SettingsWindow
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TrayApp:
    """Додаток у system tray для управління системою батьківського контролю."""
    
    def __init__(self) -> None:
        """Ініціалізує додаток у system tray."""
        logger.debug("Ініціалізація TrayApp...")
        
        # Створюємо головне вікно спочатку
        self.root: Optional[tk.Tk] = None
        self.icon: Optional[pystray.Icon] = None
        self.settings_window: Optional[SettingsWindow] = None
        self.quit_requested = False
        
        logger.debug("Створюємо головне вікно...")
        self.root = tk.Tk()
        self.root.withdraw()  # Ховаємо вікно
        # ВАЖЛИВО: Забороняємо закриття root вікна через X кнопку
        # Root вікно має залишатися живим для підтримки tray іконки
        self.root.protocol("WM_DELETE_WINDOW", self._on_root_close)
        # Переконаємося що root вікно не закривається при закритті дочірніх вікон
        self.root.wm_attributes("-topmost", False)  # Не робимо завжди поверх інших
        
        # Завантажуємо конфігурацію після створення вікна
        logger.debug("Завантажуємо конфігурацію...")
        try:
            self.config = load_config()
            logger.debug("Конфігурація завантажена успішно")
        except Exception as e:
            logger.error(f"Помилка завантаження конфігурації: {e}", exc_info=True)
            # Створюємо дефолтну конфігурацію якщо не вдалося завантажити
            from src.core.config import create_default_config
            self.config = create_default_config()
        
        # Перевіряємо чи це перший запуск
        # Не викликаємо show_settings тут - це буде зроблено в run()
        # щоб уникнути подвійного виклику
        self._is_first_run = not self.config.get("parent_password")
        if not self._is_first_run:
            # Якщо не перший запуск, налаштовуємо tray одразу
            self._setup_tray()
    
    def _on_root_close(self) -> None:
        """Обробник закриття головного вікна."""
        logger.debug("Спроба закрити root вікно")
        
        # Перевіряємо чи є відкрите вікно налаштувань
        if self.settings_window and self.settings_window.window.winfo_exists():
            logger.debug("Вікно налаштувань відкрите, закриваємо його замість root")
            # Закриваємо вікно налаштувань замість root
            try:
                self.settings_window.window.destroy()
            except:
                pass
            return
        
        config = load_config()
        if not config.get("parent_password"):
            messagebox.showwarning(
                "Увага",
                "Необхідно встановити батьківський пароль перед закриттям програми!"
            )
        else:
            # Потрібен пароль для виходу
            dialog = PasswordDialog(self.root)
            self.root.wait_window(dialog.dialog)
            if dialog.result:
                self.quit_app()
            else:
                # Якщо пароль невірний, не закриваємо root вікно
                # Просто ховаємо його
                if self.root:
                    self.root.withdraw()
    
    def _setup_tray(self) -> None:
        """Налаштовує system tray icon."""
        # Створюємо зображення для іконки (простий синій квадрат)
        image = PILImage.new('RGB', (64, 64), color=(70, 130, 180))
        
        # Створюємо меню
        menu = pystray.Menu(
            pystray.MenuItem("Відкрити налаштування", self._show_settings_from_tray),
            pystray.MenuItem("Вихід", self._quit_app_with_password)
        )
        
        self.icon = pystray.Icon("ParentControl", image, "Parent Control", menu)
        
        # Запускаємо іконку в окремому потоці
        threading.Thread(target=self.icon.run, daemon=True).start()
        logger.info("System tray icon запущено")
    
    def _show_settings_from_tray(self, icon=None, item=None) -> None:
        """Показує налаштування після перевірки пароля (викликається з tray thread).
        
        Args:
            icon: Об'єкт іконки (не використовується)
            item: Об'єкт пункту меню (не використовується)
        """
        logger.debug("Клік на 'Відкрити налаштування' з tray меню")
        
        # Плануємо GUI операцію в головному потоці
        if self.root:
            try:
                self.root.after(0, self._show_settings_from_tray_impl)
                self.root.update_idletasks()
            except Exception as e:
                logger.error(f"Помилка при плануванні показу налаштувань: {e}", exc_info=True)
                # Альтернативний спосіб - прямий виклик
                try:
                    self._show_settings_from_tray_impl()
                except Exception as e2:
                    logger.error(f"Помилка при прямому виклику: {e2}", exc_info=True)
        else:
            logger.error("Root вікно не існує!")
    
    def _show_settings_from_tray_impl(self) -> None:
        """Реалізація показу налаштувань (виконується в головному потоці)."""
        try:
            logger.debug("Відкриваємо налаштування...")
            
            # Робимо root вікно видимим для показу діалогу
            if self.root:
                self.root.deiconify()
                self.root.update_idletasks()
                self.root.lift()
                self.root.focus_force()
                self.root.update()
            
            # Показуємо діалог пароля
            logger.debug("Створюємо діалог пароля...")
            dialog = PasswordDialog(self.root)
            
            if self.root:
                self.root.wait_window(dialog.dialog)
            
            logger.debug(f"Пароль введено, результат: {dialog.result}")
            
            # Ховаємо root вікно після закриття діалогу
            if self.root:
                self.root.withdraw()
            
            if dialog.result:
                logger.debug("Пароль правильний, відкриваємо налаштування...")
                self.show_settings(first_run=False)
            else:
                logger.debug("Пароль невірний або скасовано")
                
        except Exception as e:
            logger.error(f"Помилка при відкритті налаштувань: {e}", exc_info=True)
            if self.root:
                self.root.withdraw()
    
    def show_settings(self, first_run: bool = False) -> None:
        """Показує вікно налаштувань.
        
        Args:
            first_run: Чи це перший запуск
        """
        try:
            # Робимо root вікно видимим перед показом налаштувань (якщо не перший запуск)
            if not first_run and self.root:
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
            
            # Закриваємо попереднє вікно налаштувань якщо воно існує
            if self.settings_window:
                try:
                    self.settings_window.window.destroy()
                except Exception:
                    pass
                self.settings_window = None
            
            # Створюємо нове вікно налаштувань
            self.settings_window = SettingsWindow(self.root, is_first_run=first_run)
            
            if first_run:
                # Очікуємо поки налаштування будуть збережені
                try:
                    self.root.wait_window(self.settings_window.window)
                except tk.TclError:
                    # Вікно вже закрите, це нормально
                    logger.debug("Вікно налаштувань вже закрите")
                
                # Очищаємо посилання на вікно налаштувань
                self.settings_window = None
                
                # Переконаємося що root вікно ще існує перед продовженням
                if not self.root or not self.root.winfo_exists():
                    logger.error("Root вікно було закрите після збереження налаштувань!")
                    return
                
                # Перезавантажуємо конфігурацію після збереження
                self.config = load_config()
                
                # Після першого запуску налаштовуємо tray іконку
                if self.config.get("parent_password"):
                    logger.info("Пароль встановлено, налаштовуємо tray іконку...")
                    self._is_first_run = False  # Позначаємо що перший запуск завершено
                    self._setup_tray()
                    # Ховаємо root вікно після налаштування tray
                    # Але root вікно має залишатися живим для підтримки tray іконки
                    if self.root and self.root.winfo_exists():
                        try:
                            self.root.withdraw()
                            logger.info("Перший запуск завершено, tray іконка активна, root вікно приховано")
                        except tk.TclError as e:
                            logger.error(f"Помилка при приховуванні root вікна: {e}")
                    else:
                        logger.error("Root вікно не існує після налаштування tray!")
                else:
                    logger.warning("Пароль не встановлено після першого запуску")
            else:
                # Очікуємо закриття вікна налаштувань
                # Використовуємо try-except щоб переконатися що root не закривається
                try:
                    self.root.wait_window(self.settings_window.window)
                except tk.TclError:
                    # Вікно вже закрите, це нормально
                    logger.debug("Вікно налаштувань вже закрите")
                
                # Очищаємо посилання на вікно налаштувань
                self.settings_window = None
                
                # Переконаємося що root вікно існує та не закрите
                if self.root:
                    try:
                        # Перевіряємо чи root вікно ще існує
                        self.root.winfo_exists()
                        # Ховаємо root вікно після закриття налаштувань
                        # Але root вікно залишається живим для підтримки tray іконки
                        self.root.withdraw()
                        logger.debug("Вікно налаштувань закрито, root вікно залишається живим для tray")
                    except tk.TclError:
                        logger.error("Root вікно було закрите! Це не повинно статися")
                        # Якщо root вікно закрилося, трей іконка також зникне
                        # Але це не повинно статися
                    
        except Exception as e:
            logger.error(f"Помилка при показі налаштувань: {e}", exc_info=True)
            # Навіть при помилці root вікно має залишатися живим
            if self.root:
                try:
                    self.root.withdraw()
                except:
                    pass
    
    def _quit_app_with_password(self, icon=None, item=None) -> None:
        """Запит на вихід - потребує пароль (викликається з tray thread).
        
        Args:
            icon: Об'єкт іконки (не використовується)
            item: Об'єкт пункту меню (не використовується)
        """
        logger.debug("Клік на 'Вихід' з tray меню")
        
        # Плануємо GUI операцію в головному потоці
        if self.root:
            try:
                self.root.after(0, self._quit_app_with_password_impl)
            except Exception as e:
                logger.error(f"Помилка при плануванні закриття: {e}", exc_info=True)
                try:
                    self._quit_app_with_password_impl()
                except Exception as e2:
                    logger.error(f"Помилка при прямому виклику: {e2}", exc_info=True)
        else:
            logger.error("Root вікно не існує!")
    
    def _quit_app_with_password_impl(self) -> None:
        """Реалізація виходу з програми (потребує пароль)."""
        try:
            logger.debug("Запит на вихід з програми...")
            
            # Робимо root вікно видимим для показу діалогу
            if self.root:
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
                self.root.update()
            
            config = load_config()
            if not config.get("parent_password"):
                messagebox.showwarning(
                    "Увага",
                    "Необхідно встановити батьківський пароль перед закриттям програми!"
                )
                if self.root:
                    self.root.withdraw()
                return
            
            # Потрібен пароль для виходу
            logger.debug("Створюємо діалог пароля для виходу...")
            dialog = PasswordDialog(self.root)
            
            if self.root:
                self.root.wait_window(dialog.dialog)
            
            logger.debug(f"Пароль введено, результат: {dialog.result}")
            
            # Ховаємо root вікно (якщо не виходимо)
            if self.root:
                self.root.withdraw()
            
            if dialog.result:
                logger.info("Пароль правильний, виходимо з програми...")
                self.quit_app()
            else:
                logger.debug("Пароль невірний або скасовано, залишаємося")
                
        except Exception as e:
            logger.error(f"Помилка при закритті програми: {e}", exc_info=True)
            if self.root:
                self.root.withdraw()
    
    def quit_app(self) -> None:
        """Фактично виходить з програми."""
        self.quit_requested = True
        
        if self.icon:
            self.icon.stop()
        
        if self.root:
            self.root.quit()
        
        logger.info("Вихід з програми")
        os._exit(0)
    
    def _handle_signal(self, signum, frame) -> None:
        """Обробник системних сигналів - потребує пароль для виходу.
        
        Args:
            signum: Номер сигналу
            frame: Поточний кадр стеку
        """
        config = load_config()
        if not config.get("parent_password"):
            # Не можна вийти без пароля
            return
        
        # Плануємо перевірку пароля в головному потоці
        if self.root:
            self.root.after(0, self._quit_app_with_password_impl)
    
    def run(self) -> None:
        """Запускає додаток."""
        # Налаштовуємо обробники сигналів тільки в головному потоці
        # (signal handlers працюють тільки в головному потоці інтерпретатора)
        if threading.current_thread() is threading.main_thread():
            try:
                signal.signal(signal.SIGINT, self._handle_signal)
                signal.signal(signal.SIGTERM, self._handle_signal)
            except (ValueError, OSError) as e:
                # Ігноруємо помилки встановлення signal handlers
                # (може не працювати на Windows або в деяких середовищах)
                logger.debug(f"Не вдалося встановити signal handlers: {e}")
        else:
            logger.debug("GUI запущено в окремому потоці, signal handlers не встановлюємо")
        
        # Перевіряємо чи це перший запуск (немає пароля)
        if self._is_first_run:
            # Перший запуск - показуємо налаштування
            logger.info("Перший запуск - показуємо вікно налаштувань")
            self.show_settings(first_run=True)
            # Після збереження налаштувань show_settings() налаштує tray іконку
            # та приховає root вікно, тому просто запускаємо mainloop
            self.root.mainloop()
        else:
            # Звичайний запуск - tray вже налаштовано в __init__
            logger.info("Звичайний запуск - tray іконка активна")
            # Запускаємо mainloop для підтримки GUI відгуку
            self.root.mainloop()






