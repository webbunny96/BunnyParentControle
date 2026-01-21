"""Модуль діалогу введення пароля."""

import tkinter as tk
from tkinter import messagebox
from typing import Optional

from src.core.config import check_password
from src.utils.logger import get_logger
from src.gui.themes import THEME

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
        self.dialog.title("🔒 Введіть батьківський пароль")
        self.dialog.geometry("400x200")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg=THEME["bg"])
        
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
        """Створює віджети діалогу з сучасним дизайном."""
        # Контейнер
        container = tk.Frame(self.dialog, bg=THEME["bg"])
        container.pack(fill="both", expand=True, padx=30, pady=30)
        
        # Заголовок
        title_label = tk.Label(
            container,
            text="🔒 Введіть батьківський пароль",
            font=("Segoe UI", 14, "bold"),
            bg=THEME["bg"],
            fg=THEME["fg"]
        )
        title_label.pack(pady=(0, 20))
        
        # Поле введення пароля
        self.password_entry = tk.Entry(
            container,
            show="*",
            font=("Segoe UI", 12),
            bg=THEME["entry_bg"],
            fg=THEME["entry_fg"],
            insertbackground=THEME["fg"],
            relief="flat",
            bd=0,
            highlightthickness=2,
            highlightbackground=THEME["border"],
            highlightcolor=THEME["accent"]
        )
        self.password_entry.pack(fill="x", pady=(0, 20), ipady=10)
        self.password_entry.focus_set()
        self.password_entry.focus_force()
        self.password_entry.bind("<Return>", lambda e: self.check_password())
        
        # Кнопки
        button_frame = tk.Frame(container, bg=THEME["bg"])
        button_frame.pack(fill="x")
        
        ok_button = tk.Button(
            button_frame,
            text="✓ Підтвердити",
            command=self.check_password,
            font=("Segoe UI", 10, "bold"),
            bg=THEME["button_bg"],
            fg=THEME["button_fg"],
            activebackground=THEME["button_active"],
            activeforeground=THEME["button_fg"],
            relief="flat",
            cursor="hand2",
            padx=20,
            pady=10,
            bd=0
        )
        ok_button.pack(side="right", padx=(10, 0))
        
        cancel_button = tk.Button(
            button_frame,
            text="✗ Скасувати",
            command=self._cancel_action,
            font=("Segoe UI", 10),
            bg=THEME["frame_bg"],
            fg=THEME["fg"],
            activebackground=THEME["border"],
            activeforeground=THEME["fg"],
            relief="flat",
            cursor="hand2",
            padx=20,
            pady=10,
            bd=0
        )
        cancel_button.pack(side="right")
    
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







