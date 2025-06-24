# -*- coding: utf-8 -*-
"""
Пакет evocode_gui.

Этот пакет содержит все компоненты, связанные с графическим интерфейсом пользователя (GUI)
приложения EvoCode, построенного на базе PyQt6.

Основной точкой входа в GUI является класс MainWindow.
"""

# "Поднимаем" класс MainWindow из подмодуля main_window в пространство имен этого пакета.
# Это позволяет импортировать его более коротким и удобным способом:
# from evocode_gui import MainWindow
# вместо
# from evocode_gui.main_window import MainWindow
from .main_window import MainWindow

# __all__ определяет список публичных объектов этого пакета.
# Когда кто-то выполнит `from evocode_gui import *`, будет импортирован только MainWindow.
# Это является хорошей практикой для контроля над пространством имен.
__all__ = [
    "MainWindow",
]