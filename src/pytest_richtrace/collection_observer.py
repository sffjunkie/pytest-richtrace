import logging
import time
from datetime import datetime
from pathlib import Path

import pytest
from _pytest._py.path import LocalPath
from _pytest.pathlib import import_path
from _pytest.python import Class, Module
from _pytest.skipping import evaluate_skip_marks, evaluate_xfail_marks

from . import events
from .event import SOURCE_ID_GENERATOR, EventBus, EventPublisher
from .item import NodeId
from .results import SkipInfo, TestRunResults, XfailInfo


class CollectionObserver:
    results: TestRunResults

    def __init__(
        self,
        config: pytest.Config,
        results: TestRunResults,
        event_bus: EventBus,
        source_id_generator=SOURCE_ID_GENERATOR,
    ):
        self.config = config
        self.results = results

        source_id = source_id_generator()
        self.publisher = EventPublisher(source_id, event_bus)

    class CollectError(Exception):
        """An error during collection, contains a custom message."""

    @pytest.hookimpl(tryfirst=True)
    def pytest_collection(self, session: pytest.Session) -> None:
        logging.debug("collector: pytest_collection")
        location = session.nodeid if session.nodeid else None

        self.results.collect.start = datetime.now()
        self.results.collect.precise_start = time.perf_counter()

        self.publisher.publish(
            events.CollectionStarted,
            item_id=location,
            payload={
                "session": session,
            },
        )
        return None

    @pytest.hookimpl
    def pytest_collectstart(self, collector: pytest.Collector) -> None:
        logging.debug("collector: pytest_collectstart")
        self.publisher.publish(
            events.CollectStart,
            item_id=collector.nodeid,
            payload={"collector": collector},
        )
        return None

    @pytest.hookimpl
    def pytest_make_collect_report(self, collector: pytest.Collector) -> None:
        logging.debug("collector: pytest_make_collect_report")
        self.publisher.publish(
            events.CollectMakeReport,
            item_id=collector.nodeid,
            payload={"collector": collector},
        )
        return None

    @pytest.hookimpl
    def pytest_collect_file(
        self, file_path: Path, parent: pytest.Collector
    ) -> pytest.Collector | None:
        self.publisher.publish(
            events.CollectFile,
            item_id=str(file_path),
            payload={"collector": parent},
        )
        return None

    @pytest.hookimpl
    def pytest_pycollect_makemodule(
        self, module_path: Path, path: LocalPath, parent: pytest.Collector
    ) -> pytest.Module | None:
        logging.debug("collector: pytest_pycollect_makemodule")

        importmode = self.config.getoption("--import-mode")
        try:
            import_path(str(module_path), mode=importmode, root=self.config.rootpath)
            self.publisher.publish(
                events.CollectPyModule,
                item_id=parent.nodeid,
                payload={"path": module_path},
            )
        except Exception as exc:
            self.results.collect.count += 1
            self.results.collect.error[str(module_path)] = exc
            self.publisher.publish(
                events.ModuleCollectionError,
                item_id=str(module_path),
                payload={"path": module_path, "exception": exc},
            )
        finally:
            return None

    @pytest.hookimpl
    def pytest_pycollect_makeitem(
        self, collector: Module | Class, name: str, obj: object
    ) -> pytest.Collector | None:
        logging.debug("collector: pytest_pycollect_makeitem")

        self.publisher.publish(
            events.CollectPyFile,
            item_id=collector.nodeid,
            # payload={"path": file_path},
        )
        return None

    @pytest.hookimpl
    def pytest_itemcollected(self, item: pytest.Item) -> None:
        logging.debug("collector: pytest_itemcollected")

        self.results.collect.count += 1

        markers = [mark.name for mark in item.iter_markers()]

        payload: dict[str, SkipInfo | XfailInfo] = {}
        nodeid = NodeId(item.nodeid)

        skipped = evaluate_skip_marks(item)
        if skipped is not None:
            skip_info = SkipInfo(
                reason=skipped.reason,
                markers=markers,
            )
            # TODO: Check if we need to store multiple SkipInfo
            if nodeid not in self.results.collect.skip:
                self.results.collect.skip[nodeid] = []
            self.results.collect.skip[nodeid].append(skip_info)
            payload["skipped"] = skip_info

        xfailed = evaluate_xfail_marks(item)
        if xfailed is not None:
            xfail_info = XfailInfo(
                reason=xfailed.reason,
                raises=xfailed.raises,
                run=xfailed.run,
                strict=xfailed.strict,
                markers=markers,
            )
            # TODO: Check if we need to store multiple XFailInfo
            if nodeid not in self.results.collect.xfail:
                self.results.collect.xfail[nodeid] = []
            self.results.collect.xfail[nodeid].append(xfail_info)
            payload["xfail"] = xfail_info

        self.publisher.publish(
            events.ItemCollected, item_id=item.nodeid, payload=payload
        )
        return None

    @pytest.hookimpl
    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        logging.debug("collector: pytest_collectreport")
        self.publisher.publish(
            events.CollectReport,
            item_id=report.nodeid,
            payload={"report": report},
        )
        return None

    @pytest.hookimpl
    def pytest_collection_modifyitems(
        self, session: pytest.Session, config: pytest.Config, items: list[pytest.Item]
    ) -> None:
        """Filter and re-order the list of tests"""
        logging.debug("collector: pytest_collection_modifyitems")
        self.publisher.publish(
            events.ModifyItems,
            item_id=session.nodeid,
            payload={"items": items},
        )
        return None

    @pytest.hookimpl
    def pytest_deselected(self, items: list[pytest.Item]):
        logging.debug("collector: pytest_deselected")
        for item in items:
            self.results.collect.deselected.append(item.nodeid)
        self.publisher.publish(
            events.ItemsDeselected,
            item_id=None,
            payload={"items": items},
        )
        return None

    @pytest.hookimpl(trylast=True)
    def pytest_collection_finish(self, session: pytest.Session) -> None:
        logging.debug("collector: pytest_collection_finish")
        self.results.collect.stop = datetime.now()
        self.results.collect.precise_stop = time.perf_counter()
        self.publisher.publish(
            events.CollectionFinished,
            session.nodeid,
            payload={
                "session": session,
            },
        )
        return None
