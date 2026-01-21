"""Модуль діалогу введення пароля."""

import tkinter as tk
from tkinter import messagebox
from typing import Optional

from src.core.config import check_password
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PasswordDialog:
    """Діалог для введення батьківського пароля."""
    
    def __init__(self, parent: Optional[tk.Tk] = None) -> None:
        """Ініціалізує діалог введення пароля.
        
        Args:
            parent: Батьківське вікно (опціонально)
        """
        self.result: Optional[bool] = None
        
        # Створюємо діалог
        self.dialog = tk.Toplevel(parent) if parent else tk.Tk()
        self.dialog.title("Введіть батьківський пароль")
        self.dialog.geometry("300x150")
        self.dialog.resizable(False, False)
        
        # Центруємо вікно
        self._center_window()
        
        # Налаштовуємо діалог як модальний
        self.dialog.attributes("-topmost", True)
        self.dialog.grab_set()
        self.dialog.deiconify()
        self.dialog.update_idletasks()
        self.dialog.lift()
        self.dialog.focus_force()
        self.dialog.update()
        
        logger.debug("PasswordDialog створено")
        
        self._create_widgets()
        
        # Обробка закриття діалогу
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _center_window(self) -> None:
        """Центрує вікно на екрані."""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')
    
    def _create_widgets(self) -> None:
        """Створює віджети діалогу."""
        # Мітка з інструкцією
        tk.Label(
            self.dialog,
            text="Введіть батьківський пароль:",
            font=("Arial", 10)
        ).pack(pady=10)
        
        # Поле введення пароля
        self.password_entry = tk.Entry(
            self.dialog,
            show="*",
            width=30,
            font=("Arial", 12)
        )
        self.password_entry.pack(pady=10)
        self.password_entry.focus_set()
        self.password_entry.focus_force()
        self.password_entry.bind("<Return>", lambda e: self.check_password())
        
        # Кнопки
        button_frame = tk.Frame(self.dialog)
        button_frame.pack(pady=10)
        
        tk.Button(
            button_frame,
            text="OK",
            command=self.check_password,
            width=10
        ).pack(side="left", padx=5)
        
        tk.Button(
            button_frame,
            text="Скасувати",
            command=self._cancel_action,
            width=10
        ).pack(side="left", padx=5)
    
    def _cancel_action(self) -> None:
        """Обробник кнопки Скасувати."""
        self.result = False
        self.dialog.destroy()
    
    def _on_close(self) -> None:
        """Обробник закриття діалогу через X."""
        self.result = False
        self.dialog.destroy()
    
    def check_password(self) -> None:
        """Перевіряє введений пароль.
        
        Порівнює введений пароль з паролем з БД.
        Якщо пароль правильний, встановлює self.result = True та закриває діалог.
        """
        entered_password = self.password_entry.get()
        
        if check_password(entered_password):
            self.result = True
            logger.debug("Пароль введено правильно")
            self.dialog.destroy()
        else:
            messagebox.showerror("Помилка", "Невірний пароль!")
            self.password_entry.delete(0, tk.END)
            logger.warning("Спроба введення невірного пароля")
    
    def show(self) -> Optional[bool]:
        """Показує діалог та очікує результату.
        
        Returns:
            Optional[bool]: True якщо пароль правильний, False якщо скасовано,
                           None якщо діалог не завершено
        """
        self.dialog.wait_window()
        return self.result







