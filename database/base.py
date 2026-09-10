from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class UUIDType(TypeDecorator):
    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(value)
        return str(value) if value else None

    def process_result_value(self, value, dialect):
        if dialect.name == "postgresql":
            return str(value) if value else None
        return value


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )


class VersionMixin:
    version: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, index=True
    )


class IdentityMixin:
    uuid: Mapped[str] = mapped_column(
        UUIDType(),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )


class BaseModel(Base, TimestampMixin, SoftDeleteMixin, VersionMixin, IdentityMixin):
    __abstract__ = True

    def to_dict(self) -> dict[str, Any]:
        return {
            c.key: getattr(self, c.key)
            for c in self.__table__.columns
        }

    def to_json_safe(self) -> dict[str, Any]:
        result = {}
        for c in self.__table__.columns:
            val = getattr(self, c.key)
            if isinstance(val, datetime):
                val = val.isoformat()
            if isinstance(val, uuid.UUID):
                val = str(val)
            result[c.key] = val
        return result


db_json = JSON


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
