from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.schemas.orchestration import DiscoveryRunStreamEvent

logger = logging.getLogger(__name__)


class DiscoveryRunEventManager:
    """In-memory pub/sub broker distributing real-time SSE events for discovery runs."""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[DiscoveryRunStreamEvent]]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, run_id: str) -> asyncio.Queue[DiscoveryRunStreamEvent]:
        """Subscribes an event listener queue for the specified discovery run."""
        queue: asyncio.Queue[DiscoveryRunStreamEvent] = asyncio.Queue(maxsize=100)
        async with self._lock:
            if run_id not in self._subscribers:
                self._subscribers[run_id] = set()
            self._subscribers[run_id].add(queue)
        return queue

    async def unsubscribe(self, run_id: str, queue: asyncio.Queue[DiscoveryRunStreamEvent]) -> None:
        """Unsubscribes a listener queue when an SSE client disconnects."""
        async with self._lock:
            if run_id in self._subscribers:
                self._subscribers[run_id].discard(queue)
                if not self._subscribers[run_id]:
                    del self._subscribers[run_id]

    async def broadcast(self, run_id: str, event: DiscoveryRunStreamEvent) -> None:
        """Publishes an event to all active listener queues for the run."""
        async with self._lock:
            queues = list(self._subscribers.get(run_id, []))

        for q in queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Listener queue for run %s is full; dropping event", run_id)


discovery_event_manager = DiscoveryRunEventManager()
