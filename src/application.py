# src/application.py
# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# ИСПРАВЛЕНИЕ: Импортируем ConfigurationError из правильного места
from error_handler import (
    EvoCodeError,
    ConfigurationError,
    APIKeyError,
    MissingDependencyError
)
from error_codes import ErrorCodes
from utils.dependency_checker import check_dependencies, CORE_DEPENDENCIES, GUI_DEPENDENCIES
from config.manager import Config
from config import constants
from config.prompt_config import PromptConfig

from evocode_core.exceptions import APIKeyNotFoundError

class Application:
    """
    Главный класс приложения EvoCode, управляющий инициализацией,
    загрузкой конфигурации и запуском в соответствующем режиме.
    """
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.prompts: Optional[Dict[str, Any]] = None

    def _raise_missing_dependency_error(self, missing_dependencies: list[str]):
        """
        Формирует сообщение об ошибке и возбуждает исключение MissingDependencyError.
        """
        if not missing_dependencies:
            return
        deps_str = ", ".join(missing_dependencies)
        message = f"Отсутствуют необходимые зависимости: {deps_str}. Пожалуйста, установите их."
        raise MissingDependencyError(message)

    def _check_dependencies(self):
        """Проверяет наличие необходимых зависимостей."""
        gui_deps_with_qta = GUI_DEPENDENCIES + [{
            "module_name": "qtawesome",
            "friendly_name": "QtAwesome",
            "install_command": "pip install qtawesome"
        }]
        
        all_missing_deps = check_dependencies(CORE_DEPENDENCIES)

        if self.config.get(constants.MODE_KEY) == constants.GUI_MODE:
            all_missing_deps.extend(check_dependencies(gui_deps_with_qta))

        missing_deps_friendly_names = [
            dep_info['friendly_name'] for dep_info in all_missing_deps
        ]

        if missing_deps_friendly_names:
            self._raise_missing_dependency_error(missing_deps_friendly_names)

    @staticmethod
    def _load_prompts_file(config_path: Path) -> Dict[str, Any]:
        """Загружает и парсит YAML-файл с промптами, выполняя валидацию."""
        return PromptConfig.load_and_validate(config_path)

    def _load_config(self) -> Optional[Dict[str, Any]]:
        """Загружает и возвращает конфигурацию промптов приложения."""
        try:
            prompt_config_path = self.config.get(constants.PROMPT_CONFIG_PATH_KEY)
            prompts_config = self._load_prompts_file(prompt_config_path)
            return prompts_config
        except ConfigurationError as e:
            self.logger.error(f"Не удалось загрузить конфигурацию промптов: {e}")
            raise ConfigurationError("Ошибка при загрузке конфигурации")

    def _run_cli_mode(self):
        """Запускает приложение в режиме командной строки."""
        self.logger.info("--- EvoCode CLI Mode ---")
        from evocode_core import Orchestrator
        project_dir = self.config.get(constants.PROJECT_PATH_KEY)
        num_cycles = self.config.get(constants.CYCLES_KEY)
        orchestrator = Orchestrator(
            project_path=project_dir,
            max_cycles=num_cycles,
            prompts=self.prompts
        )
        orchestrator.run()

    def _run_gui_mode(self) -> int:
        """Запускает приложение в графическом режиме."""
        self.logger.info("--- EvoCode GUI Mode ---")
        from PyQt6.QtWidgets import QApplication
        from evocode_gui import MainWindow
        from evocode_gui.styles import MODERN_STYLE_SHEET
        app = QApplication(sys.argv)
        app.setStyleSheet(MODERN_STYLE_SHEET)
        main_win = MainWindow(prompts=self.prompts)
        main_win.show()
        return app.exec()

    def _run_mode(self) -> int:
        """Запускает приложение в соответствующем режиме (CLI или GUI)."""
        try:
            if self.config.get(constants.MODE_KEY) == constants.CLI_MODE:
                self._run_cli_mode()
                return ErrorCodes.SUCCESS.value
            elif self.config.get(constants.MODE_KEY) == constants.GUI_MODE:
                return self._run_gui_mode()
        except APIKeyNotFoundError:
            raise APIKeyError("Ошибка аутентификации API. Пожалуйста, проверьте ваш ключ API.")
        return ErrorCodes.GENERAL_ERROR.value # На случай если режим не определен

    def run(self) -> int:
        """
        Главная точка входа для запуска приложения EvoCode.
        """
        self._check_dependencies()
        self.prompts = self._load_config()

        if self.prompts is None:
            raise ConfigurationError("Не удалось запустить приложение из-за ошибки в конфигурации промптов. См. лог выше.")

        return self._run_mode()