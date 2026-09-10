"""Base classes for Domain-Driven Design building blocks.

This module contains no imports from any framework.
All domain entities inherit from these base classes.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class DomainException(Exception, ABC):
    """Base exception for all domain errors."""

    @property
    @abstractmethod
    def error_code(self) -> str:
        ...

    @property
    def message(self) -> str:
        return str(self.args[0]) if self.args else ""


@dataclass
class ValueObject:
    """Base class for value objects.

    Value objects are immutable and compared by their attributes.
    """

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))


class Entity:
    """Base class for entities.

    Entities have identity and are compared by their identity, not attributes.
    Subclasses must set self.id in __init__ or provide an id field.
    """

    def __init__(self, id: str | None = None) -> None:
        self.id = id or uuid.uuid4().hex
        self._domain_events: list[DomainEvent] = []

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


class AggregateRoot(Entity):
    """Base class for aggregate roots.

    Aggregate roots manage domain events.
    """

    def record_event(self, event: Any) -> None:
        self._domain_events.append(event)

    def clear_events(self) -> list[Any]:
        events = list(self._domain_events)
        self._domain_events.clear()
        return events


class DomainService(ABC):
    """Marker interface for domain services."""


class Repository(ABC):
    """Marker interface for repositories."""


class UnitOfWork(ABC):
    """Interface for Unit of Work pattern."""

    @abstractmethod
    async def commit(self) -> None:
        ...

    @abstractmethod
    async def rollback(self) -> None:
        ...

    @abstractmethod
    async def __aenter__(self) -> UnitOfWork:
        ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        ...


class Specification(ABC):
    """Specification pattern for business rules."""

    @abstractmethod
    def is_satisfied_by(self, candidate: Any) -> bool:
        ...


class Guard:
    """Static guard clause utilities."""

    @staticmethod
    def against_empty(value: str, name: str = "value") -> None:
        if not value or not value.strip():
            raise DomainException(f"{name} cannot be empty")

    @staticmethod
    def against_null(value: Any, name: str = "value") -> None:
        if value is None:
            raise DomainException(f"{name} cannot be null")

    @staticmethod
    def against_invalid_id(value: str, name: str = "id") -> None:
        if not value or len(value) < 4:
            raise DomainException(f"{name} is not a valid identifier")
