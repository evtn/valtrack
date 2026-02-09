from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from valtrack.auth import APIKey, verify_api_key
from valtrack.database import get_db
from valtrack.models import PushRequest
from valtrack.query import get_time_point
from valtrack.schemas import TimeSeriesModel
from valtrack.sse_manager import manager

router = APIRouter()


@router.post("/push", status_code=204)
async def push_data(
    request: PushRequest,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(verify_api_key),
):
    device = request.device
    section = request.section

    if not api_key.can_write(device, section):
        raise HTTPException(
            status_code=403,
            detail=f"API key not authorized for writing to '{device}'/'{section}' key",
        )

    if not request.forcepush:
        point = await get_time_point(db, device, section)

        if point and point.value == request.value:
            return

    time_series_entry = TimeSeriesModel(
        device=device,
        section=section,
        timestamp=datetime.now(tz=UTC),
        value=request.value,
        pushed_by=api_key.key_id,
    )

    db.add(time_series_entry)
    await manager.broadcast_push(time_series_entry)
    await db.commit()

    return
