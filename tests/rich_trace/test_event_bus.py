from datetime import datetime

from pytest_richtrace.event import Event, EventBus


def test_event_list_new():
    eb = EventBus()

    assert len(eb.events) == 0


def event_id_generator():
    return "always_the_same"


def clock():
    return datetime(2000, 1, 1, 0, 0, 0)


def test_event_bus_publish_id():
    eb = EventBus(event_id_generator=event_id_generator)

    ev = Event()
    ev.source = "src"
    ev.name = "class"
    ev.item_id = "here"

    assert eb.publish(ev) == "always_the_same"


def test_event_bus_publish_time():
    eb = EventBus(event_id_generator=event_id_generator, clock=clock)

    ev = Event()
    ev.source = "src"
    ev.name = "class"
    ev.item_id = "here"

    eb.publish(ev)

    event = eb.get_with_id("always_the_same")
    assert event.time == datetime(2000, 1, 1, 0, 0, 0)


def test_event_bus_with_id_existing_event():
    eb = EventBus(event_id_generator=event_id_generator)

    ev = Event()
    ev.source = "src"
    ev.name = "class"
    ev.item_id = "here"

    eb.publish(ev)

    event = eb.get_with_id("always_the_same")

    assert event.source == "src"


def test_event_bus_subscribe():
    def call_me():
        return "called"

    eb = EventBus()
    eb.subscribe(source="src", func=call_me)

    assert len(eb.subscriptions) == 1


def test_event_bus_notify():
    def call_me():
        return "called"

    eb = EventBus()
    eb.subscribe(source="src", func=call_me)
