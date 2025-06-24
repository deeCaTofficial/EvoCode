import importlib
from pathlib import Path


CORE_DEPENDENCIES = [
    {
        "module_name": "yaml",
        "friendly_name": "PyYAML",
        "install_command": "pip install PyYAML"
    }
]

GUI_DEPENDENCIES = [
    {
        "module_name": "PyQt6",
        "friendly_name": "PyQt6",
        "install_command": "pip install PyQt6"
    }
]


def check_dependencies(dependencies_list: list[dict]) -> list[dict]:
    """
    Проверяет наличие указанных зависимостей.

    Args:
        dependencies_list (list[dict]): Список словарей с информацией о зависимостях.

    Возвращает:
        list[dict]: Список словарей, где каждый словарь представляет отсутствующую
                   зависимость и содержит ключи 'friendly_name' (строка) и
                   'install_command' (строка). Если все зависимости присутствуют,
                   возвращает пустой список.
    """
    missing_dependencies = []
    for dep_info in dependencies_list:
        try:
            importlib.import_module(dep_info["module_name"])
        except ImportError:
            missing_dependencies.append(
                {
                    "friendly_name": dep_info["friendly_name"],
                    "install_command": dep_info["install_command"]
                }
            )
    return missing_dependencies
