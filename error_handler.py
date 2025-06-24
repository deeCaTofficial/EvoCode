import logging
import sys
from error_codes import ErrorCodes

logger = logging.getLogger(__name__)


class EvoCodeError(Exception):
    """
    Базовый класс для всех пользовательских исключений EvoCode.
    Содержит сообщение об ошибке и соответствующий код выхода.
    """
    exit_code = ErrorCodes.GENERAL_ERROR

    def __init__(self, message: str):
        super().__init__(message)


class ConfigurationError(EvoCodeError):
    """Исключение, связанное с ошибками конфигурации."""
    exit_code = ErrorCodes.CONFIGURATION_ERROR


class APIKeyError(EvoCodeError):
    """Исключение, связанное с ошибками API-ключа."""
    exit_code = ErrorCodes.API_KEY_ERROR


class MissingDependencyError(EvoCodeError):
    """Исключение, связанное с отсутствующими зависимостями."""
    exit_code = ErrorCodes.MISSING_DEPENDENCY


class InvalidInputError(EvoCodeError):
    """Исключение, связанное с некорректным вводом."""
    exit_code = ErrorCodes.INVALID_INPUT


class NetworkError(EvoCodeError):
    """Исключение, связанное с сетевыми ошибками."""
    exit_code = ErrorCodes.NETWORK_ERROR


def exit_with_error(e: Exception) -> int:
    """
    Логирует исключение и возвращает соответствующий код выхода.

    Args:
        e (Exception): Экземпляр исключения.

    Returns:
        int: Код выхода, соответствующий типу ошибки.
    """
    if isinstance(e, EvoCodeError):
        return e.exit_code.value
    else:
        return ErrorCodes.GENERAL_ERROR.value
