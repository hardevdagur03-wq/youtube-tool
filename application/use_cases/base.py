"""Base classes for use cases (application services).

Use cases orchestrate domain objects to fulfill user goals.
They depend on repository interfaces and domain services.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

TCommand = TypeVar("TCommand")
TResult = TypeVar("TResult")


@dataclass
class Command(ABC):
    """A command represents an intent to change state."""

    request_id: str = ""


@dataclass
class Query(ABC):
    """A query represents an intent to read data."""

    request_id: str = ""


@dataclass
class Result:
    """Base result type for use case execution."""
    success: bool = True
    data: Any = None
    error: str = ""
    error_code: str = ""


@dataclass
class UseCase(ABC, Generic[TCommand, TResult]):
    """A single unit of business logic."""

    @abstractmethod
    async def execute(self, command: TCommand) -> TResult:
        ...


@dataclass
class QueryHandler(ABC, Generic[TCommand, TResult]):
    @abstractmethod
    async def handle(self, query: TCommand) -> TResult:
        ...
