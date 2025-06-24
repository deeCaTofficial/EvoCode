import pytest
import os
import time
from unittest.mock import patch, MagicMock

# Импортируем тестируемые компоненты
from src.evocode_core.client import GeminiClient, retry_on_api_error, MAX_API_RETRIES, INITIAL_RETRY_DELAY_SECONDS
from src.evocode_core.exceptions import (
    APIKeyNotFoundError,
    ContentBlockedError,
    CoreError,
    GeminiRateLimitError,
    GeminiServiceUnavailableError,
    GeminiInternalServerError,
    GeminiAPIError
)
from google.api_core import exceptions as google_exceptions

# --- Фикстуры и моки ---

@pytest.fixture(autouse=True)
def mock_genai_configure():
    """Автоматически мокает genai.configure, чтобы избежать реальных вызовов API."""
    with patch("src.evocode_core.client.genai.configure") as mock_configure:
        yield mock_configure
        # Сбрасываем флаг конфигурации после каждого теста для изоляции
        GeminiClient._is_configured = False

@pytest.fixture(autouse=True)
def mock_time_sleep():
    """Мокает time.sleep, чтобы тесты не ждали реально."""
    with patch("src.evocode_core.client.time.sleep") as mock_sleep:
        yield mock_sleep

# --- Тесты для GeminiClient ---

class TestGeminiClient:

    @patch.dict(os.environ, {}, clear=True)
    def test_init_no_api_key(self):
        """Проверяет, что при отсутствии API-ключа выбрасывается APIKeyNotFoundError."""
        with pytest.raises(APIKeyNotFoundError):
            GeminiClient()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}, clear=True)
    def test_init_with_api_key(self, mock_genai_configure):
        """Проверяет успешную инициализацию с ключом и однократную конфигурацию."""
        client = GeminiClient()
        mock_genai_configure.assert_called_once_with(api_key="test_key")
        assert GeminiClient._is_configured is True

        # Проверяем, что configure не вызывается повторно
        mock_genai_configure.reset_mock()
        client2 = GeminiClient()
        mock_genai_configure.assert_not_called()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}, clear=True)
    @patch("src.evocode_core.client.genai.GenerativeModel")
    def test_generate_text_success(self, mock_generative_model):
        """Проверяет успешную генерацию текста."""
        mock_model_instance = MagicMock()
        mock_generative_model.return_value = mock_model_instance
        mock_response = MagicMock()
        mock_response.text = "Generated text"
        mock_response.parts = [MagicMock()] # Убедимся, что parts не пустой
        mock_response.prompt_feedback.block_reason = None
        mock_model_instance.generate_content.return_value = mock_response

        client = GeminiClient()
        result = client.generate_text("system", "user")

        assert result == "Generated text"

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}, clear=True)
    @patch("src.evocode_core.client.genai.GenerativeModel")
    def test_generate_text_content_blocked(self, mock_generative_model):
        """Проверяет, что выбрасывается ContentBlockedError при блокировке ответа."""
        mock_model_instance = MagicMock()
        mock_generative_model.return_value = mock_model_instance
        mock_response = MagicMock()
        mock_response.parts = [] # Пустые parts сигнализируют о проблеме
        mock_response.prompt_feedback.block_reason.name = "SAFETY"
        mock_model_instance.generate_content.return_value = mock_response

        client = GeminiClient()
        with pytest.raises(ContentBlockedError, match="Ответ был заблокирован: SAFETY"):
            client.generate_text("system", "user")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}, clear=True)
    @patch("src.evocode_core.client.genai.GenerativeModel")
    def test_generate_text_returns_function_call(self, mock_generative_model):
        """Проверяет, что при получении function_call возвращается заглушка."""
        mock_model_instance = MagicMock()
        mock_generative_model.return_value = mock_model_instance
        mock_response = MagicMock()
        # Имитируем ошибку при доступе к .text, как это происходит при function_call
        type(mock_response).text = PropertyMock(side_effect=ValueError("No text"))
        mock_response.parts = [MagicMock()]
        mock_model_instance.generate_content.return_value = mock_response

        client = GeminiClient()
        result = client.generate_text("system", "user")
        assert result == "[AI-агент вернул нетекстовый ответ, который не удалось обработать]"

# --- Тесты для декоратора retry_on_api_error ---

class TestRetryOnApiErrorDecorator:

    def test_success_first_attempt(self, mock_time_sleep):
        """Проверяет, что при успехе с первой попытки нет повторов."""
        @retry_on_api_error
        def mock_func():
            return "Success"
        
        assert mock_func() == "Success"
        mock_time_sleep.assert_not_called()

    def test_success_after_retry(self, mock_time_sleep):
        """Проверяет успех после одной повторной попытки."""
        call_count = 0
        @retry_on_api_error
        def mock_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # ИСПРАВЛЕНИЕ: Создаем исключение, затем устанавливаем атрибут
                err = google_exceptions.ResourceExhausted("Rate limit")
                err.code = 429
                raise err
            return "Success"
        
        assert mock_func() == "Success"
        assert call_count == 2
        mock_time_sleep.assert_called_once_with(INITIAL_RETRY_DELAY_SECONDS)

    def test_raises_rate_limit_error_after_all_retries(self, mock_time_sleep):
        """Проверяет, что после всех попыток выбрасывается GeminiRateLimitError."""
        @retry_on_api_error
        def mock_func():
            # ИСПРАВЛЕНИЕ: Создаем исключение, затем устанавливаем атрибут
            err = google_exceptions.ResourceExhausted("Rate limit")
            err.code = 429
            raise err

        with pytest.raises(GeminiRateLimitError):
            mock_func()
        assert mock_time_sleep.call_count == MAX_API_RETRIES - 1

    def test_raises_service_unavailable_error(self, mock_time_sleep):
        """Проверяет, что выбрасывается GeminiServiceUnavailableError."""
        @retry_on_api_error
        def mock_func():
            # ИСПРАВЛЕНИЕ: Создаем исключение, затем устанавливаем атрибут
            err = google_exceptions.ServiceUnavailable("Unavailable")
            err.code = 503
            raise err

        with pytest.raises(GeminiServiceUnavailableError):
            mock_func()

    def test_raises_api_error_for_non_retryable(self, mock_time_sleep):
        """Проверяет, что для не-повторяемых ошибок нет повторных попыток."""
        @retry_on_api_error
        def mock_func():
            # ИСПРАВЛЕНИЕ: Создаем исключение, затем устанавливаем атрибут
            err = google_exceptions.InvalidArgument("Bad request")
            err.code = 400
            raise err

        with pytest.raises(GeminiAPIError):
            mock_func()
        mock_time_sleep.assert_not_called()

    def test_raises_core_error_for_unexpected_exception(self, mock_time_sleep):
        """Проверяет, что любая другая ошибка оборачивается в CoreError."""
        @retry_on_api_error
        def mock_func():
            raise ValueError("Unexpected")

        with pytest.raises(CoreError):
            mock_func()
        mock_time_sleep.assert_not_called()

# Добавляем PropertyMock, если его нет в стандартной unittest.mock (для старых версий Python)
try:
    from unittest.mock import PropertyMock
except ImportError:
    class PropertyMock(MagicMock):
        def __get__(self, obj, obj_type=None):
            return self() 