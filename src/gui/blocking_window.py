"""Модуль вікна блокування комп'ютера."""

import argparse
import ctypes
import os
import sys
import tkinter as tk
from typing import Optional
from pathlib import Path

from PIL import Image, ImageTk

from src.utils.logger import get_logger
from src.utils.qr_generator import generate_qr_code_resized
from src.gui.themes import THEME

logger = get_logger(__name__)


class BlockingWindow:
    """Вікно блокування комп'ютера з відліком до вимкнення."""
    
    def __init__(
        self,
        countdown_seconds: int = 60,
        otp: Optional[str] = None,
        bot_url: Optional[str] = None
    ) -> None:
        """Ініціалізує вікно блокування.
        
        Args:
            countdown_seconds: Кількість секунд до вимкнення
            otp: OTP код для відображення (опціонально)
            bot_url: URL бота для QR-коду (опціонально)
        """
        # Блокуємо ввід якнайшвидше
        self._set_block_input(True)
        
        self.root = tk.Tk()
        self.otp = otp
        self.bot_url = bot_url
        self.countdown_seconds = countdown_seconds
        
        self.root.title("⚠️ Система буде вимкнена")
        
        # Повноекранний режим
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)
        
        # Темний напівпрозорий фон
        self.root.configure(bg='#000000')
        self.root.attributes("-alpha", 0.95)
        
        # Головний контейнер
        main_container = tk.Frame(self.root, bg='#000000')
        main_container.pack(expand=True, fill="both")
        
        # Мітка з попередженням
        self.label = tk.Label(
            main_container,
            text=f"⚠️ Комп'ютер вимкнеться через {self.countdown_seconds} секунд",
            fg="#ff4444",
            bg="#000000",
            font=("Segoe UI", 56, "bold")
        )
        self.label.pack(pady=(100, 50))
        
        # Великий таймер
        self.timer_label = tk.Label(
            main_container,
            text=str(self.countdown_seconds),
            fg="#ff4444",
            bg="#000000",
            font=("Segoe UI", 120, "bold")
        )
        self.timer_label.pack(pady=20)
        
        # Відображаємо OTP та QR-код якщо надано
        if self.otp:
            self._create_otp_widgets(main_container)
        
        # Забороняємо закриття вікна
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        self.root.bind("<Alt-F4>", lambda e: "break")
        
        # Запускаємо відлік
        self._update_timer()
    
    def _create_otp_widgets(self, parent: tk.Widget) -> None:
        """Створює віджети для відображення OTP та QR-коду."""
        # Контейнер для OTP та QR
        otp_container = tk.Frame(parent, bg='#000000')
        otp_container.pack(pady=50)
        
        # Мітка з OTP кодом
        tk.Label(
            otp_container,
            text="Код для Telegram боту:",
            fg="#ffffff",
            bg="#000000",
            font=("Segoe UI", 20)
        ).pack(pady=(0, 10))
        
        self.otp_label = tk.Label(
            otp_container,
            text=self.otp,
            fg="#ffaa00",
            bg="#000000",
            font=("Consolas", 48, "bold"),
            relief="flat",
            bd=0,
            padx=40,
            pady=20,
            highlightthickness=3,
            highlightbackground="#ffaa00"
        )
        self.otp_label.pack(pady=10)
        
        # QR-код якщо надано URL
        if self.bot_url:
            try:
                qr_img = generate_qr_code_resized(
                    data=self.bot_url,
                    size=(400, 400),
                    version=1,
                    box_size=8,
                    border=4
                )
                
                self.qr_photo = ImageTk.PhotoImage(qr_img)
                self.qr_label = tk.Label(
                    otp_container,
                    image=self.qr_photo,
                    bg="#000000",
                    relief="flat",
                    bd=5,
                    highlightbackground="#ffffff",
                    highlightthickness=3
                )
                self.qr_label.pack(pady=30)
                logger.debug("QR-код відображено в вікні блокування")
            except Exception as e:
                logger.error(f"Помилка генерації QR-коду в вікні блокування: {e}")
    
    def _update_timer(self) -> None:
        """Оновлює таймер відліку."""
        if self.countdown_seconds > 0:
            self.label.config(
                text=f"⚠️ Комп'ютер вимкнеться через {self.countdown_seconds} секунд"
            )
            self.timer_label.config(text=str(self.countdown_seconds))
            self.countdown_seconds -= 1
            self.root.after(1000, self._update_timer)
        else:
            self.label.config(text="🔄 Вимикання...")
            self.timer_label.config(text="0")
            self._shutdown_system()
    
    def _set_block_input(self, block: bool) -> None:
        """Блокує або розблоковує ввід користувача (миша та клавіатура).
        
        Вимагає прав адміністратора.
        
        Args:
            block: True для блокування, False для розблоковування
        """
        try:
            ctypes.windll.user32.BlockInput(block)
            logger.debug(f"BlockInput встановлено: {block}")
        except Exception as e:
            logger.error(f"Помилка встановлення BlockInput({block}): {e}")
    
    def _shutdown_system(self) -> None:
        """Вимикає систему."""
        logger.warning("Вимикання комп'ютера...")
        self._set_block_input(False)  # Розблоковуємо перед вимкненням
        os.system("shutdown /s /t 1 /f")
        self.root.destroy()
        sys.exit()
    
    def run(self) -> None:
        """Запускає головний цикл вікна."""
        self.root.mainloop()


def main() -> None:
    """Головна функція для запуску вікна блокування."""
    parser = argparse.ArgumentParser(description="Вікно блокування комп'ютера")
    parser.add_argument("--otp", help="Registration OTP to display")
    parser.add_argument("--url", help="URL for QR code registration")
    args = parser.parse_args()
    
    app = BlockingWindow(60, otp=args.otp, bot_url=args.url)
    app.run()


if __name__ == "__main__":
    main()






