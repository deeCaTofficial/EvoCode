import os
import json
import argparse
from pathlib import Path
import logging
import copy

from config import constants
from error_handler import ConfigurationError
from config.cli_arguments import CLI_ARGUMENTS_DEFINITIONS
from config.validator import ConfigValidator

logger = logging.getLogger(__name__)


class Config:
    """
    Централизованный менеджер конфигурации для приложения EvoCode.
    Загружает настройки из различных источников с определенным приоритетом:
    Defaults -> File -> Environment Variables -> CLI Arguments.
    """
    REDACTED_STRING = "********"

    def __init__(self, root_dir: Path, validator: ConfigValidator):
        self._settings = {}
        self.root_dir = root_dir
        self._default_config_file = self.root_dir / "config" / "config.json"
        self._validator = validator

    def _load_defaults(self):
        """Устанавливает значения по умолчанию для всех известных настроек."""
        self._settings.update({
            constants.PROMPT_CONFIG_PATH_KEY: constants.DEFAULT_PROMPT_CONFIG_PATH,
            constants.API_KEY_ENV_VAR_NAME_KEY: "EVOCODE_API_KEY",
            constants.LOG_FILE_KEY: constants.DEFAULT_LOG_FILE_NAME,
            constants.MODE_KEY: constants.DEFAULT_MODE,
            constants.PROJECT_PATH_KEY: None,
            constants.CYCLES_KEY: constants.DEFAULT_CYCLES,
            constants.API_KEY_KEY: None,
        })
        logger.debug("Defaults loaded: %s", self._settings)

    def _load_from_file(self, filepath: Path):
        """Загружает настройки из JSON-файла."""
        try:
            with filepath.open('r', encoding='utf-8') as f:
                file_settings = json.load(f)
                self._settings.update(file_settings)
                logger.info("Settings loaded from file: %s", filepath)
                logger.debug("File settings: %s", file_settings)
        except FileNotFoundError:
            # If the default config file is not found, it's not an error.
            # It means we'll proceed with defaults and other sources.
            logger.debug("Config file not found at '%s'. Proceeding with defaults and other sources.", filepath)
            return
        except PermissionError as e:
            raise ConfigurationError(f"Permission denied to read config file '{filepath}': {e}") from e
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Error decoding config file '{filepath}': {e}") from e
        except Exception as e:
            raise ConfigurationError(
                f"An unexpected error occurred while loading config file '{filepath}': {e}"
            ) from e

    def _load_from_env(self):
        """Загружает настройки из переменных окружения."""
        api_key_env_var = self._settings.get(constants.API_KEY_ENV_VAR_NAME_KEY)
        if api_key_env_var:
            api_key = os.getenv(api_key_env_var)
            if api_key:
                self._settings[constants.API_KEY_KEY] = api_key
                logger.info("API key loaded from environment variable '%s'.", api_key_env_var)
            else:
                logger.debug("Environment variable '%s' for API key not found.", api_key_env_var)
        logger.debug("Environment variables checked.")

    def _apply_cli_values(self, cli_values: dict):
        """Применяет настройки из аргументов командной строки."""
        self._settings.update(cli_values)
        logger.info("Settings loaded from CLI arguments: %s", cli_values)

    def get_redacted_settings(self):
        """
        Возвращает глубокую копию настроек с скрытым API-ключом для логирования.
        """
        redacted_settings = copy.deepcopy(self._settings)
        if constants.API_KEY_KEY in redacted_settings:
            redacted_settings[constants.API_KEY_KEY] = self.REDACTED_STRING
        return redacted_settings

    def load(self, cli_values: dict = None):
        """
        Главная точка входа для загрузки конфигурации.
        Применяет настройки в порядке приоритета:
        Defaults -> File -> Environment Variables -> CLI Arguments.
        """
        self._load_defaults()
        self._load_from_file(self._default_config_file)
        self._load_from_env()
        if cli_values:
            self._apply_cli_values(cli_values)
        logger.info("Final configuration loaded.")
        logger.debug("Final settings: %s", self.get_redacted_settings())

    def get(self, key: str, default=None):
        """Получает значение настройки по ключу."""
        return self._settings.get(key, default)

    def validate(self):
        """Выполняет базовую валидацию загруженных настроек, используя ConfigValidator."""
        self._validator.validate(self._settings, self.root_dir)
