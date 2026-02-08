import asyncio
from datetime import datetime

from pydantic import BaseModel

from tabtrack.schemas import TimeSeriesModel


class SubscriptionEvent(BaseModel):
    device: str
    section: str
    value: float
    author: str
    updated_at: datetime


type SubscriptionKey = tuple[str, str]
type EventQueue = asyncio.Queue[SubscriptionEvent]


class ConnectionManager:
    def __init__(self):
        self.subscriptions: dict[SubscriptionKey, set[EventQueue]] = {}

    def subscribe(self, device: str = "*", section: str = "*"):
        queue: EventQueue = asyncio.Queue(maxsize=100)

        key = (device, section)

        if key not in self.subscriptions:
            self.subscriptions[key] = set()

        self.subscriptions[key].add(queue)

        return queue

    def unsubscribe(self, queue: EventQueue, device: str = "*", section: str = "*"):
        key = (device, section)

        self.subscriptions[key].discard(queue)

    async def broadcast_inner(
        self, event: SubscriptionEvent, device: str, section: str
    ):
        dead_queues: set[EventQueue] = set()

        key = (device, section)

        for queue in self.subscriptions.get(key, []):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                dead_queues.add(queue)

        for queue in dead_queues:
            self.subscriptions[key].discard(queue)

    async def broadcast_push(self, point: TimeSeriesModel):
        event = SubscriptionEvent(
            device=point.device,
            section=point.section,
            value=point.value,
            author=point.pushed_by,
            updated_at=datetime.now(),
        )

        for device_ in (event.device, "*"):
            for section_ in (event.section, "*"):
                await self.broadcast_inner(event, device_, section_)


manager = ConnectionManager()
