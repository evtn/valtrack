from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tabtrack.auth import APIKey
from tabtrack.schemas import TimeSeriesModel


async def get_time_points(
    db: AsyncSession,
    api_key: APIKey,
    is_distinct: bool = True,
):
    # Get latest value for each (device, section) using DISTINCT ON
    # Ordered by timestamp DESC so first row per group is the latest
    # This leverages TimescaleDB's time-based chunk pruning efficiently

    stmt = select(TimeSeriesModel)

    device_filter = api_key.get_device_filter()
    if device_filter is not None:
        stmt = stmt.where(TimeSeriesModel.device.in_(device_filter))

    section_filter = api_key.get_section_filter()
    if section_filter is not None:
        stmt = stmt.where(TimeSeriesModel.section.in_(section_filter))

    if is_distinct:
        stmt = stmt.distinct(TimeSeriesModel.device, TimeSeriesModel.section)

    stmt = stmt.order_by(
        TimeSeriesModel.device,
        TimeSeriesModel.section,
        TimeSeriesModel.timestamp.desc(),
    )

    for point in (await db.execute(stmt)).scalars().all():
        # just in case
        if not api_key.can_read(point.device, point.section):
            continue

        yield point
