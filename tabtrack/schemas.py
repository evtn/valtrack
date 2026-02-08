from datetime import datetime
from typing import Literal

from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Permissions:
    READ = 1
    WRITE = 2
    HISTORY = 4
    ADMIN = 8


type Wildcard = Literal["*"]


class APIKeySchema(Base):
    __tablename__ = "api_keys"

    key_id: Mapped[str] = mapped_column(primary_key=True)
    key_hash: Mapped[str] = mapped_column(unique=True, nullable=False)
    devices: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    sections: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    permissions: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[int] = mapped_column(nullable=False)

    @property
    def can_read(self) -> bool:
        return bool(self.permissions & Permissions.READ)

    @property
    def can_write(self) -> bool:
        return bool(self.permissions & Permissions.WRITE)

    @property
    def can_read_history(self) -> bool:
        return bool(self.permissions & Permissions.HISTORY)

    @property
    def device_set(self) -> Wildcard | set[str]:
        if "*" in self.devices:
            return "*"

        return set(self.devices)

    @property
    def section_set(self) -> Wildcard | set[str]:
        if "*" in self.sections:
            return "*"

        return set(self.sections)


class TimeSeriesModel(Base):
    __tablename__ = "time_series"

    device: Mapped[str] = mapped_column(String(255), primary_key=True)
    section: Mapped[str] = mapped_column(String(255), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    pushed_by: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        # Index for fast lookups by device/section when querying
        {"schema": "public"},
    )
