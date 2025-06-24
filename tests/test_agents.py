
import pytest
import time
import logging
from unittest.mock import MagicMock, patch
from pathlib import Path

from src.evocode_core.agents import BaseToolAgent, CoreError, AgentExecutionResult, MAX_CORE_ERROR_RETRIES, INITIAL_BACKOFF_SECONDS
from src.evocode_core.client import GeminiClient, GeminiResponse
from src.evocode_core.tools import finish, ToolError

# Mock logger to capture logs
@pytest.fixture
def cap_log(caplog):
    caplog.set_level(logging.INFO)
    return caplog

# Mock GeminiClient
class MockGeminiClient(GeminiClient):
    def __init__(self, responses: list):
        self._responses = responses
        self._call_count = 0

    def start_tool_chat(self, system_prompt: str, tools: list):
        return MagicMock() # Mock chat session

    def send_message(self, chat_session: MagicMock, message: Any) -> GeminiResponse:
        if self._call_count < len(self._responses):
            response = self._responses[self._call_count]
            self._call_count += 1
            if isinstance(response, Exception):
                raise response
            return response
        return {"text": "Default response if no more mock responses"}

# Simple Test Agent inheriting from BaseToolAgent
class TestToolAgent(BaseToolAgent):
    def __init__(self, system_prompt: str, project_path: Path, client: GeminiClient):
        super().__init__(system_prompt, project_path, client)
        self.tool_dispatch_table['mock_tool'] = self._mock_tool_impl
        self.available_tools.append(MagicMock(name='mock_tool')) # Add a mock tool

    def _register_tools(self):
        super()._register_tools()
        # Tools are registered in __init__ for this test agent

    def _mock_tool_impl(self, arg: str) -> str:
        return f"Mock tool executed with: {arg}"

@pytest.fixture
def mock_project_path():
    return Path("/tmp/test_project")

@pytest.fixture
def mock_fs_tools():
    with patch('src.evocode_core.agents.FileSystemTools') as MockFSTools:
        mock_instance = MockFSTools.return_value
        yield mock_instance

@pytest.fixture(autouse=True)
def mock_time_sleep():
    with patch('time.sleep', return_value=None) as mock_sleep:
        yield mock_sleep

# --- Tests for CoreError Retry Logic ---

def test_agent_retries_on_core_error_and_succeeds(mock_project_path, mock_fs_tools, mock_time_sleep, cap_log):
    # Simulate CoreError twice, then success
    mock_responses = [
        CoreError("Simulated CoreError 1"),
        CoreError("Simulated CoreError 2"),
        {"function_call": {"name": "finish", "args": {"reason": "Success after retries"}}}
    ]
    mock_client = MockGeminiClient(mock_responses)
    agent = TestToolAgent("Test system prompt", mock_project_path, mock_client)

    result = agent.execute("Test context")

    assert result["status"] == "success"
    assert "Success after retries" in result["message"]
    assert mock_client._call_count == 3 # Initial call + 2 retries
    assert mock_time_sleep.call_count == 2 # Sleep called twice
    mock_time_sleep.assert_any_call(INITIAL_BACKOFF_SECONDS)
    mock_time_sleep.assert_any_call(INITIAL_BACKOFF_SECONDS * 2)
    assert f"CoreError in cycle of agent 'TestToolAgent' (attempt 1/{MAX_CORE_ERROR_RETRIES + 1}): Simulated CoreError 1" in cap_log.text
    assert f"CoreError in cycle of agent 'TestToolAgent' (attempt 2/{MAX_CORE_ERROR_RETRIES + 1}): Simulated CoreError 2" in cap_log.text
    assert "Повторная попытка через" in cap_log.text

def test_agent_fails_after_max_core_error_retries(mock_project_path, mock_fs_tools, mock_time_sleep, cap_log):
    # Simulate CoreError for all attempts
    mock_responses = [CoreError("Persistent CoreError")] * (MAX_CORE_ERROR_RETRIES + 1)
    mock_client = MockGeminiClient(mock_responses)
    agent = TestToolAgent("Test system prompt", mock_project_path, mock_client)

    result = agent.execute("Test context")

    assert result["status"] == "success"
    assert "Критическая ошибка: Persistent CoreError. Все попытки исчерпаны." in result["message"]
    assert mock_client._call_count == MAX_CORE_ERROR_RETRIES + 1
    assert mock_time_sleep.call_count == MAX_CORE_ERROR_RETRIES
    assert f"Все {MAX_CORE_ERROR_RETRIES + 1} попыток исчерпаны для CoreError в агенте 'TestToolAgent'. Завершение работы." in cap_log.text

def test_agent_no_retry_on_non_core_error(mock_project_path, mock_fs_tools, mock_time_sleep, cap_log):
    # Simulate a non-CoreError (e.g., generic Exception)
    mock_responses = [
        Exception("Non-CoreError that should not trigger retry")
    ]
    mock_client = MockGeminiClient(mock_responses)
    agent = TestToolAgent("Test system prompt", mock_project_path, mock_client)

    with pytest.raises(Exception, match="Non-CoreError that should not trigger retry"):
        agent.execute("Test context")

    assert mock_client._call_count == 1 # No retries
    assert mock_time_sleep.call_count == 0 # No sleep calls
    assert "CoreError" not in cap_log.text # Ensure CoreError specific logs are not present

