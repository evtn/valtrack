from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from tabtrack.auth import APIKey, verify_api_key
from tabtrack.database import get_db
from tabtrack.models import PushRequest
from tabtrack.schemas import TimeSeriesModel
from tabtrack.service.query import get_time_point
from tabtrack.sse_manager import manager

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

    point = await get_time_point(db, device, section)

    if point and point.value == request.value:
        return

    time_series_entry = TimeSeriesModel(
        device=device,
        section=section,
        timestamp=datetime.now(timezone.utc),
        value=request.value,
        pushed_by=api_key.key_id,
    )

    db.add(time_series_entry)
    await manager.broadcast_push(time_series_entry)
    await db.commit()

    return
