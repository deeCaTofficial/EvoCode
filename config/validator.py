import logging
from pathlib import Path
from typing import Union

from error_handler import ConfigurationError, APIKeyError
from config import constants

logger = logging.getLogger(__name__)


class ConfigValidator:
    """
    Класс для инкапсуляции всей логики валидации конфигурации EvoCode.
    """

    def _resolve_and_validate_path(self, path_val: Union[str, Path], root_dir: Path, must_exist: bool = False, is_file: bool = False, is_dir: bool = False, config_key: str = None) -> Path:
        """
        Вспомогательный метод для преобразования значения пути в абсолютный объект Path
        и выполнения базовой валидации.
        """
        try:
            resolved_path = Path(path_val)
            if not resolved_path.is_absolute():
                resolved_path = root_dir / resolved_path

            if must_exist:
                if not resolved_path.exists():
                    raise FileNotFoundError(f"Путь не существует: {resolved_path}")
                if is_file and not resolved_path.is_file():
                    raise ValueError(f"Путь не является файлом: {resolved_path}")
                if is_dir and not resolved_path.is_dir():
                    raise ValueError(f"Путь не является директорией: {resolved_path}")

            return resolved_path
        except (FileNotFoundError, ValueError) as e:
            key_info = f" для ключа '{config_key}'" if config_key else ""
            raise ConfigurationError(f"Некорректная конфигурация пути{key_info}: {e}") from e
        except Exception as e:
            key_info = f" для ключа '{config_key}'" if config_key else ""
            raise ConfigurationError(f"Неожиданная ошибка при разрешении пути{key_info}: {e}") from e

    def _set_and_validate_path_setting(self, config_data: dict, config_key: str, root_dir: Path, must_exist: bool = False, is_file: bool = False, is_dir: bool = False):
        """
        Resolves and validates a path setting, updating the config_data dictionary.
        """
        path_val = config_data.get(config_key)

        if path_val is None:
            if must_exist:
                raise ConfigurationError(f"Обязательный путь для ключа '{config_key}' не указан.")
            else:
                logger.debug(f"Path for '{config_key}' is None and not mandatory, skipping resolution.")
                return

        if not isinstance(path_val, (str, Path)):
            raise ConfigurationError(
                f"Значение для '{config_key}' должно быть строкой или объектом Path, получено: {type(path_val).__name__}."
            )

        resolved_path = self._resolve_and_validate_path(
            path_val, root_dir, must_exist=must_exist, is_file=is_file, is_dir=is_dir, config_key=config_key
        )
        config_data[config_key] = resolved_path
        logger.debug(f"Path for '{config_key}' resolved to: {resolved_path}")

    def _validate_cli_mode_settings(self, config_data: dict, root_dir: Path):
        """Валидирует настройки, специфичные для режима CLI."""
        self._set_and_validate_path_setting(config_data, constants.PROJECT_PATH_KEY, root_dir, must_exist=True, is_dir=True)

        cycles = config_data.get(constants.CYCLES_KEY)
        if not isinstance(cycles, int) or cycles <= 0:
            raise ConfigurationError(
                f"'{constants.CYCLES_KEY}' является обязательным и должен быть положительным целым числом в режиме CLI."
            )
        logger.debug("Настройки режима CLI проверены.")

    def _resolve_and_validate_paths(self, config_data: dict, root_dir: Path):
        """
        Resolves relative paths to absolute Path objects and performs existence checks
        for paths that are always expected or generally configured.
        """
        self._set_and_validate_path_setting(config_data, constants.PROMPT_CONFIG_PATH_KEY, root_dir, must_exist=True, is_file=True)
        self._set_and_validate_path_setting(config_data, constants.LOG_FILE_KEY, root_dir, must_exist=False)
        logger.debug("Common paths resolved and validated.")

    def validate(self, config_data: dict, root_dir: Path):
        """Выполняет базовую валидацию загруженных настроек."""
        current_mode = config_data.get(constants.MODE_KEY)

        # First, resolve all paths to Path objects. This also performs existence checks where `must_exist=True`.
        self._resolve_and_validate_paths(config_data, root_dir)

        # Validate API key
        api_key = config_data.get(constants.API_KEY_KEY)
        if not api_key: # Checks for None or empty string
            raise APIKeyError(
                "API ключ не найден. Пожалуйста, убедитесь, что он предоставлен через переменную окружения, "
                "файл конфигурации или аргументы командной строки."
            )

        # Then, perform mode-specific validations based on the resolved paths.
        if current_mode == constants.CLI_MODE:
            self._validate_cli_mode_settings(config_data, root_dir)

        logger.info("Конфигурация успешно проверена.")