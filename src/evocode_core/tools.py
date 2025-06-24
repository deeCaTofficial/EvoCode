# src/evocode_core/tools.py
# -*- coding: utf-8 -*-
"""
Определяет набор "инструментов", которые AI-агент может вызывать для взаимодействия
с файловой системой, средой выполнения (pytest) и системой контроля версий (Git).
"""
import os
import sys
import subprocess
from pathlib import Path
from typing import List, Callable, Optional

class ToolError(Exception):
    """Специальное исключение для ошибок, возникающих при выполнении инструментов."""
    pass

class FileSystemTools:
    """Набор инструментов для работы с файловой системой проекта и Git."""

    def __init__(self, project_root: Path, on_activity: Optional[Callable[[str], None]] = None):
        """
        Инициализирует инструменты.

        Args:
            project_root: Корневая директория проекта, в рамках которой будут работать инструменты.
            on_activity: Опциональный callback, который будет вызываться с путем к файлу
                         при каждой операции чтения/записи.
        """
        self.project_root = project_root.resolve()
        self.on_activity = on_activity

    def _resolve_path(self, path: str) -> Path:
        """
        Преобразует относительный путь в абсолютный и безопасный путь внутри проекта.
        Предотвращает выход за пределы корневой директории проекта (Directory Traversal).
        """
        # Нормализуем путь (убираем '..', '.', и т.д.)
        abs_path = (self.project_root / path).resolve()
        
        # Проверяем, что разрешенный путь находится внутри корневой директории проекта
        if self.project_root not in abs_path.parents and abs_path != self.project_root:
            raise ToolError(f"Ошибка безопасности: Попытка доступа к файлу вне директории проекта: {path}")
            
        return abs_path

    def _run_git_command(self, *args) -> str:
        """Вспомогательный метод для безопасного выполнения команд Git."""
        try:
            # Проверяем, что мы в Git репозитории
            check_proc = subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], cwd=self.project_root, capture_output=True, text=True, check=False)
            if check_proc.returncode != 0 or "true" not in check_proc.stdout:
                raise ToolError("Проект не является Git-репозиторием. Инициализируйте его (`git init`).")

            proc = subprocess.run(['git'] + list(args), cwd=self.project_root, capture_output=True, text=True, check=True, encoding='utf-8')
            return proc.stdout.strip()
        except FileNotFoundError:
            raise ToolError("Команда 'git' не найдена. Убедитесь, что Git установлен и доступен в PATH.")
        except subprocess.CalledProcessError as e:
            raise ToolError(f"Ошибка выполнения Git команды: {e.stderr}")

    # --- Инструменты, доступные для AI ---

    def list_files(self, path: str = ".") -> str:
        """Показывает древовидную структуру файлов и папок по указанному пути внутри проекта."""
        if self.on_activity: self.on_activity(path)
        try:
            target_path = self._resolve_path(path)
            if not target_path.is_dir():
                return f"Ошибка: '{path}' не является директорией."

            tree_lines = [f"Структура директории '{path}':"]
            entries = sorted(target_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            for item in entries:
                if item.name.startswith('.') or item.name in ['__pycache__', 'venv', '.venv', 'node_modules']:
                    continue
                entry = f"{item.name}/" if item.is_dir() else item.name
                tree_lines.append(f"- {entry}")
            return "\n".join(tree_lines)
        except Exception as e: return f"Ошибка при листинге файлов: {e}"

    def read_file(self, path: str) -> str:
        """Читает и возвращает содержимое текстового файла по указанному пути."""
        if self.on_activity: self.on_activity(path)
        try:
            file_path = self._resolve_path(path)
            if not file_path.is_file(): return f"Ошибка: Файл не найден по пути '{path}'."
            return file_path.read_text(encoding='utf-8')
        except Exception as e: return f"Ошибка при чтении файла: {e}"

    def write_file(self, path: str, content: str) -> str:
        """Записывает (или перезаписывает) предоставленное содержимое в текстовый файл."""
        if self.on_activity: self.on_activity(path)
        try:
            file_path = self._resolve_path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
            return f"Файл '{path}' успешно сохранен."
        except Exception as e: return f"Ошибка при записи файла: {e}"

    def apply_patch(self, path: str, old_code: str, new_code: str) -> str:
        """Применяет точечное изменение к файлу, заменяя блок 'old_code' на 'new_code'."""
        if self.on_activity: self.on_activity(path)
        try:
            file_path = self._resolve_path(path)
            if not file_path.is_file(): return f"Ошибка: Файл для патча не найден по пути '{path}'."
            original_content = file_path.read_text(encoding='utf-8')
            if old_code not in original_content:
                return f"Ошибка: Не удалось применить патч. Блок кода для замены не найден в файле '{path}'."
            updated_content = original_content.replace(old_code, new_code, 1)
            file_path.write_text(updated_content, encoding='utf-8')
            return f"Патч успешно применен к файлу '{path}'."
        except Exception as e: return f"Ошибка при применении патча: {e}"

    def run_tests(self, test_path: str = ".") -> str:
        """Запускает pytest для указанной директории или файла и возвращает результат."""
        try:
            target_path = self._resolve_path(test_path)
            command = [sys.executable, "-m", "pytest", str(target_path)]
            result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', cwd=self.project_root)
            if result.returncode == 0: return f"УСПЕХ: Все тесты пройдены.\n\nВывод:\n{result.stdout}"
            elif result.returncode == 5: return f"ИНФО: Тесты не найдены по пути '{test_path}'.\n\nВывод:\n{result.stdout}"
            else: return f"ПРОВАЛ: Тесты не пройдены (код {result.returncode}).\n\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        except FileNotFoundError: return "Ошибка: Команда pytest не найдена. Убедитесь, что pytest установлен."
        except Exception as e: return f"Ошибка при запуске тестов: {e}"

    def git_is_clean(self) -> bool:
        """Проверяет, является ли рабочая директория 'чистой' (нет несохраненных изменений)."""
        return not bool(self._run_git_command('status', '--porcelain'))

    def git_add_all(self) -> str:
        """Добавляет все файлы в индекс."""
        return self._run_git_command('add', '.')

    def git_commit(self, message: str) -> str:
        """Создает коммит из индексированных файлов."""
        return self._run_git_command('commit', '-m', message)

    def git_stash_create(self) -> str:
        """Сохраняет текущие изменения во временном хранилище (stash)."""
        return self._run_git_command('stash', 'push', '-u', '-m', 'evocode_autostash')

    def git_stash_revert(self) -> str:
        """Отменяет все изменения, возвращаясь к последнему состоянию до запуска."""
        try:
            self._run_git_command('stash', 'pop')
        except ToolError as e:
            if 'No stash entries found' not in str(e):
                raise  # Перебрасываем другие ошибки Git
            # Если stash не найден, это нормально. Просто очищаем рабочую директорию.
        
        self._run_git_command('restore', '--staged', '.')
        self._run_git_command('restore', '.')
        self._run_git_command('clean', '-fd')
        return "Все изменения, внесенные AI, были успешно отменены."
        
    def git_stash_commit(self, message: str) -> str:
        """Применяет изменения из stash и делает коммит."""
        try:
            self._run_git_command('stash', 'pop')
        except ToolError as e:
            if 'No stash entries found' in str(e):
                return "AI не внес фактических изменений в код. Коммит не требуется."
            raise  # Перебрасываем другие ошибки Git

        self._run_git_command('add', '.')
        
        # Проверяем, есть ли что-то в индексе для коммита
        try:
            # Команда `diff-index` вернет ошибку (не-нулевой код), если есть изменения
            self._run_git_command('diff-index', '--quiet', 'HEAD')
            return "Изменения были применены, но не привели к фактическим правкам. Коммит не создан."
        except ToolError:
            # Есть изменения, делаем коммит
            return self._run_git_command('commit', '-m', message)

def finish(reason: str) -> str:
    """
    Инструмент, который AI должен вызвать, когда считает, что полностью выполнил поставленную задачу.
    """
    return f"Работа завершена. Причина: {reason}"