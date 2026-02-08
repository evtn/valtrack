import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from tabtrack.auth import APIKey, verify_api_key
from tabtrack.sse_manager import SubscriptionEvent, manager

router = APIRouter()


@router.get("/sse", response_model=list[SubscriptionEvent])
async def subscribe(
    request: Request,
    device: str = "*",
    section: str = "*",
    apikey: APIKey = Depends(verify_api_key),
):
    queue = manager.subscribe(device, section)

    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    if apikey.can_read(event.device, event.section):
                        yield {"data": event.model_dump_json()}
                except asyncio.TimeoutError:
                    continue
        finally:
            manager.unsubscribe(queue, device, section)

    return EventSourceResponse(
        event_generator(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream",
        },
    )
