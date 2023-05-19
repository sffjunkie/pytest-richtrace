from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable
from uuid import uuid1

from .item import ItemId

EventId = str
EventName = str
EventSource = str


@dataclass
class Event:
    id: EventId = ""
    source: EventSource = ""
    name: EventName = ""
    item_id: ItemId | None = ""
    time: datetime | None = None
    payload: Any | None = None

    def __init__(self, event_info: dict[str, Any] | None = None):
        if event_info is None:
            return
        self.id = event_info.get("id", "")
        self.source = event_info.get("source", "")
        self.time = event_info.get("time", None)
        self.name = event_info.get("name", "")
        self.item_id = event_info.get("item_id", None)
        self.payload = event_info.get("payload", None)

    def __rich_repr__(self):
        yield "id", self.id
        yield "source", self.source
        yield "name", self.name
        if self.item_id is not None:
            yield "item_id", self.item_id
        if self.time is not None:
            yield "time", self.time
        if self.payload is not None:
            yield "payload", self.payload


EventCallback = Callable[[Event], None]


@dataclass
class SubscriptionInfo:
    source: EventSource
    func: EventCallback


IdGenerator = Callable[[], str]
DatetimeGenerator = Callable[[], datetime]


def CLOCK() -> datetime:
    return datetime.now()


def EVENT_ID_GENERATOR() -> str:
    return str(uuid1())


def SOURCE_ID_GENERATOR() -> str:
    return str(uuid1())


class EventBus:
    def __init__(
        self,
        event_id_generator: IdGenerator = EVENT_ID_GENERATOR,
        clock: DatetimeGenerator = CLOCK,
    ) -> None:
        self.events: dict[EventId, Event] = {}
        self.subscriptions: list[SubscriptionInfo] = []
        self._event_id_generator = event_id_generator
        self._clock = clock

    def publish(
        self,
        event: Event,
    ) -> EventId:
        event_id = str(self._event_id_generator())
        event_time = self._clock()
        new_event = Event(
            {
                "id": event_id,
                "source": event.source,
                "time": event_time,
                "name": event.name,
                "item_id": event.item_id,
                "payload": event.payload,
            }
        )

        self.events[event_id] = new_event
        self._notify(new_event)
        return event_id

    def get_with_id(self, event_id: EventId) -> Event | None:
        return self.events.get(event_id, None)

    def get_from_source(self, source: EventSource) -> list[Event]:
        return [item for item in self.events.values() if item.source == source]

    def subscribe(self, source: EventSource, func: EventCallback) -> None:
        subscription = SubscriptionInfo(source, func)
        self.subscriptions.append(subscription)

    def _notify(self, event: Event):
        for subscription in self.subscriptions:
            if subscription.source != event.source:
                subscription.func(event)


class EventPublisher:
    def __init__(
        self,
        source_id: EventSource,
        event_bus: EventBus,
    ):
        self.event_bus = event_bus
        self.source_id = source_id

    def publish(
        self,
        name: EventName,
        item_id: ItemId | None = None,
        payload: Any | None = None,
    ) -> EventId:
        ev = Event(
            {
                "source": self.source_id,
                "name": name,
                "item_id": item_id,
                "payload": payload,
            }
        )
        return self.event_bus.publish(ev)
