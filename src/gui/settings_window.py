"""Модуль вікна налаштувань системи."""

import tkinter as tk
from tkinter import messagebox
from typing import Optional
from PIL import Image, ImageTk
import queue
import threading

from src.core.config import load_config, save_config
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
        self.window.geometry("650x530")
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
        
        # Прив'язка подій для перевірки паролів
        self.password_entry.bind("<KeyRelease>", self._check_password_fields)
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
    
    def _check_password_fields(self, event=None) -> None:
        """Перевіряє поля паролів та вмикає/вимикає кнопку збереження.
        
        Args:
            event: Подія (не використовується)
        """
        if self.is_first_run:
            password = self.password_entry.get()
            password_confirm = self.password_confirm_entry.get()
            
            if password and password_confirm and password == password_confirm:
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
        
        messagebox.showinfo("Успіх", "Налаштування збережено!")
        self.window.destroy()






