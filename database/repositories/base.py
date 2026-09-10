from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import ColumnExpressionArgument, Select, UnaryExpression, and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.base import BaseModel

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)


class PaginatedResult(Generic[ModelT]):
    def __init__(
        self,
        items: Sequence[ModelT],
        total: int,
        page: int,
        page_size: int,
    ):
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size
        self.total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 0
        self.has_previous = page > 1
        self.has_next = page < self.total_pages
        self.previous_page = page - 1 if self.has_previous else None
        self.next_page = page + 1 if self.has_next else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [item.to_json_safe() for item in self.items],
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
            "has_previous": self.has_previous,
            "has_next": self.has_next,
            "previous_page": self.previous_page,
            "next_page": self.next_page,
        }


class BaseRepository(Generic[ModelT]):
    def __init__(self, session: AsyncSession, model_class: type[ModelT]):
        self.session = session
        self.model_class = model_class

    async def get_by_uuid(self, uuid: str) -> ModelT | None:
        stmt = select(self.model_class).where(
            self.model_class.uuid == uuid,
            self.model_class.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_uuid_with_relations(
        self, uuid: str, relations: list[str]
    ) -> ModelT | None:
        q = select(self.model_class).options(
            *[joinedload(getattr(self.model_class, r)) for r in relations]
        ).where(
            self.model_class.uuid == uuid,
            self.model_class.is_deleted == False,
        )
        result = await self.session.execute(q)
        return result.unique().scalar_one_or_none()

    async def get_by_field(
        self, field: str, value: Any, unique: bool = True
    ) -> ModelT | Sequence[ModelT] | None:
        col = getattr(self.model_class, field, None)
        if col is None:
            raise ValueError(f"Field {field} does not exist on {self.model_class.__name__}")
        stmt = select(self.model_class).where(
            col == value, self.model_class.is_deleted == False
        )
        result = await self.session.execute(stmt)
        if unique:
            return result.scalar_one_or_none()
        return result.scalars().all()

    async def list_all(
        self,
        order_by: str | None = None,
        descending: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[ModelT]:
        stmt = select(self.model_class).where(
            self.model_class.is_deleted == False
        )
        if order_by:
            col = getattr(self.model_class, order_by, None)
            if col is not None:
                stmt = stmt.order_by(col.desc() if descending else col)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def paginate(
        self,
        page: int = 1,
        page_size: int = 20,
        order_by: str | None = "created_at",
        descending: bool = True,
        filters: list[ColumnExpressionArgument] | None = None,
        search_text: str | None = None,
        search_columns: list[str] | None = None,
    ) -> PaginatedResult[ModelT]:
        base_filter = [self.model_class.is_deleted == False]
        if filters:
            base_filter.extend(filters)

        search_clauses = []
        if search_text and search_columns:
            for col_name in search_columns:
                col = getattr(self.model_class, col_name, None)
                if col is not None:
                    search_clauses.append(col.ilike(f"%{search_text}%"))

        all_filters = list(base_filter)
        if search_clauses:
            all_filters.append(or_(*search_clauses))

        count_stmt = select(func.count()).select_from(self.model_class).where(
            *all_filters
        )
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = select(self.model_class).where(*all_filters)

        if order_by:
            col = getattr(self.model_class, order_by, None)
            if col is not None:
                stmt = stmt.order_by(col.desc() if descending else col)

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await self.session.execute(stmt)
        items = result.scalars().all()

        return PaginatedResult(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def create(self, **kwargs: Any) -> ModelT:
        instance = self.model_class(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def create_from_model(self, model: ModelT) -> ModelT:
        self.session.add(model)
        await self.session.flush()
        return model

    async def update(self, uuid: str, **kwargs: Any) -> ModelT | None:
        instance = await self.get_by_uuid(uuid)
        if instance is None:
            return None
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        instance.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return instance

    async def update_bulk(
        self, filters: list[ColumnExpressionArgument], **kwargs: Any
    ) -> int:
        kwargs["updated_at"] = datetime.now(timezone.utc)
        stmt = (
            update(self.model_class)
            .where(*filters, self.model_class.is_deleted == False)
            .values(**kwargs)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def soft_delete(self, uuid: str) -> bool:
        instance = await self.get_by_uuid(uuid)
        if instance is None:
            return False
        instance.is_deleted = True
        instance.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    async def hard_delete(self, uuid: str) -> bool:
        instance = await self.get_by_uuid(uuid)
        if instance is None:
            return False
        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def count(
        self, filters: list[ColumnExpressionArgument] | None = None
    ) -> int:
        base_filter = [self.model_class.is_deleted == False]
        if filters:
            base_filter.extend(filters)
        stmt = select(func.count()).select_from(self.model_class).where(*base_filter)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def exists(self, uuid: str) -> bool:
        stmt = select(self.model_class).where(
            self.model_class.uuid == uuid,
            self.model_class.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def bulk_create(self, instances: list[ModelT]) -> list[ModelT]:
        self.session.add_all(instances)
        await self.session.flush()
        return instances

    async def find_or_create(
        self, lookup: dict[str, Any], defaults: dict[str, Any] | None = None
    ) -> tuple[ModelT, bool]:
        stmt = select(self.model_class).where(
            *[getattr(self.model_class, k) == v for k, v in lookup.items()],
            self.model_class.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        instance = result.scalar_one_or_none()
        if instance:
            return instance, False

        create_data = {**lookup, **(defaults or {})}
        return await self.create(**create_data), True

    async def get_by_ids(self, uuids: list[str]) -> Sequence[ModelT]:
        stmt = select(self.model_class).where(
            self.model_class.uuid.in_(uuids),
            self.model_class.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_field(self, field: str, value: Any) -> int:
        col = getattr(self.model_class, field, None)
        if col is None:
            raise ValueError(f"Field {field} does not exist on {self.model_class.__name__}")
        stmt = select(func.count()).select_from(self.model_class).where(
            col == value, self.model_class.is_deleted == False
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
