# src/evocode_core/exceptions.py
# -*- coding: utf-8 -*-
"""
Определяет пользовательские исключения для пакета evocode_core.
"""

class CoreError(Exception):
    """Базовый класс для исключений в evocode_core."""
    pass

class APIKeyNotFoundError(CoreError):
    """Вызывается, когда API-ключ Gemini не найден."""
    pass

class ContentBlockedError(CoreError):
    """Вызывается, когда Gemini блокирует ответ из-за настроек безопасности."""
    pass