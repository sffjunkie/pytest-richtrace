import logging
import platform
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Any

import _pytest
import pluggy  # type: ignore
import pytest
import rich.console
from _pytest.main import Session

from . import events
from .collection_observer import CollectionObserver
from .console import print_separator
from .event import SOURCE_ID_GENERATOR, EventBus, EventPublisher
from .item import ItemId
from .results import TestRunResults
from .rich_reporter import RichReporter
from .test_execution_observer import TestExecutionObserver


class PytestRichTrace:
    def __init__(
        self,
        config: pytest.Config,
        source_id_generator=SOURCE_ID_GENERATOR,
    ):
        logging.basicConfig(level=logging.INFO)

        self.config = config
        self.location = config.rootpath
        self.quiet = "quiet" in config.option
        self.console = self._create_console(config)

        self.event_bus = EventBus()
        self.source_id = source_id_generator()
        self.publisher = EventPublisher(self.source_id, self.event_bus)

        self.run_id = str(uuid.uuid1())
        self.results = TestRunResults(run_id=self.run_id)
        self._create_plugins(config)

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionstart(self, session: Session) -> None:
        """Publish a ConfigLoaded and a TestRunStarted event."""

        logging.debug("session: pytest_sessionstart")
        if not self.quiet:
            print_separator(self.console, "Pytest Rich Trace", color="blue")

        item_id = session.nodeid if session.nodeid else ""

        start_time = datetime.now()
        self.results.start = start_time

        precise_start = time.perf_counter()
        self.results.precise_start = precise_start

        self._publish_environment()
        self._test_run_started(item_id)

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session: Session) -> None:
        """Publish a TestRunFinished event"""
        logging.debug("session: pytest_sessionfinish")

        stop_time = datetime.now()
        self.results.stop = stop_time
        precise_stop = time.perf_counter()
        self.results.precise_stop = precise_stop

        item_id = session.nodeid if session.nodeid else ""
        self._test_run_finished(item_id)

        if "output_json" in self.config.option and self.config.option.output_json:
            data = self.results.model_dump_json(indent=4)
            with open(self.config.option.output_json, "w") as fp:
                fp.write(data)

    def duration(self) -> timedelta:
        stop = self.results.stop
        start = self.results.start
        if stop is None or start is None:
            raise ValueError(f"Stop time {stop} is before start time {start}")
        if stop < start:
            raise ValueError("end time is before start time")

        return stop - start

    def duration_precise(self) -> float:
        stop = self.results.precise_stop
        start = self.results.precise_start
        if stop is None or start is None:
            raise ValueError(f"Precise stop time {stop} is before start time {start}")
        if stop < start:
            raise ValueError("end time is before start time")

        return stop - start

    def _create_console(self, config):
        record = False
        self.output_svg = None
        if "output_svg" in config.option and config.option.output_svg is not None:
            record = True
            self.output_svg = self.config.option.output_svg

        self.output_html = None
        if "output_html" in config.option and config.option.output_html is not None:
            record = True
            self.output_html = self.config.option.output_html

        self.output_text = None
        if "output_text" in config.option and config.option.output_text is not None:
            record = True
            self.output_text = self.config.option.output_text

        self.theme = rich.theme.Theme(
            styles={
                "hook": "green",
                "hookname": "yellow",
                "keyname": "blue",
                "item": "white",
                "passed": "green",
                "failed": "red",
                "skipped": "orange3",
                "error": "bright_red",
                "separator": "green",
                "xfailed": "dark_orange",
                "xpassed": "orange1",
                "deselected": "dim white",
            }
        )

        no_color = config.option.color == "no"

        return rich.console.Console(theme=self.theme, record=record, no_color=no_color)

    def _create_plugins(self, config):
        self.collector = CollectionObserver(config, self.results, self.event_bus)
        self.runtest = TestExecutionObserver(config, self.results, self.event_bus)
        self.writer = RichReporter(
            config, self.results, self.event_bus, console=self.console
        )

        config.pluginmanager.register(self, name="richtrace_session")
        config.pluginmanager.register(self.collector, name="richtrace_collection")
        config.pluginmanager.register(self.runtest, name="richtrace_testrun")
        config.pluginmanager.register(self.writer, name="richtrace_richreporter")

    def _collect_environment(self) -> dict[str, Any]:
        env: dict[str, str | list[str] | pytest.Config] = {}
        env["platform"] = sys.platform
        env["python"] = platform.python_version()
        env["pytest_version"] = _pytest.__version__
        env["pluggy_version"] = pluggy.__version__
        env["config"] = self.config

        lines = self.config.hook.pytest_report_header(
            config=self.config, start_path=self.config.rootpath
        )
        if lines:
            for line_or_lines in reversed(lines):
                if isinstance(line_or_lines, str):
                    env["plugin_report_header"] = [line_or_lines]
                else:
                    env["plugin_report_header"] = line_or_lines

        return env

    def _publish_environment(self):
        env = self._collect_environment()
        self.publisher.publish(
            events.Environment,
            item_id=self.location,
            payload={"env": env},
        )

    def _test_run_started(self, item_id: ItemId):
        self.publisher.publish(
            events.TestRunStarted,
            item_id=str(self.location),
            payload={
                "start": self.results.start,
                "precise_start": self.results.precise_start,
            },
        )

    def _test_run_finished(self, item_id: ItemId):
        self.results.execute.stop = datetime.now()
        self.results.execute.precise_stop = time.perf_counter()
        self.publisher.publish(
            events.ExecutionFinished,
            item_id=item_id,
            payload={
                "stop": self.results.stop,
                "precise_stop": self.results.precise_stop,
            },
        )
        self.publisher.publish(
            events.TestRunFinished,
            item_id=item_id,
            payload={
                "stop": self.results.stop,
                "precise_stop": self.results.precise_stop,
            },
        )
        self.save_output()

    def save_output(self) -> None:
        if self.output_svg is not None:
            self.console.save_svg(self.output_svg)
        if self.output_html is not None:
            self.console.save_html(self.output_html)
        if self.output_text is not None:
            self.console.save_text(self.output_text)
