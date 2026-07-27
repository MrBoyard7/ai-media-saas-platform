"""
Dialect-portable column types.

Production runs on PostgreSQL and should get native `UUID` and `JSONB`
columns (indexing, `?`/`@>` operators, compact storage). The test suite
runs against an in-memory SQLite database for speed and zero external
dependencies, and SQLite has no native UUID or JSONB type. `GUID` and
`PortableJSON` pick the right implementation per-dialect at column-compile
time, so the exact same model definitions work unmodified against both.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import CHAR, JSON, Enum, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID


class GUID(TypeDecorator):
    """Platform-independent UUID type.

    Uses PostgreSQL's native UUID type when available, otherwise stores as
    a stringified 32-character hex CHAR (SQLite, used only in tests).
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(value)
        return value.hex

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(value)
        return value


def PortableJSON():
    """JSON column that becomes JSONB on PostgreSQL and plain JSON elsewhere."""
    return JSON().with_variant(JSONB(), "postgresql")


def StrEnum(enum_cls: type[enum.Enum], *, name: str) -> Enum:
    """`sqlalchemy.Enum` configured to persist by `.value`, not `.name`.

    All of this platform's enums subclass `str` (e.g.
    `class JobStatus(str, enum.Enum)`) specifically so that FastAPI/Pydantic
    serialize them as their lowercase `.value` (`"succeeded"`) in API
    responses. Left at its default, `sqlalchemy.Enum` persists the
    member's `.name` instead (`"SUCCEEDED"`), which both looks wrong in
    ad-hoc SQL and -- critically -- does not match the lowercase labels the
    Alembic migration defines for the corresponding native PostgreSQL enum
    type, causing every insert to fail in production. `values_callable`
    fixes the mismatch at the source so every model just calls
    `StrEnum(MyEnum, name="my_enum")` instead of repeating this argument.
    """
    return Enum(enum_cls, name=name, values_callable=lambda obj: [member.value for member in obj])
