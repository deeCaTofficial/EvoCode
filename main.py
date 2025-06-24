# main.py
# -*- coding: utf-8 -*-
"""
Главная точка входа для приложения EvoCode.
Отвечает за парсинг аргументов командной строки, загрузку конфигурации
и запуск приложения в соответствующем режиме (GUI или CLI).
"""
import logging
import sys
import argparse
from pathlib import Path

# --- ИСПРАВЛЕНИЕ: Настройка sys.path для корректного импорта из 'src' ---
# Это необходимо делать ДО того, как мы попытаемся импортировать что-либо из 'src'.
ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))
# -------------------------------------------------------------------------

# Импорт обработчика ошибок и кодов выхода в самом начале, так как они фундаментальны
from error_handler import (
    exit_with_error,
    EvoCodeError
)
from error_codes import ErrorCodes

# Импорт класса Application
from src.application import Application
from config.manager import Config
from config.logging_config import setup_logging
from config import constants
from config.cli_arguments import CLI_ARGUMENTS_DEFINITIONS, SUBPARSER_DEFINITIONS
from config.validator import ConfigValidator

# Инициализация логгера на уровне модуля
logger = logging.getLogger(__name__)


def _parse_cli_arguments() -> argparse.Namespace:
    """Парсит аргументы командной строки для приложения EvoCode."""
    parser = argparse.ArgumentParser(
        description="EvoCode: AI-ассистент для эволюционного улучшения кода.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    subparsers = parser.add_subparsers(
        dest=constants.MODE_KEY,
        help=f'Режим запуска приложения: "{constants.CLI_MODE}" или "{constants.GUI_MODE}".'
             f'\nЕсли режим не указан, по умолчанию запускается "{constants.GUI_MODE}".'
    )

    parser_map = {"main": parser}

    for sub_def in SUBPARSER_DEFINITIONS:
        parser_name = sub_def["name"]
        parser_kwargs = {"help": sub_def["help"]}
        if sub_def["formatter_class"]:
            parser_kwargs["formatter_class"] = sub_def["formatter_class"]

        sub_parser = subparsers.add_parser(parser_name, **parser_kwargs)
        parser_map[parser_name] = sub_parser

    for arg_def in CLI_ARGUMENTS_DEFINITIONS:
        target = arg_def["target_parser"]
        parser_map[target].add_argument(*arg_def["args"], **arg_def["kwargs"])

    args = parser.parse_args()

    # Если режим не указан в аргументах, используем режим по умолчанию
    if args.mode is None:
        args.mode = constants.DEFAULT_MODE

    return args


def _load_configuration(cli_values: dict, root_dir: Path) -> Config:
    """Инициализирует и загружает конфигурацию приложения."""
    validator = ConfigValidator()
    app_config = Config(root_dir=root_dir, validator=validator)
    app_config.load(cli_values=cli_values)
    app_config.validate()
    return app_config


def _setup_logging(config: Config):
    """Настраивает логирование для приложения."""
    log_file_path = config.get(constants.LOG_FILE_KEY)
    setup_logging(log_file_path)


def _run_application(config: Config):
    """Инициализирует и запускает основное приложение EvoCode."""
    app = Application(config)
    exit_code = app.run()
    sys.exit(exit_code)


def main():
    """Главная функция: парсинг аргументов и запуск нужного режима."""
    # ROOT_DIR уже определен на уровне модуля
    try:
        args = _parse_cli_arguments()
        cli_config_dict = {
            key: value for key, value in vars(args).items() if value is not None
        }

        config = _load_configuration(cli_config_dict, ROOT_DIR)
        _setup_logging(config)

        logger.info("Starting EvoCode application...")
        _run_application(config)

    except EvoCodeError as e:
        sys.exit(exit_with_error(e))
    except Exception as e:
        # Логируем с traceback только если логгер уже настроен
        if logger.hasHandlers():
            logger.exception("An unexpected error occurred during application execution.")
        else:
            print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(ErrorCodes.GENERAL_ERROR.value)


if __name__ == "__main__":
    main()