# src/evocode_core/agents.py
# -*- coding: utf-8 -*-
"""
Определяет иерархию AI-агентов и фабрику для их создания.
Реализует надежный цикл "Рассуждай-Действуй" (ReAct).
"""
import logging
import json
import re
from abc import ABC, abstractmethod
from typing import Any, List, Callable, Dict, TypedDict, Literal, Type
from pathlib import Path

from pydantic import ValidationError, BaseModel, parse_obj_as

from .client import GeminiClient, GeminiResponse
from .tools import FileSystemTools, finish, ToolError
from .exceptions import CoreError

log = logging.getLogger(__name__)

# --- Константы ---
MAX_TOOL_CALLS = 10 # Максимальное количество последовательных вызовов инструментов

# --- Типизация ---
AgentStatus = Literal['success', 'failure']

class AgentExecutionResult(TypedDict):
    """Структурированный результат работы агента."""
    status: AgentStatus
    message: Any # Может быть строкой или Pydantic моделью

# --- Базовые классы ---

class BaseAgent(ABC):
    """Абстрактный базовый класс для всех AI-агентов."""
    def __init__(self, system_prompt: str, client: GeminiClient):
        if not system_prompt or not isinstance(system_prompt, str):
            raise ValueError("System prompt must be a non-empty string.")
        self.system_prompt = system_prompt
        self.client = client

    @abstractmethod
    def execute(self, context: Any, **kwargs) -> AgentExecutionResult:
        """Основной метод, выполняющий логику агента."""
        pass

class BaseToolAgent(BaseAgent):
    """
    Базовый класс для агентов, использующих инструменты.
    Реализует полноценный цикл "Рассуждай-Действуй" (ReAct).
    """
    def __init__(self, system_prompt: str, project_path: Path, client: GeminiClient):
        super().__init__(system_prompt, client)
        self.project_path = project_path
        self.fs_tools = FileSystemTools(project_root=self.project_path)
        self.tool_dispatch_table: Dict[str, Callable] = {}
        self.available_tools: List[Callable] = []
        self._register_tools()

    @abstractmethod
    def _register_tools(self):
        """Дочерние классы должны реализовать этот метод для регистрации своих инструментов."""
        self.tool_dispatch_table['finish'] = finish

    def _execute_tool_call(self, function_call: Any) -> str:
        """Находит и выполняет инструмент из диспетчерского стола."""
        function_name = function_call.name
        args = {key: value for key, value in (function_call.args or {}).items()}
        
        log.info(f"Агент '{self.__class__.__name__}' запросил вызов: {function_name}({args})")

        func_to_call = self.tool_dispatch_table.get(function_name)
        if not func_to_call:
            error_msg = f"Ошибка: Агент попытался вызвать неизвестный или недоступный ему инструмент '{function_name}'."
            log.error(error_msg)
            return error_msg

        try:
            return func_to_call(**args)
        except (ToolError, TypeError) as e:
            log.error(f"Ошибка при выполнении инструмента '{function_name}': {e}")
            return f"Ошибка выполнения инструмента: {e}"

    def execute(self, context: str, **kwargs) -> AgentExecutionResult:
        on_activity_hook = kwargs.get('on_activity')
        self.fs_tools.on_activity = on_activity_hook

        try:
            chat_session = self.client.start_tool_chat(self.system_prompt, self.available_tools + [finish])
            response = self.client.send_message(chat_session, context)

            for i in range(MAX_TOOL_CALLS):
                if function_call := response.get("function_call"):
                    if function_call.name == 'finish':
                        reason = (function_call.args or {}).get('reason', 'не указана')
                        log.info(f"Агент завершил работу. Причина: {reason}")
                        return {"status": "success", "message": f"Работа завершена. Причина: {reason}"}

                    tool_response = self._execute_tool_call(function_call)
                    response_data = [{"function_response": {"name": function_call.name, "response": {"result": tool_response}}}]
                    response = self.client.send_message(chat_session, response_data)
                
                elif text := response.get("text"):
                    log.warning(f"Агент вернул текст вместо инструмента: {text}")
                    return {"status": "failure", "message": f"Агент завершил работу с текстом вместо вызова `finish`: {text}"}
                
                else:
                    return {"status": "failure", "message": "Агент не смог принять решение (не вернул ни текст, ни инструмент)."}

            return {"status": "failure", "message": "Превышен лимит вызовов инструментов."}
        
        except CoreError as e:
            log.exception(f"Критическая ошибка API в цикле агента '{self.__class__.__name__}': {e}")
            return {"status": "failure", "message": f"Критическая ошибка API: {e}"}
        finally:
            self.fs_tools.on_activity = None


