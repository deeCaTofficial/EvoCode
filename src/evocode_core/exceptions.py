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

class GeminiRateLimitError(CoreError):
    """Вызывается, когда превышен лимит запросов к Gemini API (429)."""
    pass

class GeminiServiceUnavailableError(CoreError):
    """Вызывается, когда сервис Gemini API временно недоступен (503)."""
    pass

class GeminiInternalServerError(CoreError):
    """Вызывается, когда Gemini API возвращает внутреннюю ошибку сервера (500)."""
    pass

class GeminiAPIError(CoreError):
    """Базовый класс для всех специфических ошибок Gemini API."""
    pass