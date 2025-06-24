"""
Централизованное определение кодов выхода для приложения EvoCode.
"""
from enum import IntEnum


class ErrorCodes(IntEnum):
    SUCCESS = 0
    GENERAL_ERROR = 1
    CONFIGURATION_ERROR = 2
    API_KEY_ERROR = 3
    MISSING_DEPENDENCY = 4
    NETWORK_ERROR = 5
    INVALID_INPUT = 6
    FILE_NOT_FOUND = 7