# --- Конкретные реализации агентов ---

class TextAgent(BaseAgent):
    """Простой агент, который генерирует текст (обычно JSON) и парсит его."""
    
    def _parse_json_response(self, response_str: str, model: Type[BaseModel]) -> Any:
        """Надежно парсит JSON из ответа AI, очищая и исправляя частые ошибки."""
        if not response_str:
            raise CoreError("AI вернул пустой ответ.")
            
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_str, re.DOTALL)
        cleaned_str = match.group(1).strip() if match else response_str.strip()
        
        try:
            data = json.loads(cleaned_str)
        except json.JSONDecodeError as e:
            log.warning(f"Первая попытка парсинга JSON провалилась ({e}). Пробуем исправить строку...")
            try:
                repaired_str = cleaned_str.replace('\n', '\\n').replace('`', "'")
                data = json.loads(repaired_str)
                log.info("Строка JSON успешно исправлена и распарсена.")
            except json.JSONDecodeError as e2:
                raise CoreError(f"Ошибка парсинга JSON: {e2}. Ответ AI: {cleaned_str[:300]}...") from e2
        
        try:
            return parse_obj_as(List[model], data) if isinstance(data, list) else model.model_validate(data)
        except ValidationError as e_pydantic:
            raise CoreError(f"Ошибка валидации Pydantic: {e_pydantic}. Данные: {str(data)[:300]}...") from e_pydantic

    def execute(self, context: str, **kwargs) -> AgentExecutionResult:
        expected_model = kwargs.get('expected_model')
        try:
            raw_text = self.client.generate_text(self.system_prompt, context)
            if "Ошибка API" in raw_text:
                 return {"status": "failure", "message": raw_text}

            if not expected_model:
                return {"status": "success", "message": raw_text}
            
            parsed_data = self._parse_json_response(raw_text, expected_model)
            return {"status": "success", "message": parsed_data}
        except CoreError as e:
            log.error(f"TextAgent столкнулся с ошибкой: {e}")
            return {"status": "failure", "message": str(e)}

class ReadOnlyToolAgent(BaseToolAgent):
    """Агент с инструментами только для чтения."""
    def _register_tools(self):
        super()._register_tools()
        read_tools = [self.fs_tools.list_files, self.fs_tools.read_file]
        self.available_tools.extend(read_tools)
        self.tool_dispatch_table.update({
            'list_files': self.fs_tools.list_files,
            'read_file': self.fs_tools.read_file,
        })

class QAAgent(ReadOnlyToolAgent):
    """Агент-QA, который может читать файлы и запускать тесты."""
    def _register_tools(self):
        super()._register_tools()
        self.available_tools.append(self.fs_tools.run_tests)
        self.tool_dispatch_table['run_tests'] = self.fs_tools.run_tests

class ReadWriteToolAgent(ReadOnlyToolAgent):
    """Агент с полным доступом к файловой системе (чтение и запись)."""
    def _register_tools(self):
        super()._register_tools()
        write_tools = [self.fs_tools.write_file, self.fs_tools.apply_patch]
        self.available_tools.extend(write_tools)
        self.tool_dispatch_table.update({
            'write_file': self.fs_tools.write_file,
            'apply_patch': self.fs_tools.apply_patch,
        })

# --- Фабрика Агентов ---

def create_agent(
    agent_name: str,
    system_prompt: str,
    client: GeminiClient,
    project_path: Path
) -> BaseAgent:
    """Фабричная функция для создания экземпляров агентов по их имени."""
    agent_map: Dict[str, type] = {
        'ideator': TextAgent,
        'filter': TextAgent,
        'planner': TextAgent,
        'commit_message_generator': TextAgent,
        'coder': ReadWriteToolAgent,
        'test_writer': ReadWriteToolAgent,
        'qa_agent': QAAgent,
    }
    agent_class = agent_map.get(agent_name)

    if not agent_class:
        raise ValueError(f"Неизвестное имя агента: {agent_name}")

    if issubclass(agent_class, TextAgent):
        return agent_class(system_prompt, client)
    elif issubclass(agent_class, BaseToolAgent):
        return agent_class(system_prompt, project_path, client)
    else:
        raise TypeError(f"Неизвестный базовый тип для агента '{agent_name}'")