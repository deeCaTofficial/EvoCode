# src/evocode_core/__init__.py
# -*- coding: utf-8 -*-
"""
Пакет evocode_core.
"""

from .orchestrator import Orchestrator
# ИСПРАВЛЕНИЕ: Заменяем ToolAgent на BaseToolAgent, так как это основной класс для агентов с инструментами
from .agents import BaseAgent, BaseToolAgent
from .models import (
    ImprovementIdea,
    ImplementationPlan,
    CodeValidationResult,
    TestResult,
    TestValidationResult,
)
from .exceptions import (
    CoreError,
    APIKeyNotFoundError,
    ContentBlockedError,
)

# __all__ определяет публичный API пакета.
__all__ = [
    "Orchestrator",
    "BaseAgent",
    # ИСПРАВЛЕНИЕ: Заменяем ToolAgent на BaseToolAgent
    "BaseToolAgent",
    "ImprovementIdea",
    "ImplementationPlan",
    "CodeValidationResult",
    "TestResult",
    "TestValidationResult",
    "CoreError",
    "APIKeyNotFoundError",
    "ContentBlockedError",
]