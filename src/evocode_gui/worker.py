# src/evocode_gui/worker.py
# -*- coding: utf-8 -*-
"""
Содержит логику для выполнения длительных задач в отдельном потоке,
чтобы не замораживать графический интерфейс.
"""
from pathlib import Path
from typing import Dict, Any, List, Union, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from evocode_core import Orchestrator, ImprovementIdea, ImplementationPlan
from evocode_core.exceptions import APIKeyNotFoundError, CoreError

# --- Классы для описания задач ---

class ScanTask:
    """Задача для сканирования директории."""
    def __init__(self, path: Path):
        self.path = path

class EvoTask:
    """Задача для запуска основного цикла EvoCode."""
    def __init__(self, project_path: Path, cycles: int, prompts: Dict[str, Any]):
        self.project_path = project_path
        self.cycles = cycles
        self.prompts = prompts

class Worker(QObject):
    """
    Рабочий, выполняющий задачу в отдельном потоке.
    Транслирует вызовы хуков из Orchestrator в сигналы PyQt.
    """
    # --- Сигналы ---
    finished = pyqtSignal()
    scan_finished = pyqtSignal(dict)
    error = pyqtSignal(str, str)
    stage_changed = pyqtSignal(str)
    idea_approved = pyqtSignal(ImprovementIdea)
    plan_approved = pyqtSignal(ImplementationPlan)
    file_activity_changed = pyqtSignal(str)

    def __init__(self, task: Union[ScanTask, EvoTask]):
        super().__init__()
        self.task = task
        self._is_cancelled = False

    def run(self):
        """Выполняет задачу в зависимости от ее типа."""
        try:
            if isinstance(self.task, ScanTask):
                self._run_scan_task()
            elif isinstance(self.task, EvoTask):
                self._run_evo_task()
        except Exception as e:
            # Отлов самых общих ошибок на верхнем уровне
            error_type = type(e).__name__
            self.error.emit("Непредвиденная ошибка в Worker", f"{error_type}: {e}")
        finally:
            self.finished.emit()
    
    def _run_scan_task(self):
        """Выполняет задачу сканирования директории."""
        try:
            self.stage_changed.emit("Сканирование проекта...")
            structure = self._scan_directory_iterative(self.task.path)
            self.scan_finished.emit(structure)
        except Exception as e:
            self.error.emit("Ошибка сканирования", f"Не удалось просканировать директорию: {e}")

    def _scan_directory_iterative(self, root_path: Path) -> Dict[str, Any]:
        """Итеративно сканирует директорию и возвращает вложенную структуру."""
        structure = {}
        queue = [(root_path, structure)]
        EXCLUDED_DIRS = {'.git', '__pycache__', '.venv', 'venv', 'node_modules', '.idea', '.vscode'}
        EXCLUDED_FILES = {'.DS_Store'}
        while queue:
            current_path, parent_dict = queue.pop(0)
            try:
                entries = sorted(current_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
                for p in entries:
                    if p.name in EXCLUDED_DIRS or p.name in EXCLUDED_FILES or p.name.startswith('.'):
                        continue
                    if p.is_dir():
                        parent_dict[p.name] = {}
                        queue.append((p, parent_dict[p.name]))
                    else:
                        parent_dict[p.name] = "file"
            except OSError:
                continue
        return structure

    def _run_evo_task(self):
        """Выполняет основную задачу EvoCode."""
        # ИСПРАВЛЕНИЕ: Получаем данные из объекта self.task, а не из self
        if not isinstance(self.task, EvoTask):
            self.error.emit("Ошибка Worker", "Неверный тип задачи для выполнения цикла EvoCode.")
            return

        try:
            hooks = {
                'on_stage_change': self.stage_changed.emit,
                'on_idea_approved': self.idea_approved.emit,
                'on_plan_approved': self.plan_approved.emit,
                'is_cancelled': lambda: self._is_cancelled,
                'on_file_activity': self.file_activity_changed.emit
            }
            
            orchestrator = Orchestrator(
                project_path=self.task.project_path, 
                max_cycles=self.task.cycles, 
                prompts=self.task.prompts,
                hooks=hooks
            )
            orchestrator.run()
        except (APIKeyNotFoundError, CoreError) as e:
            self.error.emit("Ошибка ядра EvoCode", str(e))
        except ValueError as e:
            self.error.emit("Ошибка конфигурации", str(e))

    def cancel(self):
        """Устанавливает флаг отмены для Orchestrator."""
        self._is_cancelled = True