from config import constants
import argparse
from pathlib import Path

CLI_ARGUMENTS_DEFINITIONS = [
    # Global arguments
    {
        "target_parser": "main",
        "args": [f'--{constants.PROMPT_CONFIG_PATH_KEY.replace("_", "-")}'],
        "kwargs": {
            "type": Path,
            "dest": constants.PROMPT_CONFIG_PATH_KEY,
            "help": f"Путь к YAML-файлу с промптами (по умолчанию: {constants.DEFAULT_PROMPT_CONFIG_PATH}, относительно корня приложения)."
        }
    },
    {
        "target_parser": "main",
        "args": [f'--{constants.LOG_FILE_KEY.replace("_", "-")}'],
        "kwargs": {
            "type": Path,
            "dest": constants.LOG_FILE_KEY,
            "help": f"Путь к файлу логов (по умолчанию: {constants.DEFAULT_LOG_FILE_NAME} в текущей рабочей директории)."
        }
    },
    # CLI mode arguments
    {
        "target_parser": constants.CLI_MODE,
        "args": [f'--{constants.PROJECT_PATH_KEY.replace("_", "-")}'],
        "kwargs": {
            "type": Path,
            "required": True,
            "dest": constants.PROJECT_PATH_KEY,
            "help": "Путь к директории анализируемого проекта."
        }
    },
    {
        "target_parser": constants.CLI_MODE,
        "args": [f'--{constants.CYCLES_KEY.replace("_", "-")}'],
        "kwargs": {
            "type": int,
            "default": constants.DEFAULT_CYCLES,
            "dest": constants.CYCLES_KEY,
            "help": f"Количество полных циклов улучшения (по умолчанию: {constants.DEFAULT_CYCLES})."
        }
    },
    # GUI mode arguments (none specific yet)
]

SUBPARSER_DEFINITIONS = [
    {
        "name": constants.CLI_MODE,
        "help": "Запустить EvoCode в режиме командной строки.",
        "formatter_class": argparse.RawTextHelpFormatter
    },
    {
        "name": constants.GUI_MODE,
        "help": "Запустить EvoCode в графическом интерфейсе.",
        "formatter_class": None
    }
]
