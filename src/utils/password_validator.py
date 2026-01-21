"""Модуль для валідації батьківського пароля."""

import re
from typing import Dict, List, Tuple


def validate_password(password: str) -> Tuple[bool, List[str], Dict[str, bool]]:
    """Валідує пароль та повертає результат з деталями.
    
    Args:
        password: Пароль для валідації
        
    Returns:
        Tuple[bool, List[str], Dict[str, bool]]: 
            - Чи пароль валідний
            - Список помилок/попереджень
            - Словник з деталями виконання вимог
    """
    errors = []
    requirements = {
        "Мінімум 8 символів": False,
        "Великі літери (A-Z)": False,
        "Малі літери (a-z)": False,
        "Цифри (0-9)": False
    }
    
    # Перевірка довжини
    if len(password) >= 8:
        requirements["Мінімум 8 символів"] = True
    else:
        errors.append("Пароль повинен містити мінімум 8 символів")
    
    # Перевірка великих літер
    if re.search(r'[A-Z]', password):
        requirements["Великі літери (A-Z)"] = True
    else:
        errors.append("Пароль повинен містити хоча б одну велику літеру (A-Z)")
    
    # Перевірка малих літер
    if re.search(r'[a-z]', password):
        requirements["Малі літери (a-z)"] = True
    else:
        errors.append("Пароль повинен містити хоча б одну малу літеру (a-z)")
    
    # Перевірка цифр
    if re.search(r'[0-9]', password):
        requirements["Цифри (0-9)"] = True
    else:
        errors.append("Пароль повинен містити хоча б одну цифру (0-9)")
    
    is_valid = all(requirements.values())
    
    return is_valid, errors, requirements


def get_password_strength(password: str) -> str:
    """Оцінює силу пароля.
    
    Args:
        password: Пароль для оцінки
        
    Returns:
        str: Рівень сили пароля ("weak", "medium", "strong")
    """
    if not password:
        return "weak"
    
    score = 0
    
    # Довжина
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    
    # Різноманітність символів
    if re.search(r'[a-z]', password):
        score += 1
    if re.search(r'[A-Z]', password):
        score += 1
    if re.search(r'[0-9]', password):
        score += 1
    if re.search(r'[^a-zA-Z0-9]', password):
        score += 1
    
    if score <= 2:
        return "weak"
    elif score <= 4:
        return "medium"
    else:
        return "strong"
