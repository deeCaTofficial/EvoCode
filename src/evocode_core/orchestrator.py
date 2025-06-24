# src/evocode_core/orchestrator.py
# -*- coding: utf-8 -*-
"""
Главный класс-оркестратор, управляющий адаптивным процессом
эволюционного улучшения кода с использованием Git для безопасности.
"""
import json
import re
from pathlib import Path
# ИСПРАВЛЕНИЕ: Добавляем tuple из typing для корректной аннотации
from typing import Dict, Any, Optional, List, Type, Callable, TypeVar, TypedDict, Tuple

from .agents import create_agent, BaseAgent, AgentExecutionResult
from .models import ImprovementIdea, ImplementationPlan
from .exceptions import CoreError
from .client import GeminiClient
from .tools import FileSystemTools

T = TypeVar('T')

class ProgressHooks(TypedDict, total=False):
    on_stage_change: Callable[[str], None]
    on_idea_approved: Callable[[ImprovementIdea], None]
    on_plan_approved: Callable[[ImplementationPlan], None]
    is_cancelled: Callable[[], bool]
    on_file_activity: Callable[[str], None]

class Orchestrator:
    """
    Управляет высокоуровневым, адаптивным потоком AI-агентов для улучшения кода,
    используя Git для обеспечения безопасности и атомарности операций.
    """
    MAX_REPAIR_ATTEMPTS = 3
    MAX_GENERATION_ATTEMPTS = 3

    def __init__(self, project_path: Path, max_cycles: int, prompts: Dict[str, Any], hooks: ProgressHooks = None):
        if not project_path.is_dir():
            raise CoreError(f"Указанный путь не является директорией: {project_path}")
        self.project_path = project_path
        self.max_cycles = max_cycles
        self.hooks = hooks or {}
        self.client = GeminiClient()
        self.agents = self._create_agents(prompts)
        self.fs_tools = FileSystemTools(project_root=self.project_path)
        self.initial_context: Optional[str] = None

    def _create_agents(self, prompts: Dict[str, Any]) -> Dict[str, BaseAgent]:
        self._report_progress("Инициализация AI-агентов...")
        if not prompts or not isinstance(prompts, dict):
            raise CoreError("Ошибка конфигурации: промпты не были загружены.")
        
        agents = {}
        for name, data in prompts.items():
            agents[name] = create_agent(
                agent_name=name,
                system_prompt=data['system_prompt'],
                client=self.client,
                project_path=self.project_path
            )
        self._report_progress("Агенты успешно созданы.")
        return agents

    def _read_project_context(self, file_paths: Optional[List[Path]] = None) -> str:
        self._report_progress("Анализ контекста проекта...")
        
        if file_paths is None:
            scan_paths = self.project_path.rglob('*.py')
        else:
            scan_paths = file_paths

        files_to_read = [
            p for p in scan_paths
            if '.git' not in p.parts and '__pycache__' not in p.parts and 'venv' not in p.parts
        ]

        if not files_to_read:
            return "В проекте не найдено релевантных файлов для анализа."
        
        # Здесь может быть более сложная логика построения дерева
        structure_str = "Структура проекта:\n" + "\n".join(f"- {p.relative_to(self.project_path)}" for p in files_to_read)
            
        content_lines = ["\nСодержимое файлов:"]
        for path in files_to_read:
            relative_path = str(path.relative_to(self.project_path)).replace('\\', '/')
            content_lines.append(f"\n# --- File: {relative_path} ---")
            try:
                content_lines.append(path.read_text(encoding="utf-8"))
            except Exception as e:
                content_lines.append(f"# Ошибка чтения файла: {e}")
        
        return structure_str + "\n\n" + "\n".join(content_lines)

    def _report_progress(self, message: str):
        print(message)
        if 'on_stage_change' in self.hooks:
            self.hooks['on_stage_change'](message)

    def _is_cancelled(self) -> bool:
        return self.hooks.get('is_cancelled', lambda: False)()

    def _execute_agent_step(self, step_name: str, agent_name: str, context: Any, expected_model: Optional[Type[T]] = None) -> Optional[T]:
        self._report_progress(f"\n{step_name}...")
        for attempt in range(self.MAX_GENERATION_ATTEMPTS):
            if self._is_cancelled(): return None
            self._report_progress(f"  Попытка {attempt + 1}/{self.MAX_GENERATION_ATTEMPTS}...")
            
            result = self.agents[agent_name].execute(context, expected_model=expected_model)
            
            if result['status'] == 'success':
                self._report_progress(f"  Шаг '{step_name}' выполнен успешно.")
                return result['message']
            else:
                self._report_progress(f"  Попытка провалена. Ошибка: {result['message']}")
        
        self._report_progress(f"Не удалось выполнить шаг '{step_name}' после нескольких попыток.")
        return None

    def run(self) -> None:
        """Запускает главный цикл улучшений с проверкой и управлением Git."""
        self._report_progress(f"Запуск процесса для проекта: {self.project_path}")
        
        try:
            if not self.fs_tools.git_is_clean():
                self._report_progress("Рабочая директория не 'чистая'. Автоматический коммит изменений...")
                self.fs_tools.git_add_all()
                self.fs_tools.git_commit("Auto-commit: Сохранение незафиксированных изменений перед запуском EvoCode")
                self._report_progress("Изменения успешно закоммичены.")

        except CoreError as e:
            self._report_progress(f"ОШИБКА: {e}")
            return

        for i in range(self.max_cycles):
            if self._is_cancelled(): break
            self._report_progress(f"\n{'='*20} Глобальный цикл #{i + 1}/{self.max_cycles} {'='*20}")
            
            self.initial_context = self._read_project_context()
            
            self.fs_tools.git_stash_create()
            self._report_progress("Создана точка отката (git stash).")

            is_success, commit_title = self.run_full_cycle()
            
            if is_success:
                commit_msg_context = f"Идея: {commit_title}\nРезультат: Изменения успешно реализованы и протестированы."
                # Предполагаем, что commit_message_generator есть в prompts.yaml
                commit_agent_name = 'commit_message_generator'
                if commit_agent_name in self.agents:
                    commit_msg_result = self.agents[commit_agent_name].execute(commit_msg_context)
                    commit_message = commit_msg_result['message'] if commit_msg_result['status'] == 'success' else f"refactor: Apply '{commit_title}'"
                else:
                    commit_message = f"refactor: Apply '{commit_title}'"

                self.fs_tools.git_stash_commit(commit_message)
                self._report_progress(f"Изменения успешно применены и сохранены в коммите.")
            else:
                self.fs_tools.git_stash_revert()
                self._report_progress("Цикл завершился неудачей. Все изменения отменены.")
                break
                
        self._report_progress("\nВсе циклы EvoCode завершены.")

    def run_full_cycle(self) -> Tuple[bool, str]:
        """Выполняет один адаптивный проход по агентам и возвращает (успех, заголовок_идеи)."""
        if self._is_cancelled(): return False, ""

        ideas = self._execute_agent_step("Шаг 1/3: Генерация идей", 'ideator', self.initial_context, ImprovementIdea)
        if not ideas: return False, ""
        
        idea_context = json.dumps([i.model_dump() for i in ideas], indent=2, ensure_ascii=False)
        idea_obj = self._execute_agent_step("Шаг 2/3: Фильтрация идей", 'filter', idea_context, ImprovementIdea)
        if not idea_obj: return False, ""
        self._report_progress(f"  Выбрана идея: '{idea_obj.title}' (Тип: {idea_obj.type})")
        if 'on_idea_approved' in self.hooks: self.hooks['on_idea_approved'](idea_obj)

        if idea_obj.type in ['REFACTORING', 'BUG_FIX', 'FEATURE']:
            is_pipeline_success = self._run_code_change_pipeline(idea_obj)
            return is_pipeline_success, idea_obj.title
        else:
            self._report_progress(f"Тип задачи '{idea_obj.type}' не требует изменения кода. Пропуск.")
            return True, idea_obj.title

    def _run_code_change_pipeline(self, idea_obj: ImprovementIdea) -> bool:
        """Пайплайн для задач, изменяющих код."""
        plan_obj = self._execute_agent_step("Шаг 3/3: Создание плана", 'planner', idea_obj.model_dump_json(), ImplementationPlan)
        if not plan_obj: return False
        if 'on_plan_approved' in self.hooks: self.hooks['on_plan_approved'](plan_obj)
        
        coder_task = (
            f"ИДЕЯ: {idea_obj.title} - {idea_obj.description}\n"
            f"ПЛАН: {plan_obj.description}\n\n"
            f"Выполни этот план, используя инструменты. Предпочитай `apply_patch`."
        )

        for attempt in range(self.MAX_REPAIR_ATTEMPTS):
            if self._is_cancelled(): return False
            self._report_progress(f"\n--- Попытка Разработки и Тестирования #{attempt + 1}/{self.MAX_REPAIR_ATTEMPTS} ---")

            coder_result = self.agents['coder'].execute(coder_task, on_activity=self.hooks.get('on_file_activity'))
            if coder_result['status'] != 'success':
                coder_task = f"Твоя предыдущая попытка провалилась. Ошибка: {coder_result['message']}. Проанализируй ошибку и попробуй еще раз, исправив свой подход."
                continue

            test_writer_task = f"Агент-кодер внес изменения: '{coder_result['message']}'. Напиши или обнови pytest тесты."
            test_writer_result = self.agents['test_writer'].execute(test_writer_task, on_activity=self.hooks.get('on_file_activity'))
            if test_writer_result['status'] != 'success':
                coder_task = f"Твои изменения работают, но агент-тестировщик не смог написать для них тесты. Ошибка: {test_writer_result['message']}. Возможно, код нетестируемый? Попробуй исправить."
                continue

            qa_task = "Кодер внес изменения, тестировщик написал тесты. Запусти тесты и вынеси вердикт."
            qa_result = self.agents['qa_agent'].execute(qa_task, on_activity=self.hooks.get('on_file_activity'))
            
            is_qa_passed = qa_result['status'] == 'success' and ('успех' in qa_result['message'].lower() or 'пройдены' in qa_result['message'].lower())
            if is_qa_passed:
                return True
            
            current_code_context = self._read_project_context()
            coder_task = (
                f"Твоя предыдущая попытка провалила проверку качества. Отчет от QA: '{qa_result['message']}'.\n\n"
                f"Вот АКТУАЛЬНОЕ состояние кода:\n{current_code_context}\n\n"
                f"ИСПРАВЬ ЭТУ ОШИБКУ."
            )
        
        self._report_progress(f"\n--- Не удалось исправить код за {self.MAX_REPAIR_ATTEMPTS} попытки. ---")
        return False