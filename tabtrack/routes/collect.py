from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from tabtrack.auth import APIKey, verify_api_key
from tabtrack.database import get_db
from tabtrack.schemas import TimeSeriesModel
from tabtrack.service.query import get_time_points

router = APIRouter(prefix="/items")


class Value(BaseModel):
    updated_at: datetime
    value: float
    author: str

    @staticmethod
    def from_point(point: TimeSeriesModel):
        return Value(
            updated_at=point.timestamp,
            value=point.value,
            author=point.pushed_by,
        )


type Sections = dict[str, Value]

type CollectionType = Literal["section", "device"]


class Collection[CollectionType](BaseModel):
    key: str
    type: CollectionType
    values: Sections = Field(default_factory=dict)

    def get_point_key(self, point: TimeSeriesModel):
        if self.type == "section":
            return point.device
        return point.section

    def add_point(self, point: TimeSeriesModel):
        point_key = self.get_point_key(point)

        self.values[point_key] = Value.from_point(point)


class DeviceState(Collection[Literal["device"]]):
    type: Literal["device"] = "device"


class SectionState(Collection[Literal["section"]]):
    type: Literal["section"] = "section"


class SystemState(BaseModel):
    devices: dict[str, DeviceState] = Field(default_factory=dict)

    def add_point(self, point: TimeSeriesModel):
        device = point.device

        if device not in self.devices:
            self.devices[device] = DeviceState(key=device)

        self.devices[device].add_point(point)


class CollectResponse(BaseModel):
    values: dict[str, Sections] = Field(default_factory=dict)

    def add_point(self, point: TimeSeriesModel):
        device = point.device

        if device not in self.values:
            self.values[device] = {}

        device_data = self.values[device]

        section = point.section

        device_data[section] = Value.from_point(point)


@router.get("/")
async def collect_data(
    db: AsyncSession = Depends(get_db),
    scopes: APIKey = Depends(verify_api_key),
) -> SystemState:
    collection = SystemState()

    async for point in get_time_points(db, scopes):
        collection.add_point(point)

    return collection


@router.get("/history")
async def get_history(
    device: str,
    section: str,
    db: AsyncSession = Depends(get_db),
    scopes: APIKey = Depends(verify_api_key),
) -> list[Value]:
    if not scopes.can_read_history(device, section):
        raise HTTPException(403, detail=f"cannot read history of {device}/{section}")

    scopes = scopes.one_device(device).one_section(section)

    values: list[Value] = []

    async for point in get_time_points(
        db,
        scopes,
        is_distinct=False,
    ):
        values.append(Value.from_point(point))

    return values


@router.get("/device/{device}")
async def get_device(
    device: str,
    db: AsyncSession = Depends(get_db),
    scopes: APIKey = Depends(verify_api_key),
) -> DeviceState:
    scopes = scopes.one_device(device)

    state = DeviceState(key=device)

    async for point in get_time_points(db, scopes):
        if device != point.device:
            continue  # just in case

        state.add_point(point)

    return state


@router.get("/section/{section}")
async def get_section(
    section: str,
    db: AsyncSession = Depends(get_db),
    scopes: APIKey = Depends(verify_api_key),
) -> SectionState:
    scopes = scopes.one_section(section)

    state = SectionState(key=section)

    async for point in get_time_points(db, scopes):
        if section != point.section:
            continue  # just in case

        state.add_point(point)

    return state
