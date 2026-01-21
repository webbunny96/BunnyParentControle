"""Модуль вікна налаштувань системи."""

import tkinter as tk
from tkinter import messagebox
from typing import Optional
from PIL import Image, ImageTk

from src.core.config import load_config, save_config
from src.utils.logger import get_logger
from src.utils.env_manager import get_bot_token_from_env, save_bot_token_to_env
from src.utils.telegram_api import get_bot_username
from src.utils.qr_generator import generate_qr_code_resized, create_auth_url

logger = get_logger(__name__)


class SettingsWindow:
    """Вікно налаштувань системи батьківського контролю."""
    
    def __init__(self, parent: Optional[tk.Tk] = None, is_first_run: bool = False) -> None:
        """Ініціалізує вікно налаштувань.
        
        Args:
            parent: Батьківське вікно (опціонально)
            is_first_run: Чи це перший запуск (не можна закрити без пароля)
        """
        self.is_first_run = is_first_run
        self.config = load_config()
        
        # Створюємо вікно
        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self.window.title(
            "Налаштування" if not is_first_run else "Перший запуск - Налаштування"
        )
        self.window.geometry("500x700")
        self.window.resizable(False, False)
        
        # Центруємо вікно
        self._center_window()
        
        # Налаштовуємо модальність
        if not is_first_run:
            self.window.transient(parent)
            self.window.grab_set()
        else:
            # Забороняємо закриття на першому запуску без пароля
            self.window.protocol("WM_DELETE_WINDOW", self._on_close_first_run)
            self.window.bind("<Alt-F4>", lambda e: "break")
            self.window.bind("<Control-w>", lambda e: "break")
            self.window.bind("<Control-q>", lambda e: "break")
        
        # Завантажуємо токен з .env
        self.bot_token = get_bot_token_from_env()
        
        # Створюємо віджети
        self._create_widgets()
        self.update_qr_code()
        
        # На першому запуску вимикаємо кнопку збереження до введення пароля
        if is_first_run:
            self.save_button.config(state="disabled")
    
    def _center_window(self) -> None:
        """Центрує вікно на екрані."""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def _create_widgets(self) -> None:
        """Створює віджети вікна."""
        # Заголовок
        title_label = tk.Label(
            self.window,
            text="Налаштування системи",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=10)
        
        # Поле введення токену
        token_frame = tk.Frame(self.window)
        token_frame.pack(pady=10, padx=20, fill="x")
        
        tk.Label(
            token_frame,
            text="Токен Telegram боту:",
            font=("Arial", 10)
        ).pack(anchor="w")
        
        self.token_entry = tk.Entry(token_frame, width=50, show="*")
        self.token_entry.pack(fill="x", pady=5)
        
        if self.bot_token:
            self.token_entry.insert(0, self.bot_token)
        
        self.token_entry.bind("<KeyRelease>", lambda e: self.update_qr_code())
        
        # Фрейм для QR-коду
        qr_frame = tk.Frame(self.window)
        qr_frame.pack(pady=10)
        
        tk.Label(
            qr_frame,
            text="QR-код для підключення адміністратора:",
            font=("Arial", 10)
        ).pack()
        
        self.qr_label = tk.Label(
            qr_frame,
            text="QR-код буде тут",
            bg="white",
            width=150,
            height=150
        )
        self.qr_label.pack(pady=5)
        
        # Мітка з інструкцією
        otp_info_label = tk.Label(
            qr_frame,
            text="Або введіть код вручну:",
            font=("Arial", 11),
            fg="gray"
        )
        otp_info_label.pack(pady=(10, 5))
        
        # Відображення OTP коду
        self.otp_display_label = tk.Label(
            qr_frame,
            text="",
            font=("Arial", 24, "bold"),
            fg="#1976D2",
            bg="white",
            relief="sunken",
            bd=2,
            padx=20,
            pady=12
        )
        self.otp_display_label.pack(pady=(0, 10))
        
        # Поля для пароля
        password_frame = tk.Frame(self.window)
        password_frame.pack(pady=10, padx=20, fill="x")
        
        tk.Label(
            password_frame,
            text="Новий батьківський пароль:",
            font=("Arial", 10)
        ).pack(anchor="w")
        
        self.password_entry = tk.Entry(password_frame, width=50, show="*")
        self.password_entry.pack(fill="x", pady=5)
        
        tk.Label(
            password_frame,
            text="Підтвердіть пароль:",
            font=("Arial", 10)
        ).pack(anchor="w", pady=(10, 0))
        
        self.password_confirm_entry = tk.Entry(password_frame, width=50, show="*")
        self.password_confirm_entry.pack(fill="x", pady=5)
        
        # Прив'язка подій для перевірки паролів
        self.password_entry.bind("<KeyRelease>", self._check_password_fields)
        self.password_confirm_entry.bind("<KeyRelease>", self._check_password_fields)
        
        # Кнопки
        button_frame = tk.Frame(self.window)
        button_frame.pack(pady=20)
        
        self.save_button = tk.Button(
            button_frame,
            text="Зберегти",
            command=self.save_settings,
            font=("Arial", 12),
            bg="#4CAF50",
            fg="white",
            width=15,
            height=2
        )
        self.save_button.pack(side="left", padx=5)
        
        if not self.is_first_run:
            cancel_button = tk.Button(
                button_frame,
                text="Скасувати",
                command=self.window.destroy,
                font=("Arial", 12),
                bg="#f44336",
                fg="white",
                width=15,
                height=2
            )
            cancel_button.pack(side="left", padx=5)
    
    def _on_close_first_run(self) -> None:
        """Обробник закриття вікна на першому запуску."""
        self.config = load_config()
        if not self.config.get("parent_password"):
            messagebox.showwarning(
                "Увага",
                "Необхідно встановити батьківський пароль перед продовженням!"
            )
        else:
            self.window.destroy()
    
    def _check_password_fields(self, event=None) -> None:
        """Перевіряє поля паролів та вмикає/вимикає кнопку збереження.
        
        Args:
            event: Подія (не використовується)
        """
        if self.is_first_run:
            password = self.password_entry.get()
            password_confirm = self.password_confirm_entry.get()
            
            if password and password_confirm and password == password_confirm:
                self.save_button.config(state="normal")
            else:
                self.save_button.config(state="disabled")
    
    def update_qr_code(self) -> None:
        """Оновлює QR-код на основі поточного токену та OTP."""
        token = self.token_entry.get().strip()
        
        if not token:
            self.qr_label.config(image="", text="Введіть токен для генерації QR-коду")
            self.otp_display_label.config(text="")
            return
        
        # Отримуємо username бота
        bot_username = get_bot_username(token)
        
        if not bot_username:
            self.qr_label.config(
                image="",
                text="Помилка підключення до Telegram API"
            )
            self.otp_display_label.config(text="")
            return
        
        # Створюємо URL для авторизації
        otp_code = self.config.get('otp', 'N/A')
        auth_url = create_auth_url(bot_username, otp_code)
        
        try:
            # Генеруємо QR-код
            qr_img = generate_qr_code_resized(
                data=auth_url,
                size=(150, 150),
                version=1,
                box_size=5,
                border=4
            )
            
            self.qr_photo = ImageTk.PhotoImage(qr_img)
            self.qr_label.config(image=self.qr_photo, text="")
            
            # Відображаємо OTP код
            self.otp_display_label.config(
                text=otp_code,
                font=("Arial", 24, "bold"),
                fg="#1976D2"
            )
            
            logger.debug("QR-код оновлено")
            
        except Exception as e:
            logger.error(f"Помилка генерації QR-коду: {e}")
            self.qr_label.config(image="", text=f"Помилка генерації QR-коду: {str(e)}")
            self.otp_display_label.config(text="")
    
    def save_settings(self) -> None:
        """Зберігає налаштування (токен та пароль)."""
        # Валідація пароля
        password = self.password_entry.get()
        password_confirm = self.password_confirm_entry.get()
        
        if not password:
            messagebox.showerror("Помилка", "Пароль не може бути порожнім!")
            return
        
        if password != password_confirm:
            messagebox.showerror("Помилка", "Паролі не співпадають!")
            return
        
        # Зберігаємо токен в .env
        token = self.token_entry.get().strip()
        if token:
            if not save_bot_token_to_env(token):
                messagebox.showerror("Помилка", "Не вдалося зберегти токен!")
                return
        
        # Зберігаємо пароль в конфігурацію
        self.config["parent_password"] = password
        save_config(self.config)
        
        logger.info("Налаштування збережено")
        messagebox.showinfo("Успіх", "Налаштування збережено!")
        self.window.destroy()






