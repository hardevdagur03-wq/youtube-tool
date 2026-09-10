from __future__ import annotations

import contextlib
from typing import Any


class MockResult:
    def __init__(self, rows: list[dict[str, Any]] | None = None):
        self._rows = rows or []
        self._index = 0

    def scalars(self) -> MockResult:
        return self

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def all(self) -> list[dict[str, Any]]:
        return list(self._rows)

    def one(self) -> dict[str, Any]:
        if len(self._rows) == 0:
            raise Exception("No rows found for one()")
        if len(self._rows) > 1:
            raise Exception("Multiple rows found for one()")
        return self._rows[0]

    def one_or_none(self) -> dict[str, Any] | None:
        if len(self._rows) == 0:
            return None
        return self._rows[0]

    def __iter__(self):
        return iter(self._rows)

    def __len__(self) -> int:
        return len(self._rows)


class MockDatabaseSession:
    def __init__(self):
        self._executed_queries: list[str] = []
        self._added_instances: list[Any] = []
        self._deleted_instances: list[Any] = []
        self._result_sets: dict[str, list[dict[str, Any]]] = {}
        self._committed: bool = False
        self._rolled_back: bool = False
        self._closed: bool = False
        self._flushed: bool = False
        self._refreshed_instances: list[Any] = []

    async def __aenter__(self) -> MockDatabaseSession:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    def execute(self, query: Any) -> MockResult:
        query_str = str(query) if not isinstance(query, str) else query
        self._executed_queries.append(query_str)
        rows = self._result_sets.get(query_str, [])
        return MockResult(rows)

    def fetch_all(self) -> list[dict[str, Any]]:
        return [r for r in self._result_sets.values() for r in r]

    def fetch_one(self) -> dict[str, Any] | None:
        for rows in self._result_sets.values():
            if rows:
                return rows[0]
        return None

    def commit(self) -> None:
        self._committed = True

    def rollback(self) -> None:
        self._rolled_back = True

    def close(self) -> None:
        self._closed = True

    def add(self, instance: Any) -> None:
        self._added_instances.append(instance)

    def add_all(self, instances: list[Any]) -> None:
        self._added_instances.extend(instances)

    def delete(self, instance: Any) -> None:
        self._deleted_instances.append(instance)

    def flush(self) -> None:
        self._flushed = True

    def refresh(self, instance: Any) -> None:
        self._refreshed_instances.append(instance)

    def set_results(self, query: str, rows: list[dict[str, Any]]) -> None:
        self._result_sets[query] = list(rows)

    def get_executed_queries(self) -> list[str]:
        return list(self._executed_queries)

    def get_added_instances(self) -> list[Any]:
        return list(self._added_instances)

    def get_deleted_instances(self) -> list[Any]:
        return list(self._deleted_instances)

    def was_committed(self) -> bool:
        return self._committed

    def was_rolled_back(self) -> bool:
        return self._rolled_back

    def was_closed(self) -> bool:
        return self._closed

    def was_flushed(self) -> bool:
        return self._flushed

    def reset(self) -> None:
        self._executed_queries.clear()
        self._added_instances.clear()
        self._deleted_instances.clear()
        self._result_sets.clear()
        self._committed = False
        self._rolled_back = False
        self._closed = False
        self._flushed = False
        self._refreshed_instances.clear()
