import logging
import time
from datetime import datetime

import pytest
from _pytest.main import Session
from _pytest.nodes import Item
from _pytest.reports import TestReport
from _pytest.runner import CallInfo

from . import events
from .event import SOURCE_ID_GENERATOR, EventBus, EventPublisher
from .results import (
    TestExecutionNodeRecord,
    TestExecutionResultRecord,
    TestResult,
    TestRunResults,
    TestStage,
)


class TestExecutionObserver:
    def __init__(
        self,
        config: pytest.Config,
        results: TestRunResults,
        event_bus: EventBus,
        source_id_generator=SOURCE_ID_GENERATOR,
    ):
        self.config = config
        self.results = results

        self.source_id = source_id_generator()
        self.publisher = EventPublisher(self.source_id, event_bus)

    @pytest.hookimpl
    def pytest_runtestloop(self, session: Session) -> None:
        logging.debug("collector: pytest_runtestloop")

        self.results.execute.start = datetime.now()
        self.results.execute.precise_start = time.perf_counter()

        self.publisher.publish(events.ExecutionStarted, item_id=session.nodeid)

    @pytest.hookimpl
    def pytest_runtest_logstart(
        self, nodeid: str, location: tuple[str, int | None, str]
    ) -> None:
        logging.debug("collector: pytest_runtest_logstart")
        self.results.execute.count += 1
        self._current_execution_node = TestExecutionNodeRecord(nodeid=nodeid)
        module, line, func = location
        self.publisher.publish(
            events.ExecuteItemStarted,
            item_id=nodeid,
            payload={
                "module": module,
                "line": line,
                "function": func,
            },
        )
        return None

    @pytest.hookimpl
    def pytest_runtest_makereport(self, item: Item, call: CallInfo[None]) -> None:
        """Runtest report"""
        logging.debug("collector: pytest_runtest_makereport")
        if (
            call.excinfo is not None
            and call.excinfo._excinfo is not None
            and call.when not in self._current_execution_node.stages
        ):
            result = TestExecutionResultRecord()
            result.exception = call.excinfo._excinfo[1]
            self._current_execution_node.stages[TestStage(call.when)] = result

    @pytest.hookimpl
    def pytest_runtest_logreport(
        self,
        report: TestReport,
    ) -> None:
        """setup, call, teardown"""
        logging.debug("collector: pytest_runtest_logreport")

        if report.when is None:
            return

        when = TestStage(report.when)
        if when not in self._current_execution_node.stages:
            result = TestExecutionResultRecord()
            self._current_execution_node.stages[when] = result
        else:
            result = self._current_execution_node.stages[when]

        result.xfail = hasattr(report, "wasxfail")
        result.xdist = hasattr(report, "node")

        self._current_execution_node.stages[when].precise_start = report.start
        self._current_execution_node.stages[when].precise_finish = report.stop

        self._current_execution_node.stages[when].when = report.when
        self._current_execution_node.stages[when].outcome = report.outcome

        module, line, func = report.location
        self._current_execution_node.stages[when].module = module
        self._current_execution_node.stages[when].line = line
        self._current_execution_node.stages[when].function = func

        payload = {
            "module": module,
            "line": line,
            "function": func,
            "report": report,
        }

        if when == TestStage.Setup:
            event = events.ExecuteItemReport
        elif when == TestStage.Call:
            event = events.ExecuteItemCall
        elif when == TestStage.Teardown:
            event = events.ExecuteItemTeardown

        self.publisher.publish(
            event,
            item_id=report.nodeid,
            payload=payload,
        )

        self.publisher.publish(
            events.ExecuteItemReport,
            item_id=report.nodeid,
            payload=payload,
        )

    @pytest.hookimpl
    def pytest_runtest_logfinish(self, nodeid, location) -> None:
        """Test ended"""
        logging.debug("collector: pytest_runtest_logfinish")

        assert self._current_execution_node.nodeid == nodeid
        self.results.execute.nodes[
            self._current_execution_node.nodeid
        ] = self._current_execution_node
        self._finalize_node(nodeid)

        module, line, func = location
        self.publisher.publish(
            events.ExecuteItemFinished,
            nodeid,
            payload={
                "module": module,
                "line": line,
                "function": func,
            },
        )

    def _finalize_node(self, nodeid):
        logging.debug(f"collector: finalizing node {nodeid}")

        node = self._current_execution_node
        setup = node.stages.get("setup", None)
        call = node.stages.get("call", None)
        teardown = node.stages.get("teardown", None)

        if call is None:
            if setup.outcome == "skipped":
                node.result = TestResult.Skipped
                self.results.execute.skipped.add(nodeid)
            elif setup.outcome == TestResult.Failed:
                node.result = TestResult.Error
                self.results.execute.error.add(nodeid)
            else:
                node.result = TestResult.Unknown
        else:
            all_passed = all(
                (
                    setup.outcome == "passed",
                    call.outcome == "passed",
                    teardown.outcome == "passed",
                )
            )

            if call.xfail:
                if all_passed:
                    node.result = TestResult.XPassed
                    self.results.execute.xpassed.add(nodeid)
                else:
                    node.result = TestResult.XFailed
                    self.results.execute.xfailed.add(nodeid)
            else:
                if all_passed:
                    node.result = TestResult.Passed
                    self.results.execute.passed.add(nodeid)
                else:
                    if call.outcome == TestResult.Failed:
                        node.result = TestResult.Failed
                        self.results.execute.failed.add(nodeid)
                    elif call.outcome == TestResult.Skipped:
                        node.result = TestResult.Skipped
