"""Модуль вікна налаштувань системи."""

import tkinter as tk
from tkinter import messagebox
from typing import Optional
from PIL import Image, ImageTk
import queue
import threading

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
        
        # Фрейм для поля вводу та кнопки вставки
        entry_frame = tk.Frame(token_frame)
        entry_frame.pack(fill="x", pady=5)
        
        self.token_entry = tk.Entry(entry_frame, width=40, show="*")
        self.token_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # Кнопка вставки з буферу обміну
        paste_button = tk.Button(
            entry_frame,
            text="Вставити",
            command=self._paste_token_from_clipboard,
            width=12,
            font=("Arial", 9),
            cursor="hand2"
        )
        paste_button.pack(side="right", fill="y")
        
        if self.bot_token:
            self.token_entry.insert(0, self.bot_token)
        
        # Статус підключення
        self.connection_status_label = tk.Label(
            token_frame,
            text="",
            font=("Arial", 9),
            fg="gray"
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
        except Exception as e:
            logger.error(f"Помилка вставки з буферу обміну: {e}")
            messagebox.showerror(
                "Помилка",
                f"Не вдалося вставити текст з буферу обміну:\n{str(e)}"
            )
        
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
    
    def _on_close_settings(self) -> None:
        """Обробник закриття вікна налаштувань (не перший запуск)."""
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
            self.connection_status_label.config(text="", fg="gray")
            return
        
        # Показуємо статус підключення
        self.connection_status_label.config(text="Підключення...", fg="blue")
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
                fg="red"
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
            self.connection_status_label.config(
                text=f"Помилка генерації QR-коду: {str(e)}",
                fg="red"
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
            self.qr_label.config(image="", text="Введіть токен для генерації QR-коду")
            self.otp_display_label.config(text="")
            self.connection_status_label.config(text="", fg="gray")
            return
        
        # Показуємо статус підключення
        self.connection_status_label.config(text="Підключення...", fg="blue")
        self.window.update_idletasks()  # Оновлюємо GUI без блокування
        
        # Отримуємо username бота
        try:
            bot_username = get_bot_username(token, timeout=5)
            
            if not bot_username:
                self.connection_status_label.config(
                    text="Помилка підключення: не вдалося отримати дані бота",
                    fg="red"
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
                fg="red"
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






