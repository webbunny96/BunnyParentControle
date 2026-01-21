# API Документація

Детальна документація API для системи батьківського контролю.

## Зміст

- [Конфігурація](#конфігурація)
- [Core API](#core-api)
- [Bot API](#bot-api)
- [GUI API](#gui-api)
- [Utils API](#utils-api)

## Конфігурація

### Структура config.json

```json
{
  "admin_ids": [123456789, 987654321],
  "otp": "ABCD1234",
  "parent_password": "пароль",
  "force_block": false,
  "time_limit_minutes": 60,
  "start_time": 1234567890.0,
  "schedule": {
    "0": {
      "start": "22:00",
      "end": "07:00",
      "enabled": true
    },
    "1": {
      "start": "22:00",
      "end": "07:00",
      "enabled": true
    }
  }
}
```

### Поля конфігурації

| Поле | Тип | Опис |
|------|-----|------|
| `admin_ids` | `List[int]` | Список ID адміністраторів Telegram |
| `otp` | `str` | Код реєстрації (8 символів) |
| `parent_password` | `str \| None` | Батьківський пароль |
| `force_block` | `bool` | Примусове блокування |
| `time_limit_minutes` | `int` | Ліміт часу в хвилинах (0 = без ліміту) |
| `start_time` | `float` | Unix timestamp початку відліку |
| `schedule` | `Dict[str, Dict]` | Розклад блокування по днях тижня |

### Формат розкладу

День тижня: `"0"` (понеділок) до `"6"` (неділя)

```json
{
  "start": "HH:MM",    // Час початку блокування
  "end": "HH:MM",      // Час кінця блокування
  "enabled": true      // Чи активний розклад
}
```

## Core API

### src.core.config

#### `load_config() -> Dict[str, Any]`

Завантажує конфігурацію з файлу `config.json`.

**Returns:**
- `Dict[str, Any]`: Конфігурація системи

**Raises:**
- `ValueError`: Якщо файл пошкоджений

**Example:**
```python
from src.core.config import load_config

config = load_config()
print(config["otp"])
```

#### `save_config(config: Dict[str, Any]) -> None`

Зберігає конфігурацію у файл `config.json`.

**Args:**
- `config`: Словник з конфігурацією

**Raises:**
- `IOError`: Якщо не вдалося записати файл
- `ValueError`: Якщо конфігурація невалідна

**Example:**
```python
from src.core.config import load_config, save_config

config = load_config()
config["force_block"] = True
save_config(config)
```

#### `normalize_config(config: Dict[str, Any]) -> Dict[str, Any]`

Нормалізує конфігурацію, додаючи відсутні поля.

**Args:**
- `config`: Поточна конфігурація

**Returns:**
- `Dict[str, Any]`: Нормалізована конфігурація

#### `validate_config(config: Dict[str, Any]) -> Dict[str, Any]`

Валідує конфігурацію та виправляє помилки.

**Args:**
- `config`: Конфігурація для валідації

**Returns:**
- `Dict[str, Any]`: Валідна конфігурація

**Raises:**
- `ValueError`: Якщо конфігурація містить критичні помилки

### src.core.monitor

#### `should_block(config: Dict[str, Any]) -> bool`

Визначає, чи потрібно заблокувати комп'ютер.

**Args:**
- `config`: Конфігурація системи

**Returns:**
- `bool`: `True` якщо потрібно заблокувати

**Логіка перевірки:**
1. `force_block == True` → блокування
2. `time_limit_minutes > 0` і час вичерпано → блокування
3. Поточний час в активному розкладі → блокування

**Example:**
```python
from src.core.monitor import should_block
from src.core.config import load_config

config = load_config()
if should_block(config):
    print("Потрібно заблокувати")
```

#### `monitor_logic(check_interval: float = 10.0, on_block_callback: Optional[Callable] = None, on_unblock_callback: Optional[Callable] = None) -> None`

Основна логіка моніторингу стану системи.

**Args:**
- `check_interval`: Інтервал перевірки в секундах (за замовчуванням 10)
- `on_block_callback`: Функція для виклику при потребі блокування
- `on_unblock_callback`: Функція для виклику при потребі розблокування

**Note:**
Функція працює в циклі до переривання. Callback функції можуть бути async або синхронними.

**Example:**
```python
async def on_block(config):
    print("Блокування!")

async def main():
    await monitor_logic(
        check_interval=5.0,
        on_block_callback=on_block
    )
```

#### `get_time_remaining(config: Dict[str, Any]) -> Optional[float]`

Отримує залишок часу до блокування через ліміт часу.

**Args:**
- `config`: Конфігурація системи

**Returns:**
- `Optional[float]`: Залишок часу в хвилинах або `None` якщо ліміт не встановлено

#### `get_status_info(config: Dict[str, Any]) -> Dict[str, Any]`

Отримує інформацію про поточний стан системи.

**Args:**
- `config`: Конфігурація системи

**Returns:**
- `Dict[str, Any]`: Словник з інформацією:
  - `blocked`: `bool` - чи заблоковано зараз
  - `force_block`: `bool` - чи активне force block
  - `time_limit`: `Optional[float]` - ліміт часу в хвилинах
  - `time_remaining`: `Optional[float]` - залишок часу в хвилинах
  - `schedule_active`: `bool` - чи активний розклад зараз

### src.core.scheduler

#### `is_within_schedule(schedule_config: Dict[str, Dict[str, Any]]) -> bool`

Перевіряє, чи поточний час знаходиться в межах активного розкладу.

**Args:**
- `schedule_config`: Словник з розкладом на тиждень

**Returns:**
- `bool`: `True` якщо поточний час в межах активного розкладу

**Example:**
```python
from src.core.scheduler import is_within_schedule
from src.core.config import load_config

config = load_config()
schedule = config["schedule"]
if is_within_schedule(schedule):
    print("Зараз час блокування")
```

#### `get_current_day_schedule(schedule_config: Dict[str, Dict[str, Any]]) -> Dict[str, Any] | None`

Отримує розклад для поточного дня тижня.

**Args:**
- `schedule_config`: Словник з розкладом на тиждень

**Returns:**
- `Dict[str, Any] | None`: Розклад для поточного дня або `None`

#### `validate_time_format(time_str: str) -> bool`

Валідує формат часу HH:MM.

**Args:**
- `time_str`: Рядок з часом у форматі HH:MM

**Returns:**
- `bool`: `True` якщо формат валідний

#### `validate_schedule(schedule_config: Dict[str, Dict[str, Any]]) -> bool`

Валідує структуру розкладу.

**Args:**
- `schedule_config`: Словник з розкладом на тиждень

**Returns:**
- `bool`: `True` якщо розклад валідний

## Bot API

### src.bot.handlers

#### `register_handlers(dp: Dispatcher, config: Dict[str, Any]) -> None`

Реєструє всі обробники в dispatcher.

**Args:**
- `dp`: Dispatcher для реєстрації обробників
- `config`: Конфігурація системи

**Реєструє:**
- Команди: `/start`, `/status`, `/shutdown`, `/restart`, `/block`, `/unblock`
- Callback запити: всі callback з клавіатур
- Введення часу: регулярний вираз для HH:MM
- Введення пароля: будь-який текст, якщо очікується пароль

#### `is_admin(user_id: int, config: Dict[str, Any] | None = None) -> bool`

Перевіряє, чи користувач є адміністратором.

**Args:**
- `user_id`: ID користувача Telegram
- `config`: Конфігурація системи (якщо `None`, завантажується автоматично)

**Returns:**
- `bool`: `True` якщо користувач є адміністратором

### src.bot.keyboards

#### `get_main_keyboard() -> InlineKeyboardMarkup`

Повертає головну клавіатуру з основними діями.

**Returns:**
- `InlineKeyboardMarkup`: Клавіатура з кнопками блокування, розкладу, статусу тощо

#### `get_schedule_keyboard(config: Dict[str, Any] | None = None) -> InlineKeyboardMarkup`

Повертає клавіатуру для вибору дня тижня в розкладі.

**Args:**
- `config`: Конфігурація системи (якщо `None`, завантажується автоматично)

**Returns:**
- `InlineKeyboardMarkup`: Клавіатура з кнопками днів тижня та статусом (✅/❌)

#### `get_day_config_keyboard(day_idx: str | int, config: Dict[str, Any] | None = None) -> InlineKeyboardMarkup`

Повертає клавіатуру для налаштування конкретного дня тижня.

**Args:**
- `day_idx`: Індекс дня тижня (0-6, 0=понеділок, 6=неділя)
- `config`: Конфігурація системи (якщо `None`, завантажується автоматично)

**Returns:**
- `InlineKeyboardMarkup`: Клавіатура з опціями налаштування дня

## GUI API

### src.gui.tray_app

#### `class TrayApp`

Додаток у system tray для управління системою.

**Methods:**

- `__init__() -> None`: Ініціалізує додаток у system tray
- `show_settings(first_run: bool = False) -> None`: Показує вікно налаштувань
- `run() -> None`: Запускає додаток

**Example:**
```python
from src.gui.tray_app import TrayApp

app = TrayApp()
app.run()
```

### src.gui.settings_window

#### `class SettingsWindow`

Вікно налаштувань системи батьківського контролю.

**Methods:**

- `__init__(parent: Optional[tk.Tk] = None, is_first_run: bool = False) -> None`: Ініціалізує вікно налаштувань
- `update_qr_code() -> None`: Оновлює QR-код на основі поточного токену
- `save_settings() -> None`: Зберігає налаштування (токен та пароль)

### src.gui.blocking_window

#### `class BlockingWindow`

Вікно блокування комп'ютера з відліком до вимкнення.

**Methods:**

- `__init__(countdown_seconds: int = 60, otp: Optional[str] = None, bot_url: Optional[str] = None) -> None`: Ініціалізує вікно блокування
- `run() -> None`: Запускає головний цикл вікна
- `_set_block_input(block: bool) -> None`: Блокує або розблоковує ввід користувача
- `_shutdown_system() -> None`: Вимикає систему

**Example:**
```python
from src.gui.blocking_window import BlockingWindow

window = BlockingWindow(
    countdown_seconds=60,
    otp="ABCD1234",
    bot_url="https://t.me/bot?start=ABCD1234"
)
window.run()
```

### src.gui.password_dialog

#### `class PasswordDialog`

Діалог для введення батьківського пароля.

**Methods:**

- `__init__(parent: Optional[tk.Tk] = None) -> None`: Ініціалізує діалог введення пароля
- `check_password() -> None`: Перевіряє введений пароль
- `show() -> Optional[bool]`: Показує діалог та очікує результату

**Example:**
```python
from src.gui.password_dialog import PasswordDialog

dialog = PasswordDialog(parent_window)
parent_window.wait_window(dialog.dialog)
if dialog.result:
    print("Пароль правильний")
```

## Utils API

### src.utils.logger

#### `setup_logging(level: int = logging.INFO, log_file: Optional[Path] = None, format_string: Optional[str] = None) -> logging.Logger`

Налаштовує систему логування.

**Args:**
- `level`: Рівень логування (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `log_file`: Шлях до файлу для збереження логів (опціонально)
- `format_string`: Формат повідомлень логування (опціонально)

**Returns:**
- `logging.Logger`: Налаштований логер

#### `get_logger(name: str) -> logging.Logger`

Отримує логер для конкретного модуля.

**Args:**
- `name`: Ім'я модуля (зазвичай `__name__`)

**Returns:**
- `logging.Logger`: Логер для модуля

### src.utils.qr_generator

#### `generate_qr_code(data: str, version: int = 1, box_size: int = 5, border: int = 4, fill_color: str = "black", back_color: str = "white") -> Image.Image`

Генерує QR-код як PIL Image.

**Args:**
- `data`: Дані для кодування в QR-код
- `version`: Версія QR-коду (1-40)
- `box_size`: Розмір кожного квадрата в пікселях
- `border`: Розмір border (мінімум 4)
- `fill_color`: Колір заповнення
- `back_color`: Колір фону

**Returns:**
- `Image.Image`: Зображення QR-коду

#### `create_auth_url(bot_username: str, otp_code: str) -> str`

Створює URL для авторизації через Telegram бота.

**Args:**
- `bot_username`: Username Telegram бота (без @)
- `otp_code`: OTP код для авторизації

**Returns:**
- `str`: URL для авторизації

**Example:**
```python
from src.utils.qr_generator import create_auth_url

url = create_auth_url("mybot", "ABCD1234")
# Повертає: "https://t.me/mybot?start=ABCD1234"
```

### src.utils.telegram_api

#### `get_bot_token() -> Optional[str]`

Отримує токен бота з змінних середовища.

**Returns:**
- `Optional[str]`: Токен бота або `None` якщо не знайдено

#### `get_bot_username(token: Optional[str] = None, timeout: int = 5) -> Optional[str]`

Отримує username Telegram бота через API.

**Args:**
- `token`: Токен бота (якщо `None`, отримується з змінних середовища)
- `timeout`: Таймаут запиту в секундах

**Returns:**
- `Optional[str]`: Username бота (без @) або `None`

**Raises:**
- `requests.RequestException`: Якщо виникла помилка при HTTP запиті

#### `validate_bot_token(token: Optional[str] = None, timeout: int = 5) -> bool`

Перевіряє валідність токену бота.

**Args:**
- `token`: Токен бота (якщо `None`, отримується з змінних середовища)
- `timeout`: Таймаут запиту в секундах

**Returns:**
- `bool`: `True` якщо токен валідний

### src.utils.env_manager

#### `get_bot_token_from_env() -> Optional[str]`

Отримує токен бота з .env файлу.

**Returns:**
- `Optional[str]`: Токен бота або `None` якщо не знайдено

#### `save_bot_token_to_env(token: str) -> bool`

Зберігає токен бота в .env файл.

**Args:**
- `token`: Токен бота для збереження

**Returns:**
- `bool`: `True` якщо успішно збережено

