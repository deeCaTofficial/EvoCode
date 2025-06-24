# src/evocode_core/models.py
# -*- coding: utf-8 -*-
"""
Определяет Pydantic-модели, которые служат в качестве "контрактов"
для обмена данными между AI-агентами в системе EvoCode.

Эти модели обеспечивают строгую типизацию и валидацию данных,
получаемых от LLM, что критически важно для стабильности всего конвейера.
"""
from __future__ import annotations
from typing import List, Optional, Literal

from pydantic import BaseModel, Field

# Тип для классификации идей по улучшению
ImprovementType = Literal['REFACTORING', 'BUG_FIX', 'FEATURE', 'TESTING', 'DOCUMENTATION', 'STYLE']

class ImprovementIdea(BaseModel):
    """
    Структура для описания одной конкретной идеи по улучшению кода.
    Генерируется Агентом 1 (Ideator).
    """
    id: int = Field(
        ...,
        description="Уникальный порядковый номер идеи в списке.",
        example=1
    )
    title: str = Field(
        ...,
        description="Краткий, емкий заголовок идеи (до 10 слов).",
        example="Рефакторинг функции calculate_statistics"
    )
    description: str = Field(
        ...,
        description="Подробное описание улучшения: что не так сейчас и почему предлагаемое изменение сделает код лучше.",
        example="Текущая функция превышает 50 строк и нарушает Принцип Единственной Ответственности. Ее следует разбить на три более мелкие функции: для загрузки данных, их обработки и сохранения результата."
    )
    priority: float = Field(
        ...,
        description="Приоритет идеи от 0.0 до 1.0, где 1.0 - самый высокий.",
        ge=0.0,
        le=1.0,
        example=0.9
    )
    type: ImprovementType = Field(
        ...,
        description="Тип улучшения из предопределенного списка: 'REFACTORING', 'BUG_FIX', 'FEATURE', 'TESTING', 'DOCUMENTATION', 'STYLE'.",
        example="REFACTORING"
    )


class ImplementationPlan(BaseModel):
    """
    Структура для описания пошагового плана внедрения идеи.
    Генерируется Агентом 3 (Planner).
    """
    description: str = Field(
        ...,
        description="Детальное, пошаговое описание того, как именно нужно изменить код для реализации идеи. Должно быть понятно другому программисту или AI. Формат: однострочный текст, шаги разделены через ' -> '.",
        example="1. Открыть файл 'data_processor.py'. -> 2. Найти функцию 'calculate_statistics'. -> 3. Создать новую функцию 'load_data_from_db(query: str) -> pd.DataFrame'. -> ..."
    )
    code_diff: Optional[str] = Field(
        None,
        description="(Опционально) Предлагаемые изменения в формате diff/patch для автоматического применения.",
        example="--- a/data_processor.py\n+++ b/data_processor.py\n@@ -10,5 +10,7 @@\n- old_line()\n+ new_line()"
    )


class ValidationResult(BaseModel):
    """
    Базовая модель для всех результатов валидации.
    Определяет общий формат ответа для проверяющих агентов.
    """
    is_ok: bool = Field(
        ...,
        description="Результат проверки: True, если проверка пройдена успешно, иначе False."
    )
    feedback: Optional[str] = Field(
        None,
        description="Конструктивная обратная связь в случае неудачи (is_ok=False). Должна объяснять, что именно нужно исправить.",
        example="План не учитывает случай, когда входные данные пусты. Необходимо добавить проверку на пустой DataFrame."
    )


class PlanValidationResult(ValidationResult):
    """Результат проверки Плана внедрения от Агента 4 (Plan Validator)."""
    pass


class CodeValidationResult(ValidationResult):
    """Результат проверки качества кода от Агента 6 (Code Validator)."""
    pass


class TestValidationResult(ValidationResult):
    """Результат проверки качества тестов от Агента 8 (Test Validator)."""
    pass


class TestResult(BaseModel):
    """
    Структура, содержащая сгенерированные тесты и результат их (симулированного) прогона.
    Генерируется Агентом 7 (Tester).
    """
    is_passing: bool = Field(
        ...,
        description="Проходят ли сгенерированные тесты: True или False."
    )
    details: str = Field(
        ...,
        description="Полный код сгенерированных тестов с использованием pytest.",
        example="import pytest\nfrom my_module import new_function\n\ndef test_new_function():\n    assert new_function(2) == 4"
    )