def test_agent_succeeds_without_core_error(mock_project_path, mock_fs_tools, mock_time_sleep, cap_log):
    # Simulate direct success
    mock_responses = [
        {"function_call": {"name": "finish", "args": {"reason": "Direct success"}}}
    ]
    mock_client = MockGeminiClient(mock_responses)
    agent = TestToolAgent("Test system prompt", mock_project_path, mock_client)

    result = agent.execute("Test context")

    assert result["status"] == "success"
    assert "Direct success" in result["message"]
    assert mock_client._call_count == 1
    assert mock_time_sleep.call_count == 0
    assert "CoreError" not in cap_log.text

def test_agent_handles_tool_error_gracefully(mock_project_path, mock_fs_tools, cap_log):
    # Simulate a tool call that raises a ToolError
    mock_responses = [
        {"function_call": {"name": "mock_tool", "args": {"arg": "test"}}},
        {"function_response": {"name": "mock_tool", "response": {"result": "Ошибка выполнения инструмента: Mock Tool Error"}}},
        {"function_call": {"name": "finish", "args": {"reason": "Finished after tool error"}}}
    ]
    
    # Patch _execute_tool_call to simulate ToolError
    with patch.object(TestToolAgent, '_execute_tool_call', side_effect=[
        "Ошибка выполнения инструмента: Mock Tool Error", # First call to _execute_tool_call
        "Mock tool executed with: test" # Second call to _execute_tool_call (if it were to happen, but it won't in this flow)
    ]) as mock_execute_tool:
        mock_client = MockGeminiClient([
            {"function_call": {"name": "mock_tool", "args": {"arg": "test"}}},
            {"function_call": {"name": "finish", "args": {"reason": "Finished after tool error"}}}
        ])
        agent = TestToolAgent("Test system prompt", mock_project_path, mock_client)

        result = agent.execute("Test context")

        assert result["status"] == "success"
        assert "Finished after tool error" in result["message"]
        mock_execute_tool.assert_called_once_with({"name": "mock_tool", "args": {"arg": "test"}})
        assert "Ошибка при выполнении инструмента 'mock_tool': Mock Tool Error" in cap_log.text

def test_agent_handles_unknown_tool_call(mock_project_path, mock_fs_tools, cap_log):
    # Simulate agent trying to call an unknown tool
    mock_responses = [
        {"function_call": {"name": "unknown_tool", "args": {}}},
        {"function_call": {"name": "finish", "args": {"reason": "Finished after unknown tool"}}}
    ]
    mock_client = MockGeminiClient(mock_responses)
    agent = TestToolAgent("Test system prompt", mock_project_path, mock_client)

    result = agent.execute("Test context")

    assert result["status"] == "success"
    assert "Finished after unknown tool" in result["message"]
    assert "Ошибка: Агент попытался вызвать неизвестный или недоступный ему инструмент 'unknown_tool'." in cap_log.text

def test_agent_handles_max_tool_calls_exceeded(mock_project_path, mock_fs_tools, cap_log):
    # Simulate agent continuously calling a tool without finishing
    mock_responses = [{"function_call": {"name": "mock_tool", "args": {"arg": f"call_{i}"}}} for i in range(MAX_TOOL_CALLS + 1)]
    mock_client = MockGeminiClient(mock_responses)
    agent = TestToolAgent("Test system prompt", mock_project_path, mock_client)

    result = agent.execute("Test context")

    assert result["status"] == "failure"
    assert "Превышен лимит вызовов инструментов." in result["message"]
    assert mock_client._call_count == MAX_TOOL_CALLS # Should stop after MAX_TOOL_CALLS attempts

def test_agent_handles_text_instead_of_tool_call(mock_project_path, mock_fs_tools, cap_log):
    # Simulate agent returning text instead of a tool call
    mock_responses = [
        {"text": "This is unexpected text from the agent."}
    ]
    mock_client = MockGeminiClient(mock_responses)
    agent = TestToolAgent("Test system prompt", mock_project_path, mock_client)

    result = agent.execute("Test context")

    assert result["status"] == "failure"
    assert "Работа завершена. Причина: This is unexpected text from the agent." in result["message"]
    assert "Агент вернул текст вместо инструмента: This is unexpected text from the agent." in cap_log.text

def test_agent_handles_no_decision(mock_project_path, mock_fs_tools, cap_log):
    # Simulate agent returning neither text nor function call
    mock_responses = [
        {} # Empty response
    ]
    mock_client = MockGeminiClient(mock_responses)
    agent = TestToolAgent("Test system prompt", mock_project_path, mock_client)

    result = agent.execute("Test context")

    assert result["status"] == "failure"
    assert "Агент не смог принять решение (не вернул ни текст, ни инструмент)." in result["message"]
