# config/prompt_config.py
import yaml
from pathlib import Path
from typing import Dict, Any, List

from error_handler import ConfigurationError
from config import constants


class PromptConfig:
    """
    Утилитарный класс для загрузки и валидации файла конфигурации промптов.
    """

    @staticmethod
    def load_and_validate(file_path: Path) -> Dict[str, Any]:
        """
        Загружает и валидирует YAML-файл с промптами для нескольких агентов.

        Args:
            file_path (Path): Путь к YAML-файлу с промптами.

        Returns:
            Dict[str, Any]: Словарь с загруженными и валидированными промптами.

        Raises:
            ConfigurationError: Если файл не найден, некорректен или не проходит валидацию.
        """
        try:
            with file_path.open('r', encoding='utf-8') as f:
                prompts_data = yaml.safe_load(f)

            if not isinstance(prompts_data, dict) or not prompts_data:
                raise ConfigurationError(
                    f"Содержимое файла конфигурации промптов '{file_path}' должно быть непустым словарем."
                )

            # Проверяем, что у каждого агента есть обязательный ключ 'system_prompt'
            for agent_name, agent_config in prompts_data.items():
                if not isinstance(agent_config, dict):
                    raise ConfigurationError(
                        f"Конфигурация для агента '{agent_name}' в файле '{file_path}' должна быть словарем."
                    )
                
                if constants.SYSTEM_PROMPT_KEY not in agent_config:
                    raise ConfigurationError(
                        f"Отсутствует обязательный ключ '{constants.SYSTEM_PROMPT_KEY}' "
                        f"для агента '{agent_name}' в файле '{file_path}'."
                    )
                
                if not isinstance(agent_config[constants.SYSTEM_PROMPT_KEY], str):
                    raise ConfigurationError(
                        f"Значение для ключа '{constants.SYSTEM_PROMPT_KEY}' у агента '{agent_name}' "
                        f"должно быть строкой."
                    )

            return prompts_data

        except yaml.YAMLError as e:
            raise ConfigurationError(f"Ошибка парсинга YAML в файле '{file_path}': {e}") from e
        except OSError as e:
            raise ConfigurationError(f"Ошибка доступа к файлу конфигурации промптов '{file_path}': {e}") from e