"""Модуль вікна налаштувань системи."""

import tkinter as tk
from tkinter import messagebox
from typing import Optional
from PIL import Image, ImageTk
import queue
import threading
import subprocess

from src.core.config import load_config, save_config, has_password
from src.core.otp_manager import (
    register_otp_change_callback, 
    unregister_otp_change_callback,
    get_time_until_next_update,
    OTP_UPDATE_INTERVAL
)
from src.utils.logger import get_logger
from src.utils.env_manager import get_bot_token_from_env, save_bot_token_to_env
from src.utils.telegram_api import get_bot_username
from src.utils.qr_generator import generate_qr_code_resized, create_auth_url
from src.utils.password_validator import validate_password
from src.utils.service_manager import (
    is_service_installed,
    uninstall_service,
    install_service,
    is_admin,
    is_service_running,
    stop_service
)
from src.gui.themes import THEME

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
        self.window.geometry("650x600")
        self.window.resizable(False, False)
        
        # Застосовуємо темну тему
        self.window.configure(bg=THEME["bg"])
        
        # Центруємо вікно
        self._center_window()
        
        # Переконаємося що вікно видиме та на передньому плані
        self.window.deiconify()  # Показуємо вікно
        self.window.lift()  # Піднімаємо на передній план
        self.window.focus_force()  # Даємо фокус
        self.window.update()  # Оновлюємо вікно
        
        # Налаштовуємо модальність
        if not is_first_run:
            self.window.transient(parent)
            self.window.grab_set()
            # Обробник закриття вікна налаштувань (не перший запуск)
            self.window.protocol("WM_DELETE_WINDOW", self._on_close_settings)
        else:
            # Забороняємо закриття на першому запуску без пароля
            self.window.protocol("WM_DELETE_WINDOW", self._on_close_first_run)
            self.window.bind("<Alt-F4>", lambda e: "break")
            self.window.bind("<Control-w>", lambda e: "break")
            self.window.bind("<Control-q>", lambda e: "break")
        
        # Завантажуємо токен з .env
        self.bot_token = get_bot_token_from_env()
        
        # Черга для передачі результатів з потоку в головний потік GUI
        self.result_queue = queue.Queue()
        
        # Створюємо віджети
        self._create_widgets()
        self.update_qr_code()
        
        # Запускаємо перевірку черги результатів
        self._check_result_queue()
        
        # Реєструємо callback для оновлення QR-коду при зміні OTP
        register_otp_change_callback(self._on_otp_changed)
        
        # На першому запуску вимикаємо кнопку збереження до введення пароля
        # Перевірка після створення віджетів, щоб save_button вже існував
        if is_first_run and hasattr(self, 'save_button'):
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
        """Створює віджети вікна з сучасним дизайном."""
        # Головний контейнер з прокруткою
        main_container = tk.Frame(self.window, bg=THEME["bg"])
        main_container.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Компактний заголовок
        header_frame = tk.Frame(main_container, bg=THEME["bg"], height=40)
        header_frame.pack(fill="x", pady=(8, 10))
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame,
            text="⚙️ Налаштування системи",
            font=("Segoe UI", 14, "bold"),
            bg=THEME["bg"],
            fg=THEME["fg"]
        )
        title_label.pack(pady=8)
        
        # Контейнер для контенту
        content_frame = tk.Frame(main_container, bg=THEME["bg"])
        content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # Секція токену бота
        token_section = tk.LabelFrame(
            content_frame,
            text="🤖 Telegram бот",
            font=("Segoe UI", 10, "bold"),
            bg=THEME["frame_bg"],
            fg=THEME["fg"],
            padx=10,
            pady=10,
            relief="flat",
            bd=1,
            highlightbackground=THEME["border"],
            highlightthickness=1
        )
        token_section.pack(fill="x", pady=(0, 8))
        
        # Компактне розташування: мітка та поле в одному рядку
        token_row = tk.Frame(token_section, bg=THEME["frame_bg"])
        token_row.pack(fill="x", pady=(0, 6))
        
        tk.Label(
            token_row,
            text="Токен:",
            font=("Segoe UI", 9),
            bg=THEME["frame_bg"],
            fg=THEME["fg"]
        ).pack(side="left", padx=(0, 8))
        
        # Фрейм для поля вводу та кнопки вставки
        entry_frame = tk.Frame(token_row, bg=THEME["frame_bg"])
        entry_frame.pack(side="left", fill="x", expand=True)
        
        self.token_entry = tk.Entry(
            entry_frame,
            width=40,
            show="*",
            font=("Consolas", 10),
            bg=THEME["entry_bg"],
            fg=THEME["entry_fg"],
            insertbackground=THEME["fg"],
            relief="flat",
            bd=0,
            highlightthickness=2,
            highlightbackground=THEME["border"],
            highlightcolor=THEME["accent"]
        )
        self.token_entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=6)
        
        # Кнопка очищення поля токену
        clear_button = tk.Button(
            entry_frame,
            text="✕",
            command=self._clear_token_field,
            font=("Segoe UI", 9),
            bg=THEME["error"],
            fg=THEME["button_fg"],
            activebackground="#b02a2a",
            activeforeground=THEME["button_fg"],
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=6,
            bd=0,
            width=3
        )
        clear_button.pack(side="right", padx=(0, 6))
        
        # Кнопка вставки з буферу обміну (компактна)
        paste_button = tk.Button(
            entry_frame,
            text="📋",
            command=self._paste_token_from_clipboard,
            font=("Segoe UI", 9),
            bg=THEME["button_bg"],
            fg=THEME["button_fg"],
            activebackground=THEME["button_active"],
            activeforeground=THEME["button_fg"],
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=6,
            bd=0,
            width=3
        )
        paste_button.pack(side="right")
        
        if self.bot_token:
            self.token_entry.insert(0, self.bot_token)
        
        # Статус підключення (компактний)
        self.connection_status_label = tk.Label(
            token_section,
            text="",
            font=("Segoe UI", 8),
            bg=THEME["frame_bg"],
            fg=THEME["fg"]
        )
        self.connection_status_label.pack(anchor="w", pady=(2, 0))
        
        # Обробка подій для оновлення QR-коду з затримкою
        self._qr_update_scheduled = None
        
        def schedule_qr_update():
            """Планує оновлення QR-коду з затримкою."""
            # Відміняємо попереднє заплановане оновлення якщо воно є
            if self._qr_update_scheduled is not None:
                try:
                    self.window.after_cancel(self._qr_update_scheduled)
                except:
                    pass
            
            # Плануємо оновлення через 500мс після останньої зміни
            # Це дозволяє вставити весь текст перед перевіркою
            self._qr_update_scheduled = self.window.after(500, self.update_qr_code)
        
        def on_modified(event):
            """Обробник зміни тексту в полі (викликається для всіх змін, включаючи вставку)."""
            if self.token_entry.edit_modified():
                # Скидаємо прапорець Modified
                self.token_entry.edit_modified(False)
                # Плануємо оновлення
                schedule_qr_update()
        
        def on_paste(event=None):
            """Обробник вставки - дозволяє стандартну обробку, потім планує оновлення."""
            # Дозволяємо стандартну обробку вставки Tkinter
            # Після вставки викличеться Modified, який запланує оновлення
            # Але також плануємо оновлення тут для надійності
            self.window.after(100, schedule_qr_update)
            return None  # Не блокуємо стандартну обробку
        
        # Використовуємо подію Modified для всіх змін тексту
        self.token_entry.bind("<<Modified>>", on_modified)
        
        # Явна обробка вставки через Ctrl+V та Shift+Insert
        self.token_entry.bind("<Control-v>", on_paste)
        self.token_entry.bind("<Shift-Insert>", on_paste)
        
        # Також обробляємо вставку через контекстне меню (права кнопка миші)
        # Tkinter автоматично обробляє це, але ми можемо додати обробник для надійності
        def on_button_release(event):
            """Обробник відпускання кнопки миші - може бути вставка через контекстне меню."""
            # Плануємо перевірку через невелику затримку
            self.window.after(100, schedule_qr_update)
        
        self.token_entry.bind("<ButtonRelease-1>", on_button_release)
        
        # Секція QR-коду та OTP (компактна, горизонтальне розташування)
        qr_section = tk.LabelFrame(
            content_frame,
            text="🔐 Підключення адміністратора",
            font=("Segoe UI", 10, "bold"),
            bg=THEME["frame_bg"],
            fg=THEME["fg"],
            padx=10,
            pady=10,
            relief="flat",
            bd=1,
            highlightbackground=THEME["border"],
            highlightthickness=1
        )
        qr_section.pack(fill="x", pady=(0, 8))
        
        # Контейнер для QR-коду та OTP (горизонтально)
        qr_container = tk.Frame(qr_section, bg=THEME["frame_bg"])
        qr_container.pack(fill="x")
        
        # Ліва частина: QR-код (компактний)
        qr_left = tk.Frame(qr_container, bg=THEME["frame_bg"])
        qr_left.pack(side="left", padx=(0, 12))
        
        tk.Label(
            qr_left,
            text="QR-код:",
            font=("Segoe UI", 8),
            bg=THEME["frame_bg"],
            fg=THEME["fg"]
        ).pack(pady=(0, 4))
        
        self.qr_label = tk.Label(
            qr_left,
            text="QR-код\nбуде тут",
            bg=THEME["entry_bg"],
            width=100,
            height=100,
            relief="flat",
            bd=2,
            highlightbackground=THEME["border"],
            highlightthickness=2,
            font=("Segoe UI", 7),
            fg=THEME["fg"],
            justify="center"
        )
        self.qr_label.pack()
        
        # Права частина: OTP код (компактний)
        otp_right = tk.Frame(qr_container, bg=THEME["frame_bg"])
        otp_right.pack(side="left", fill="x", expand=True)
        
        tk.Label(
            otp_right,
            text="Код підключення:",
            font=("Segoe UI", 8),
            bg=THEME["frame_bg"],
            fg=THEME["fg"]
        ).pack(pady=(0, 4))
        
        self.otp_display_label = tk.Label(
            otp_right,
            text="",
            font=("Consolas", 20, "bold"),
            fg=THEME["accent"],
            bg=THEME["entry_bg"],
            relief="flat",
            bd=0,
            padx=15,
            pady=8,
            highlightthickness=2,
            highlightbackground=THEME["border"]
        )
        self.otp_display_label.pack()
        
        # Лейбл з відліком часу до оновлення
        self.countdown_label = tk.Label(
            otp_right,
            text="",
            font=("Segoe UI", 9),
            bg=THEME["frame_bg"],
            fg=THEME["fg"]
        )
        self.countdown_label.pack(pady=(8, 0))
        
        # Запускаємо оновлення відліку
        self._update_countdown()
        
        # Секція пароля (компактна, поля поруч)
        password_section = tk.LabelFrame(
            content_frame,
            text="🔒 Батьківський пароль",
            font=("Segoe UI", 10, "bold"),
            bg=THEME["frame_bg"],
            fg=THEME["fg"],
            padx=10,
            pady=10,
            relief="flat",
            bd=1,
            highlightbackground=THEME["border"],
            highlightthickness=1
        )
        password_section.pack(fill="x", pady=(0, 8))
        
        # Поля паролів в одному рядку
        password_row = tk.Frame(password_section, bg=THEME["frame_bg"])
        password_row.pack(fill="x")
        
        # Перше поле пароля
        password1_frame = tk.Frame(password_row, bg=THEME["frame_bg"])
        password1_frame.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        tk.Label(
            password1_frame,
            text="Новий пароль:",
            font=("Segoe UI", 8),
            bg=THEME["frame_bg"],
            fg=THEME["fg"]
        ).pack(anchor="w", pady=(0, 4))
        
        self.password_entry = tk.Entry(
            password1_frame,
            show="*",
            font=("Segoe UI", 9),
            bg=THEME["entry_bg"],
            fg=THEME["entry_fg"],
            insertbackground=THEME["fg"],
            relief="flat",
            bd=0,
            highlightthickness=2,
            highlightbackground=THEME["border"],
            highlightcolor=THEME["accent"]
        )
        self.password_entry.pack(fill="x", ipady=5)
        
        # Друге поле пароля
        password2_frame = tk.Frame(password_row, bg=THEME["frame_bg"])
        password2_frame.pack(side="left", fill="x", expand=True)
        
        tk.Label(
            password2_frame,
            text="Підтвердження:",
            font=("Segoe UI", 8),
            bg=THEME["frame_bg"],
            fg=THEME["fg"]
        ).pack(anchor="w", pady=(0, 4))
        
        self.password_confirm_entry = tk.Entry(
            password2_frame,
            show="*",
            font=("Segoe UI", 9),
            bg=THEME["entry_bg"],
            fg=THEME["entry_fg"],
            insertbackground=THEME["fg"],
            relief="flat",
            bd=0,
            highlightthickness=2,
            highlightbackground=THEME["border"],
            highlightcolor=THEME["accent"]
        )
        self.password_confirm_entry.pack(fill="x", ipady=5)
        
        # Фрейм для вимог до пароля
        requirements_frame = tk.Frame(password_section, bg=THEME["frame_bg"])
        requirements_frame.pack(fill="x", pady=(10, 0))
        
        tk.Label(
            requirements_frame,
            text="Вимоги до пароля:",
            font=("Segoe UI", 8, "bold"),
            bg=THEME["frame_bg"],
            fg=THEME["fg"]
        ).pack(anchor="w", pady=(0, 5))
        
        # Контейнер для вимог (2 колонки)
        requirements_container = tk.Frame(requirements_frame, bg=THEME["frame_bg"])
        requirements_container.pack(fill="x")
        
        # Ліва колонка вимог
        requirements_left = tk.Frame(requirements_container, bg=THEME["frame_bg"])
        requirements_left.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # Права колонка вимог
        requirements_right = tk.Frame(requirements_container, bg=THEME["frame_bg"])
        requirements_right.pack(side="left", fill="x", expand=True)
        
        # Створюємо лейбли для вимог (будуть оновлюватися динамічно)
        self.requirement_labels = {}
        requirement_keys = [
            "Мінімум 8 символів",
            "Великі літери (A-Z)",
            "Малі літери (a-z)",
            "Цифри (0-9)"
        ]
        
        for i, req_key in enumerate(requirement_keys):
            parent = requirements_left if i < 2 else requirements_right
            label = tk.Label(
                parent,
                text=f"⏳ {req_key}",
                font=("Segoe UI", 7),
                bg=THEME["frame_bg"],
                fg=THEME["fg"],
                anchor="w"
            )
            label.pack(anchor="w", pady=2)
            self.requirement_labels[req_key] = label
        
        # Прив'язка подій для перевірки паролів та валідації
        self.password_entry.bind("<KeyRelease>", self._on_password_changed)
        self.password_confirm_entry.bind("<KeyRelease>", self._check_password_fields)
        
        # Кнопки (компактні, внизу)
        button_frame = tk.Frame(content_frame, bg=THEME["bg"])
        button_frame.pack(pady=(5, 0), fill="x")
        
        # Контейнер для кнопок по центру
        button_container = tk.Frame(button_frame, bg=THEME["bg"])
        button_container.pack()
        
        self.save_button = tk.Button(
            button_container,
            text="💾 Зберегти",
            command=self.save_settings,
            font=("Segoe UI", 10, "bold"),
            bg=THEME["button_bg"],
            fg=THEME["button_fg"],
            activebackground=THEME["button_active"],
            activeforeground=THEME["button_fg"],
            relief="flat",
            cursor="hand2",
            padx=20,
            pady=8,
            bd=0
        )
        self.save_button.pack(side="left", padx=(0, 8))
        
        if not self.is_first_run:
            cancel_button = tk.Button(
                button_container,
                text="✗ Скасувати",
                command=self.window.destroy,
                font=("Segoe UI", 9),
                bg=THEME["frame_bg"],
                fg=THEME["fg"],
                activebackground=THEME["border"],
                activeforeground=THEME["fg"],
                relief="flat",
                cursor="hand2",
                padx=18,
                pady=8,
                bd=0
            )
            cancel_button.pack(side="left")
            
            # Кнопка встановлення/видалення служби Windows
            try:
                service_installed = is_service_installed()
                
                # Створюємо кнопку з динамічним текстом та командою
                if service_installed:
                    service_button_text = "🗑️ Видалити службу"
                    service_button_bg = THEME["error"]
                    service_button_active = "#b02a2a"
                    service_button_command = self._uninstall_service
                else:
                    service_button_text = "⚙️ Встановити службу"
                    service_button_bg = THEME["button_bg"]
                    service_button_active = THEME["button_active"]
                    service_button_command = self._install_service
                
                self.service_button = tk.Button(
                    button_container,
                    text=service_button_text,
                    command=service_button_command,
                    font=("Segoe UI", 9),
                    bg=service_button_bg,
                    fg=THEME["button_fg"],
                    activebackground=service_button_active,
                    activeforeground=THEME["button_fg"],
                    relief="flat",
                    cursor="hand2",
                    padx=15,
                    pady=8,
                    bd=0
                )
                self.service_button.pack(side="left", padx=(8, 0))
            except Exception as e:
                logger.warning(f"Не вдалося перевірити статус служби: {e}")
    
    def _update_service_button(self) -> None:
        """Оновлює текст та команду кнопки служби в залежності від статусу."""
        try:
            if not hasattr(self, 'service_button'):
                return
            
            service_installed = is_service_installed()
            
            if service_installed:
                self.service_button.config(
                    text="🗑️ Видалити службу",
                    bg=THEME["error"],
                    activebackground="#b02a2a",
                    command=self._uninstall_service
                )
            else:
                self.service_button.config(
                    text="⚙️ Встановити службу",
                    bg=THEME["button_bg"],
                    activebackground=THEME["button_active"],
                    command=self._install_service
                )
        except Exception as e:
            logger.warning(f"Не вдалося оновити кнопку служби: {e}")
    
    def _install_service(self) -> None:
        """Встановлює службу Windows."""
        try:
            # Перевіряємо чи служба вже встановлена
            if is_service_installed():
                messagebox.showinfo(
                    "Інформація",
                    "Служба Windows вже встановлена."
                )
                self._update_service_button()
                return
            
            # Перевіряємо права адміністратора
            if not is_admin():
                messagebox.showerror(
                    "Помилка",
                    "Для встановлення служби потрібні права адміністратора.\n\n"
                    "Запустіть програму від імені адміністратора."
                )
                return
            
            # Підтвердження встановлення
            result = messagebox.askyesno(
                "Підтвердження",
                "Встановити службу Windows?\n\n"
                "Після встановлення служба буде автоматично запускатися при завантаженні системи.\n"
                "Програма буде працювати у фоновому режимі без GUI.",
                icon="question"
            )
            
            if not result:
                return
            
            # Встановлюємо службу
            logger.info("Встановлення служби Windows...")
            if install_service():
                logger.info("Служба Windows встановлена успішно")
                # Оновлюємо кнопку
                self._update_service_button()
                
                # Показуємо діалог з опціями перезавантаження
                restart_result = self._ask_restart_dialog(
                    "Служба встановлена",
                    "Служба Windows успішно встановлена!\n\n"
                    "Для повного застосування змін рекомендується перезавантажити комп'ютер."
                )
                
                if restart_result == "now":
                    # Перезавантажуємо комп'ютер зараз
                    self._restart_computer()
                elif restart_result == "later":
                    # Плануємо перезавантаження пізніше
                    self._restart_computer_later()
                else:
                    # Скасовано
                    messagebox.showinfo(
                        "Інформація",
                        "Служба встановлена.\n\n"
                        "Ви можете перезавантажити комп'ютер пізніше для повного застосування змін.\n"
                        "Або запустіть службу вручну через 'Служби Windows'."
                    )
            else:
                messagebox.showerror(
                    "Помилка",
                    "Не вдалося встановити службу.\n\n"
                    "Перевірте логи для деталей або встановіть службу вручну через командний рядок."
                )
                
        except Exception as e:
            logger.error(f"Помилка при встановленні служби: {e}", exc_info=True)
            messagebox.showerror(
                "Помилка",
                f"Сталася помилка при встановленні служби:\n{str(e)}"
            )
    
    def _uninstall_service(self) -> None:
        """Видаляє службу Windows з підтвердженням."""
        try:
            # Перевіряємо чи служба встановлена
            if not is_service_installed():
                messagebox.showinfo(
                    "Інформація",
                    "Служба Windows не встановлена."
                )
                self._update_service_button()
                return
            
            # Перевіряємо права адміністратора
            if not is_admin():
                messagebox.showerror(
                    "Помилка",
                    "Для видалення служби потрібні права адміністратора.\n\n"
                    "Запустіть програму від імені адміністратора."
                )
                return
            
            # Підтвердження видалення
            result = messagebox.askyesno(
                "Підтвердження",
                "Ви впевнені, що хочете видалити службу Windows?\n\n"
                "Після видалення служба не буде автоматично запускатися при завантаженні системи.\n"
                "Програму можна буде запускати вручну.",
                icon="warning"
            )
            
            if not result:
                return
            
            # Зупиняємо службу якщо вона запущена
            if is_service_running():
                logger.info("Зупинка служби перед видаленням...")
                if not stop_service():
                    messagebox.showerror(
                        "Помилка",
                        "Не вдалося зупинити службу.\n"
                        "Спробуйте зупинити службу вручну через 'Служби Windows'."
                    )
                    return
            
            # Видаляємо службу
            logger.info("Видалення служби Windows...")
            if uninstall_service():
                messagebox.showinfo(
                    "Успіх",
                    "Служба Windows успішно видалена.\n\n"
                    "Програма більше не буде автоматично запускатися при завантаженні системи."
                )
                logger.info("Служба Windows видалена успішно")
                # Оновлюємо кнопку
                self._update_service_button()
            else:
                messagebox.showerror(
                    "Помилка",
                    "Не вдалося видалити службу.\n\n"
                    "Перевірте логи для деталей або видаліть службу вручну через 'Служби Windows'."
                )
                
        except Exception as e:
            logger.error(f"Помилка при видаленні служби: {e}", exc_info=True)
            messagebox.showerror(
                "Помилка",
                f"Сталася помилка при видаленні служби:\n{str(e)}"
            )
    
    def _ask_restart_dialog(self, title: str, message: str) -> str:
        """Показує діалог з трьома опціями перезавантаження.
        
        Args:
            title: Заголовок діалогу
            message: Текст повідомлення
            
        Returns:
            'now' - перезавантажити зараз
            'later' - перезавантажити пізніше (через 1 годину)
            'cancel' - скасувати
        """
        dialog = tk.Toplevel(self.window)
        dialog.title(title)
        dialog.geometry("450x200")
        dialog.resizable(False, False)
        dialog.transient(self.window)
        dialog.grab_set()
        
        # Центруємо діалог
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        result = {"value": "cancel"}
        
        # Текст повідомлення
        message_label = tk.Label(
            dialog,
            text=message,
            font=("Segoe UI", 10),
            bg=THEME["bg"],
            fg=THEME["fg"],
            wraplength=400,
            justify="left",
            padx=20,
            pady=15
        )
        message_label.pack()
        
        # Фрейм для кнопок
        button_frame = tk.Frame(dialog, bg=THEME["bg"])
        button_frame.pack(pady=15)
        
        def set_result(value: str) -> None:
            result["value"] = value
            dialog.destroy()
        
        # Кнопка "Перезавантажити зараз"
        restart_now_btn = tk.Button(
            button_frame,
            text="🔄 Перезавантажити зараз",
            command=lambda: set_result("now"),
            font=("Segoe UI", 9),
            bg=THEME["button_bg"],
            fg=THEME["button_fg"],
            activebackground=THEME["button_active"],
            activeforeground=THEME["button_fg"],
            relief="flat",
            cursor="hand2",
            padx=15,
            pady=8,
            bd=0
        )
        restart_now_btn.pack(side="left", padx=5)
        
        # Кнопка "Перезавантажити пізніше"
        restart_later_btn = tk.Button(
            button_frame,
            text="⏰ Перезавантажити пізніше",
            command=lambda: set_result("later"),
            font=("Segoe UI", 9),
            bg=THEME["button_bg"],
            fg=THEME["button_fg"],
            activebackground=THEME["button_active"],
            activeforeground=THEME["button_fg"],
            relief="flat",
            cursor="hand2",
            padx=15,
            pady=8,
            bd=0
        )
        restart_later_btn.pack(side="left", padx=5)
        
        # Кнопка "Скасувати"
        cancel_btn = tk.Button(
            button_frame,
            text="❌ Скасувати",
            command=lambda: set_result("cancel"),
            font=("Segoe UI", 9),
            bg=THEME["bg"],
            fg=THEME["fg"],
            activebackground=THEME["button_active"],
            activeforeground=THEME["fg"],
            relief="flat",
            cursor="hand2",
            padx=15,
            pady=8,
            bd=0
        )
        cancel_btn.pack(side="left", padx=5)
        
        # Очікуємо закриття діалогу
        dialog.wait_window()
        
        return result["value"]
    
    def _restart_computer_later(self) -> None:
        """Планує перезавантаження комп'ютера через 1 годину."""
        try:
            logger.info("Планується перезавантаження комп'ютера через 1 годину...")
            # Використовуємо команду shutdown для відкладеного перезавантаження Windows
            # /r - перезавантаження
            # /t 3600 - затримка 3600 секунд (1 година)
            # /f - примусове закриття всіх запущених програм
            subprocess.run(
                ["shutdown", "/r", "/t", "3600", "/f"],
                check=True,
                timeout=5
            )
            logger.info("Команда відкладеного перезавантаження виконана успішно")
            messagebox.showinfo(
                "Перезавантаження заплановано",
                "Комп'ютер буде перезавантажено через 1 годину.\n\n"
                "Щоб скасувати перезавантаження, виконайте команду:\n"
                "shutdown /a"
            )
        except subprocess.TimeoutExpired:
            logger.error("Таймаут при виконанні команди відкладеного перезавантаження")
            messagebox.showerror(
                "Помилка",
                "Не вдалося запланувати перезавантаження комп'ютера.\n"
                "Спробуйте перезавантажити вручну."
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Помилка при виконанні команди відкладеного перезавантаження: {e}")
            messagebox.showerror(
                "Помилка",
                f"Не вдалося запланувати перезавантаження комп'ютера.\n"
                f"Помилка: {str(e)}\n\n"
                f"Спробуйте перезавантажити вручну."
            )
        except Exception as e:
            logger.error(f"Помилка при плануванні перезавантаження комп'ютера: {e}", exc_info=True)
            messagebox.showerror(
                "Помилка",
                f"Не вдалося запланувати перезавантаження комп'ютера:\n{str(e)}"
            )
    
    def _restart_computer(self) -> None:
        """Перезавантажує комп'ютер через команду shutdown."""
        try:
            logger.info("Ініціюється перезавантаження комп'ютера...")
            # Використовуємо команду shutdown для перезавантаження Windows
            # /r - перезавантаження
            # /t 0 - затримка 0 секунд
            # /f - примусове закриття всіх запущених програм
            subprocess.run(
                ["shutdown", "/r", "/t", "0", "/f"],
                check=True,
                timeout=5
            )
            logger.info("Команда перезавантаження виконана успішно")
        except subprocess.TimeoutExpired:
            logger.error("Таймаут при виконанні команди перезавантаження")
            messagebox.showerror(
                "Помилка",
                "Не вдалося перезавантажити комп'ютер.\n"
                "Спробуйте перезавантажити вручну."
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Помилка при виконанні команди перезавантаження: {e}")
            messagebox.showerror(
                "Помилка",
                f"Не вдалося перезавантажити комп'ютер.\n"
                f"Помилка: {str(e)}\n\n"
                f"Спробуйте перезавантажити вручну."
            )
        except Exception as e:
            logger.error(f"Несподівана помилка при перезавантаженні: {e}", exc_info=True)
            messagebox.showerror(
                "Помилка",
                f"Сталася помилка при спробі перезавантаження:\n{str(e)}\n\n"
                f"Спробуйте перезавантажити вручну."
            )
    
    def _clear_token_field(self) -> None:
        """Очищає поле введення токену."""
        self.token_entry.delete(0, tk.END)
        self.token_entry.focus_set()
        # Оновлюємо QR-код після очищення
        self.update_qr_code()
        logger.debug("Поле токену очищено")
    
    def _paste_token_from_clipboard(self) -> None:
        """Вставляє токен з буферу обміну в поле вводу."""
        try:
            # Отримуємо текст з буферу обміну
            clipboard_text = self.window.clipboard_get()
            
            if clipboard_text:
                clipboard_text = clipboard_text.strip()
                
                # Отримуємо позицію курсора
                cursor_pos = self.token_entry.index(tk.INSERT)
                
                # Якщо поле порожнє або користувач хоче замінити весь текст
                # Очищаємо поле та вставляємо новий текст
                if not self.token_entry.get() or cursor_pos == 0:
                    self.token_entry.delete(0, tk.END)
                    self.token_entry.insert(0, clipboard_text)
                else:
                    # Вставляємо в позицію курсора
                    self.token_entry.insert(tk.INSERT, clipboard_text)
                
                # Переміщуємо фокус на поле вводу
                self.token_entry.focus_set()
                
                # Плануємо оновлення QR-коду
                self.update_qr_code()
                logger.debug("Токен вставлено з буферу обміну")
        except tk.TclError as e:
            # Буфер обміну порожній або містить не текст
            logger.warning(f"Буфер обміну порожній або містить не текст: {e}")
            messagebox.showwarning(
                "Помилка",
                "Буфер обміну порожній або містить не текст.\nСкопіюйте токен та спробуйте ще раз."
            )
        except Exception as e:
            logger.error(f"Помилка вставки з буферу обміну: {e}", exc_info=True)
            messagebox.showerror(
                "Помилка",
                f"Не вдалося вставити текст з буферу обміну:\n{str(e)}"
            )
    
    def _update_countdown(self) -> None:
        """Оновлює відлік часу до наступного оновлення OTP."""
        try:
            remaining_seconds = get_time_until_next_update()
            
            if remaining_seconds > 0:
                minutes = remaining_seconds // 60
                seconds = remaining_seconds % 60
                countdown_text = f"⏱️ Оновлення через: {minutes:02d}:{seconds:02d}"
                
                # Змінюємо колір залежно від часу
                if remaining_seconds <= 60:  # Менше хвилини
                    color = THEME["error"]
                elif remaining_seconds <= 180:  # Менше 3 хвилин
                    color = THEME["warning"]
                else:
                    color = THEME["fg"]
                
                self.countdown_label.config(text=countdown_text, fg=color)
            else:
                self.countdown_label.config(text="⏱️ Оновлення...", fg=THEME["warning"])
            
            # Плануємо наступне оновлення через 1 секунду
            self.window.after(1000, self._update_countdown)
        except Exception as e:
            logger.error(f"Помилка оновлення відліку: {e}")
            # Плануємо повторну спробу через 1 секунду
            self.window.after(1000, self._update_countdown)
    
    def _on_otp_changed(self, new_otp: str) -> None:
        """Callback функція, яка викликається при зміні OTP коду.
        
        Args:
            new_otp: Новий OTP код
        """
        # Оновлюємо конфігурацію
        self.config = load_config()
        
        # Оновлюємо QR-код якщо токен вже введено
        token = self.token_entry.get().strip()
        if token:
            # Оновлюємо QR-код з новим OTP
            self.window.after(0, lambda: self.update_qr_code())
            logger.debug(f"QR-код буде оновлено з новим OTP: {new_otp}")
        
        # Відлік оновиться автоматично через _update_countdown
    
    def _on_close_settings(self) -> None:
        """Обробник закриття вікна налаштувань (не перший запуск)."""
        # Видаляємо callback для зміни OTP
        unregister_otp_change_callback(self._on_otp_changed)
        
        # Просто закриваємо вікно налаштувань, root вікно залишається живим
        # Використовуємо withdraw() замість destroy() для безпеки
        # але для Toplevel потрібно використовувати destroy()
        try:
            self.window.destroy()
        except Exception as e:
            logger.error(f"Помилка при закритті вікна налаштувань: {e}")
            # Якщо не вдалося закрити, просто ховаємо
            try:
                self.window.withdraw()
            except:
                pass
    
    def _on_close_first_run(self) -> None:
        """Обробник закриття вікна на першому запуску."""
        from src.core.config import has_password
        if not has_password():
            messagebox.showwarning(
                "Увага",
                "Необхідно встановити батьківський пароль перед продовженням!"
            )
        else:
            # Видаляємо callback для зміни OTP
            unregister_otp_change_callback(self._on_otp_changed)
            self.window.destroy()
    
    def _on_password_changed(self, event=None) -> None:
        """Обробник зміни пароля - валідує та оновлює індикатори вимог.
        
        Args:
            event: Подія (не використовується)
        """
        password = self.password_entry.get()
        
        # Валідуємо пароль та отримуємо деталі
        is_valid, errors, requirements = validate_password(password)
        
        # Оновлюємо індикатори вимог
        for req_key, label in self.requirement_labels.items():
            if requirements.get(req_key, False):
                label.config(
                    text=f"✅ {req_key}",
                    fg=THEME["success"]
                )
            else:
                label.config(
                    text=f"❌ {req_key}",
                    fg=THEME["error"]
                )
        
        # Перевіряємо чи паролі співпадають та валідні
        self._check_password_fields(event)
    
    def _check_password_fields(self, event=None) -> None:
        """Перевіряє поля паролів та вмикає/вимикає кнопку збереження.
        
        Args:
            event: Подія (не використовується)
        """
        if self.is_first_run:
            password = self.password_entry.get()
            password_confirm = self.password_confirm_entry.get()
            
            # Валідуємо пароль
            is_valid, errors, requirements = validate_password(password)
            
            # Перевіряємо чи паролі співпадають та валідні
            if password and password_confirm and password == password_confirm and is_valid:
                self.save_button.config(state="normal", bg=THEME["button_bg"])
            else:
                self.save_button.config(state="disabled", bg=THEME["border"])
    
    def update_qr_code(self) -> None:
        """Оновлює QR-код на основі поточного токену та OTP."""
        token = self.token_entry.get().strip()
        
        if not token:
            self.qr_label.config(
                image="", 
                text="Введіть токен\nдля генерації QR-коду",
                bg=THEME["entry_bg"],
                fg=THEME["fg"],
                font=("Segoe UI", 10)
            )
            self.otp_display_label.config(text="")
            self.connection_status_label.config(text="", fg=THEME["fg"])
            return
        
        # Показуємо статус підключення
        self.connection_status_label.config(text="⏳ Підключення...", fg=THEME["warning"])
        self.window.update_idletasks()  # Оновлюємо GUI без блокування
        
        # Отримуємо username бота в окремому потоці, щоб не блокувати GUI
        def check_token():
            """Перевіряє токен в окремому потоці."""
            try:
                bot_username = get_bot_username(token, timeout=5)
                
                # Передаємо результат через чергу в головний потік
                self.result_queue.put(('success', bot_username, token))
            except Exception as e:
                error_msg = str(e)
                if "timeout" in error_msg.lower() or "Timeout" in error_msg:
                    error_msg = "Таймаут підключення. Перевірте інтернет-з'єднання"
                elif "invalid" in error_msg.lower() or "401" in error_msg:
                    error_msg = "Невірний токен. Перевірте правильність токену"
                else:
                    error_msg = f"Помилка підключення: {error_msg}"
                
                # Передаємо помилку через чергу в головний потік
                self.result_queue.put(('error', error_msg))
        
        # Запускаємо перевірку в окремому потоці
        threading.Thread(target=check_token, daemon=True).start()
    
    def _check_result_queue(self) -> None:
        """Перевіряє чергу результатів та оновлює GUI в головному потоці."""
        try:
            while True:
                result = self.result_queue.get_nowait()
                result_type = result[0]
                
                if result_type == 'success':
                    bot_username, token = result[1], result[2]
                    self._update_qr_with_username(bot_username, token)
                elif result_type == 'error':
                    error_msg = result[1]
                    self._update_qr_with_error(error_msg)
        except queue.Empty:
            pass
        
        # Плануємо наступну перевірку через 100мс
        self.window.after(100, self._check_result_queue)
    
    def _update_qr_with_username(self, bot_username: Optional[str], token: str) -> None:
        """Оновлює QR-код з отриманим username бота."""
        if not bot_username:
            self.connection_status_label.config(
                text="Помилка підключення: не вдалося отримати дані бота",
                fg=THEME["error"]
            )
            self.qr_label.config(
                image="",
                text="Помилка підключення до Telegram API"
            )
            self.otp_display_label.config(text="")
            return
        
        # Підключення успішне
        self.connection_status_label.config(
            text=f"✅ Підключено до @{bot_username}",
            fg=THEME["success"]
        )
        
        # Оновлюємо конфігурацію для отримання актуального OTP
        self.config = load_config()
        
        # Створюємо URL для авторизації
        otp_code = self.config.get('otp', 'N/A')
        auth_url = create_auth_url(bot_username, otp_code)
        
        try:
            # Генеруємо QR-код
            qr_img = generate_qr_code_resized(
                data=auth_url,
                size=(120, 120),  # Оптимальний розмір для сканування
                version=1,
                box_size=6,
                border=4
            )
            
            self.qr_photo = ImageTk.PhotoImage(qr_img)
            self.qr_label.config(image=self.qr_photo, text="")
            
            # Відображаємо OTP код
            self.otp_display_label.config(
                text=otp_code,
                font=("Consolas", 28, "bold"),
                fg=THEME["accent"]
            )
            
            logger.debug("QR-код оновлено")
            
        except Exception as e:
            logger.error(f"Помилка генерації QR-коду: {e}")
            self.qr_label.config(image="", text=f"Помилка генерації QR-коду: {str(e)}")
            self.otp_display_label.config(text="")
            self.connection_status_label.config(
                text=f"Помилка генерації QR-коду: {str(e)}",
                fg=THEME["error"]
            )
    
    def _update_qr_with_error(self, error_msg: str) -> None:
        """Оновлює GUI з повідомленням про помилку."""
        self.connection_status_label.config(
            text=error_msg,
            fg="red"
        )
        self.qr_label.config(
            image="",
            text="Помилка підключення до Telegram API"
        )
        self.otp_display_label.config(text="")
    
    def update_qr_code_old(self) -> None:
        """Стара версія update_qr_code (залишено для резерву)."""
        token = self.token_entry.get().strip()
        
        if not token:
            self.qr_label.config(
                image="", 
                text="Введіть токен\nдля генерації QR-коду",
                bg=THEME["entry_bg"],
                fg=THEME["fg"],
                font=("Segoe UI", 10)
            )
            self.otp_display_label.config(text="")
            self.connection_status_label.config(text="", fg=THEME["fg"])
            return
        
        # Показуємо статус підключення
        self.connection_status_label.config(text="⏳ Підключення...", fg=THEME["warning"])
        self.window.update_idletasks()  # Оновлюємо GUI без блокування
        
        # Отримуємо username бота
        try:
            bot_username = get_bot_username(token, timeout=5)
            
            if not bot_username:
                self.connection_status_label.config(
                    text="Помилка підключення: не вдалося отримати дані бота",
                    fg=THEME["error"]
                )
                self.qr_label.config(
                    image="",
                    text="Помилка підключення до Telegram API"
                )
                self.otp_display_label.config(text="")
                return
            
            # Підключення успішне
            self.connection_status_label.config(
                text=f"Підключено до @{bot_username}",
                fg="green"
            )
        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower() or "Timeout" in error_msg:
                error_msg = "Таймаут підключення. Перевірте інтернет-з'єднання"
            elif "invalid" in error_msg.lower() or "401" in error_msg:
                error_msg = "Невірний токен. Перевірте правильність токену"
            else:
                error_msg = f"Помилка підключення: {error_msg}"
            
            self.connection_status_label.config(
                text=error_msg,
                fg=THEME["error"]
            )
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
                size=(200, 200),  # Оптимальний розмір для сканування
                version=1,
                box_size=6,
                border=4
            )
            
            self.qr_photo = ImageTk.PhotoImage(qr_img)
            self.qr_label.config(image=self.qr_photo, text="")
            
            # Відображаємо OTP код
            self.otp_display_label.config(
                text=otp_code,
                font=("Consolas", 28, "bold"),
                fg=THEME["accent"]
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
        token_saved = False
        if token:
            if not save_bot_token_to_env(token):
                messagebox.showerror("Помилка", "Не вдалося зберегти токен!")
                return
            token_saved = True
        
        # Зберігаємо пароль в БД
        # Валідуємо пароль перед збереженням
        is_valid, errors, requirements = validate_password(password)
        
        if not is_valid:
            error_text = "Пароль не відповідає вимогам безпеки:\n\n"
            for error in errors:
                error_text += f"• {error}\n"
            messagebox.showerror("Помилка валідації пароля", error_text)
            return
        
        # Перевіряємо чи це перший запуск (пароль не був встановлений раніше)
        password_was_set = has_password()
        
        # Пароль валідний, зберігаємо його
        from src.core.config import set_password
        set_password(password)
        # Оновлюємо локальну конфігурацію
        self.config["parent_password"] = "***"  # Плейсхолдер
        
        logger.info("Налаштування збережено")
        
        # Якщо токен збережено, сигналізуємо про необхідність запуску бота
        if token_saved:
            from src.utils.bot_signal import signal_bot_start
            signal_bot_start()
            logger.info("Сигнал запуску бота відправлено")
        
        # Якщо це перший запуск (пароль не був встановлений), спробуємо автоматично встановити службу
        if not password_was_set:
            logger.info("Перший запуск: спроба автоматичного встановлення служби")
            if is_admin():
                if not is_service_installed():
                    try:
                        if install_service():
                            logger.info("Служба автоматично встановлена після першого збереження налаштувань")
                            # Оновлюємо кнопку служби якщо вона існує
                            if hasattr(self, '_service_button'):
                                self._update_service_button()
                            
                            # Показуємо діалог з опціями перезавантаження
                            restart_result = self._ask_restart_dialog(
                                "Налаштування збережено",
                                "Налаштування збережено!\n\n"
                                "Служба Windows автоматично встановлена.\n\n"
                                "Для повного застосування змін рекомендується перезавантажити комп'ютер."
                            )
                            
                            if restart_result == "now":
                                # Перезавантажуємо комп'ютер зараз
                                self._restart_computer()
                            elif restart_result == "later":
                                # Плануємо перезавантаження пізніше
                                self._restart_computer_later()
                            else:
                                # Скасовано
                                messagebox.showinfo(
                                    "Інформація",
                                    "Налаштування збережено!\n\n"
                                    "Служба встановлена.\n"
                                    "Ви можете перезавантажити комп'ютер пізніше для повного застосування змін."
                                )
                        else:
                            logger.warning("Не вдалося автоматично встановити службу")
                            messagebox.showinfo(
                                "Успіх", 
                                "Налаштування збережено!\n\nНе вдалося автоматично встановити службу. "
                                "Ви можете встановити її вручну через кнопку в налаштуваннях."
                            )
                    except Exception as e:
                        logger.error(f"Помилка при автоматичному встановленні служби: {e}", exc_info=True)
                        messagebox.showinfo(
                            "Успіх", 
                            "Налаштування збережено!\n\nНе вдалося автоматично встановити службу. "
                            "Ви можете встановити її вручну через кнопку в налаштуваннях."
                        )
                else:
                    logger.info("Служба вже встановлена")
                    # Показуємо діалог з опціями перезавантаження
                    restart_result = self._ask_restart_dialog(
                        "Налаштування збережено",
                        "Налаштування збережено!\n\n"
                        "Служба Windows вже встановлена.\n\n"
                        "Для повного застосування змін рекомендується перезавантажити комп'ютер."
                    )
                    
                    if restart_result == "now":
                        # Перезавантажуємо комп'ютер зараз
                        self._restart_computer()
                    elif restart_result == "later":
                        # Плануємо перезавантаження пізніше
                        self._restart_computer_later()
                    else:
                        # Скасовано
                        messagebox.showinfo(
                            "Інформація",
                            "Налаштування збережено!\n\n"
                            "Ви можете перезавантажити комп'ютер пізніше для повного застосування змін."
                        )
            else:
                logger.info("Недостатньо прав для автоматичного встановлення служби")
                messagebox.showinfo(
                    "Успіх", 
                    "Налаштування збережено!\n\nДля встановлення служби Windows потрібні права адміністратора. "
                    "Запустіть програму від імені адміністратора та встановіть службу через кнопку в налаштуваннях."
                )
        else:
            messagebox.showinfo("Успіх", "Налаштування збережено!")
        
        self.window.destroy()






