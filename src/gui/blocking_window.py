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
        
        self.root.title("System Shutdown Warning")
        
        # Повноекранний режим
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)
        
        # Напівпрозорий фон (тільки Windows)
        self.root.attributes("-alpha", 0.8)
        self.root.configure(bg='black')
        
        # Мітка з попередженням
        self.label = tk.Label(
            self.root,
            text=f"Комп'ютер вимкнеться через {self.countdown_seconds} секунд",
            fg="white",
            bg="black",
            font=("Helvetica", 48, "bold")
        )
        self.label.pack(expand=True)
        
        # Відображаємо OTP та QR-код якщо надано
        if self.otp:
            self._create_otp_widgets()
        
        # Забороняємо закриття вікна
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        self.root.bind("<Alt-F4>", lambda e: "break")
        
        # Запускаємо відлік
        self._update_timer()
    
    def _create_otp_widgets(self) -> None:
        """Створює віджети для відображення OTP та QR-коду."""
        # Мітка з OTP кодом
        self.otp_label = tk.Label(
            self.root,
            text=f"Код для Telegram боту: {self.otp}",
            fg="yellow",
            bg="black",
            font=("Helvetica", 24)
        )
        self.otp_label.pack(pady=10)
        
        # QR-код якщо надано URL
        if self.bot_url:
            try:
                qr_img = generate_qr_code_resized(
                    data=self.bot_url,
                    size=(300, 300),
                    version=1,
                    box_size=5,
                    border=4
                )
                
                self.qr_photo = ImageTk.PhotoImage(qr_img)
                self.qr_label = tk.Label(
                    self.root,
                    image=self.qr_photo,
                    bg="black"
                )
                self.qr_label.pack(pady=20)
                logger.debug("QR-код відображено в вікні блокування")
            except Exception as e:
                logger.error(f"Помилка генерації QR-коду в вікні блокування: {e}")
    
    def _update_timer(self) -> None:
        """Оновлює таймер відліку."""
        if self.countdown_seconds > 0:
            self.label.config(
                text=f"Комп'ютер вимкнеться через {self.countdown_seconds} секунд"
            )
            self.countdown_seconds -= 1
            self.root.after(1000, self._update_timer)
        else:
            self.label.config(text="Вимикання...")
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






