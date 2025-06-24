# src/evocode_core/client.py
# -*- coding: utf-8 -*-
"""
Production-grade клиент для взаимодействия с API Google Gemini.
Инкапсулирует логику запросов, обработку ошибок и повторные попытки.
"""
import os
import logging
import time
from functools import wraps
from typing import List, Callable, Any, Optional, Dict, Union, TypedDict

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    from google.generativeai.generative_models import ChatSession
    from google.api_core import exceptions
except ImportError:
    # Эта ошибка будет поймана на уровне Application при запуске
    raise

from .exceptions import APIKeyNotFoundError, ContentBlockedError, CoreError

log = logging.getLogger(__name__)

# --- Константы ---
MAX_API_RETRIES = 3
INITIAL_RETRY_DELAY_SECONDS = 5

# --- Типизация для ответов от клиента ---
class GeminiResponse(TypedDict, total=False):
    text: Optional[str]
    function_call: Optional[Any] # Используем Any для совместимости

# --- Декоратор для повторных попыток ---
def retry_on_api_error(func: Callable) -> Callable:
    """
    Декоратор для обработки ошибок API с экспоненциальной выдержкой.
    Ловит ResourceExhausted (429) и временные ошибки сервера (5xx).
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        last_exception = None
        for attempt in range(MAX_API_RETRIES):
            try:
                return func(*args, **kwargs)
            except (exceptions.ResourceExhausted, exceptions.ServiceUnavailable, exceptions.InternalServerError) as e:
                last_exception = e
                delay = INITIAL_RETRY_DELAY_SECONDS * (2 ** attempt)
                log.warning(
                    f"Ошибка API ({type(e).__name__}). Попытка {attempt + 1}/{MAX_API_RETRIES}. "
                    f"Повтор через {delay} сек..."
                )
                time.sleep(delay)
            except exceptions.GoogleAPICallError as e:
                log.error(f"Невосстановимая ошибка вызова API: {e}")
                raise CoreError(f"Ошибка вызова API: {e}") from e

        log.error("Не удалось выполнить запрос к API после нескольких попыток.")
        raise CoreError("Превышен лимит запросов к API или сервис временно недоступен.") from last_exception
    return wrapper

class GeminiClient:
    """
    Клиент для работы с Google Gemini API, инкапсулирующий конфигурацию и сессии.
    """
    _is_configured = False
    PRO_MODEL_NAME = "gemini-2.5-flash"
    FLASH_MODEL_NAME = "gemini-2.0-flash"

    def __init__(self):
        self._ensure_configured()
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        self.generation_config = {"temperature": 0.2}

    def _ensure_configured(self):
        """Гарантирует, что глобальная конфигурация genai вызывается только один раз."""
        if not GeminiClient._is_configured:
            api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('EVOCODE_API_KEY')
            if not api_key:
                raise APIKeyNotFoundError("Переменная окружения для API ключа не найдена.")
            genai.configure(api_key=api_key)
            GeminiClient._is_configured = True
            log.info("Клиент Gemini успешно сконфигурирован.")

    @retry_on_api_error
    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        """Генерирует простой текстовый ответ, используя менее мощную модель."""
        log.info("Запрос на генерацию текста...")
        model = genai.GenerativeModel(
            self.FLASH_MODEL_NAME,
            system_instruction=system_prompt,
            safety_settings=self.safety_settings
        )
        response = model.generate_content(user_prompt)
        if not response.parts and hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
            raise ContentBlockedError(f"Ответ был заблокирован: {response.prompt_feedback.block_reason.name}")
        
        try:
            # Пытаемся получить текст напрямую
            return response.text
        except ValueError as e:
            # Обработка случая, когда модель возвращает function_call вместо текста
            log.warning(f"Не удалось преобразовать ответ в текст (возможно, был возвращен function_call): {e}")
            return "[AI-агент вернул нетекстовый ответ, который не удалось обработать]"

    def start_tool_chat(self, system_prompt: str, tools: List[Callable]) -> ChatSession:
        """Начинает новую сессию чата с инструментами, используя мощную модель."""
        log.info("Запуск новой сессии чата с инструментами...")
        model = genai.GenerativeModel(
            self.PRO_MODEL_NAME,
            system_instruction=system_prompt,
            tools=tools,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings
        )
        return model.start_chat(enable_automatic_function_calling=False)

    @retry_on_api_error
    def send_message(self, chat_session: ChatSession, message: Union[str, List[Dict]]) -> GeminiResponse:
        """Отправляет сообщение в чат и парсит ответ в типизированный словарь."""
        log.info(f"Отправка сообщения в чат: {str(message)[:150]}...")
        response = chat_session.send_message(message)
        
        if not response.candidates or not response.candidates[0].content.parts:
            raise CoreError("AI вернул пустой или невалидный ответ.")

        part = response.candidates[0].content.parts[0]
        
        if hasattr(part, 'function_call') and part.function_call.name:
            return {"function_call": part.function_call}
        
        return {"text": response.text}