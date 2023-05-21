import importlib
import logging
import platform
import re
import sys
from pathlib import Path
from textwrap import indent, wrap

import _pytest
import pluggy  # type: ignore
import pytest
import rich
import rich.box
import rich.console
import rich.padding
import rich.table
import rich.theme
import rich.traceback
from _pytest.skipping import evaluate_skip_marks, evaluate_xfail_marks
from _pytest.terminal import _plugin_nameversions
from rich.padding import Padding

from . import events
from .console import (
    INDENT,
    MIN_WIDTH,
    print_hook_info,
    print_key,
    print_key_value,
    print_separator,
    print_value,
)
from .event import SOURCE_ID_GENERATOR, Event, EventBus, EventCallback
from .results import TestRunResults, TestStage


class RichReporter:
    def __init__(
        self,
        config: pytest.Config,
        results: TestRunResults,
        event_bus: EventBus,
        console: rich.console.Console,
        source_id_generator=SOURCE_ID_GENERATOR,
    ):
        self.config = config
        self.results = results
        self.quiet = "quiet" in config.option
        self.verbose = "verbose" in config.option and config.option.verbose == 1

        self.source_id = source_id_generator()
        self._event_handlers = self._configure_event_handlers()
        event_bus.subscribe(self.source_id, self.event_handler)

        self.console = console

    # region collection

    @pytest.hookimpl
    def pytest_itemcollected(self, item: pytest.Item) -> None:
        logging.debug("rich_writer: pytest_itemcollected")

        if self.quiet:
            return

        print_hook_info(self.console, "pytest_itemcollected", item.nodeid)

        if not self.verbose:
            return

        print_key_value(self.console, "nodeid", item.nodeid, prefix=INDENT)

        markers = list(item.iter_markers())

        skip_markers = ", ".join(
            [mark.name for mark in markers if mark.name.startswith("skip")]
        )

        xfail_markers = ", ".join(
            [mark.name for mark in markers if mark.name.startswith("xfail")]
        )

        if skip_markers or xfail_markers:
            print_key(self.console, "markers", prefix=INDENT)
            skipped = evaluate_skip_marks(item)
            if skipped is not None:
                table = rich.table.Table()
                table = rich.table.Table(
                    show_header=False, show_edge=False, show_lines=False
                )
                table.add_column("name", style="keyname", width=15)
                table.add_column("value", width=61)

                table.add_row("type", "skip")
                table.add_row("reason", skipped.reason)
                table.add_row("marker", skip_markers)

                padding = rich.padding.Padding(table, (0, 0, 0, 8))
                self.console.print(padding)

            xfailed = evaluate_xfail_marks(item)
            if xfailed is not None:
                table = rich.table.Table()
                table = rich.table.Table(
                    show_header=False, show_edge=False, show_lines=False
                )
                table.add_column("name", style="keyname", width=15)
                table.add_column("value", width=61)

                table.add_row("type", "xfail")
                table.add_row("reason", xfailed.reason)
                if xfailed.raises:
                    table.add_row("raises", str(xfailed.raises))
                table.add_row("run", str(xfailed.run))
                table.add_row("strict", str(xfailed.strict))
                table.add_row("marker", xfail_markers)

                padding = rich.padding.Padding(table, (0, 0, 0, 8))
                self.console.print(padding)

    # endregion

    # region run tests

    # endregion

    # region event handling
    def event_handler(self, event: Event) -> None:
        handler = self._event_handlers.get(event.name, None)
        if handler is not None:
            handler(event)

    def _environment_received(self, event: Event) -> None:
        self._print_environment()
        return None

    def _test_run_started(self, event: Event) -> None:
        logging.debug("rich_writer: session started")

        if not self.quiet:
            print_separator(self.console, "Test Run started")
        return None

    def _test_run_finished(self, event: Event) -> None:
        logging.debug("rich_writer: session finished")

        if not self.quiet:
            print_separator(self.console, "Test Run finished")
        self.print_testrun_results()
        return None

    def _collection_started(self, event: Event) -> None:
        logging.debug("rich_writer: collection stage started")

        if not self.quiet:
            print_separator(self.console, "Test Collection started")

            print_hook_info(self.console, "pytest_collection")
            if event.payload and "session" in event.payload:
                session = str(event.payload["session"])
            else:
                session = ""
            print_key_value(self.console, f"{INDENT}session", session)
        return None

    def _collect_makereport(self, event: Event) -> None:
        """Create/Modify the collect report"""
        logging.debug("rich_writer: pytest_make_collect_report")

        if self.quiet:
            return None

        if event.payload and "collector" in event.payload:
            nodeid = event.payload["collector"].nodeid
        else:
            nodeid = ""
        print_hook_info(self.console, "pytest_make_collect_report", nodeid)
        return None

    def _collect_start(self, event: Event) -> None:
        logging.debug("rich_writer: pytest_collectstart")

        if self.quiet:
            return None

        if event.payload and "collector" in event.payload:
            nodeid = event.payload["collector"].nodeid
        else:
            nodeid = ""
        print_hook_info(self.console, "pytest_collectstart", nodeid)

        if not self.verbose:
            return None

        if nodeid:
            print_key_value(self.console, "nodeid", nodeid, prefix=INDENT)
        return None

    def _collect_file(self, event: Event) -> None:
        logging.debug("rich_writer: pytest_collect_file")

        if self.quiet:
            return None

        print_hook_info(self.console, "pytest_collect_file", str(event.item_id))
        return None

    def _pycollect_makemodule(self, event: Event) -> None:
        logging.debug("rich_writer: pytest_pycollect_makemodule")

        if self.quiet:
            return None

        print_hook_info(self.console, "pytest_pycollect_makemodule", str(event.item_id))
        return None

    def _pycollect_module_error(self, event: Event) -> None:
        if self.quiet:
            return None

        if event.payload and "exception" in event.payload:
            message = event.payload["exception"].msg
        else:
            message = ""
        self.console.print(f"{INDENT}[error]Error collecting module[/]:")
        self.console.print(f"{INDENT*2}[white]{event.item_id}[/]")
        if message:
            self.console.print(f"{INDENT*2}{message}")
        return None

    def _pycollect_makeitem(self, event: Event) -> None:
        ...

    def _collect_report(self, event: Event) -> None:
        logging.debug("rich_writer: pytest_collectreport")

        if self.quiet:
            return None

        print_hook_info(self.console, "pytest_collectreport", event.item_id or "")

        if self.verbose and event.item_id:
            if event.payload and "report" in event.payload:
                self._print_collect_report(event.payload["report"])

        return None

    def _collect_deselected(self, event: Event) -> None:
        logging.debug("rich_writer: pytest_deselected")

        if self.quiet:
            return None

        print_hook_info(self.console, "pytest_deselected")
        # for item in items:
        #     self._test_deselected_ids.add(item.nodeid)
        return None

    def _collect_modifyitems(self, event: Event) -> None:
        logging.debug("rich_writer: pytest_collection_modifyitems")

        if self.quiet:
            return None

        print_hook_info(self.console, "pytest_collection_modifyitems")

        if self.verbose:
            if event.payload and "items" in event.payload:
                items = event.payload["items"]
                if not self.quiet and items:
                    self.console.print(f"{INDENT}[keyname]items[/]:")
                    item_text = "\n".join([f.name for f in items]).replace("[", "\\[")

                    self.console.print(indent(item_text, INDENT * 2))
                    self.console.print()

        return None

    def _collection_finished(self, event: Event) -> None:
        logging.debug("rich_writer: pytest_collection_finish")

        if self.quiet:
            return

        print_hook_info(self.console, "pytest_collection_finish", event.item_id or "")

        if self.verbose:
            if event.payload and "session" in event.payload:
                print_key_value(
                    self.console, "session", repr(event.payload["session"]), INDENT
                )
                self.console.print()

        print_separator(self.console, "Test Collection finished")
        return None

    def _execution_started(self, event: Event) -> None:
        logging.debug("rich_writer: pytest_runtestloop")

        if self.quiet:
            return

        if not self.config.option.collectonly:
            self.console.print()
            print_separator(self.console, "Test Execution started")

        return None

    def _execute_logstart(self, event: Event) -> None:
        logging.debug("rich_writer: pytest_runtest_logstart")
        if not self.quiet:
            self.console.print()
            print_hook_info(
                self.console, "pytest_runtest_logstart", info=event.item_id or ""
            )

            if self.verbose:
                if event.payload and "function" in event.payload:
                    print_key_value(
                        self.console,
                        "function",
                        event.payload["function"],
                        prefix=INDENT,
                    )
                if event.payload and "module" in event.payload:
                    print_key_value(
                        self.console, "module", event.payload["module"], prefix=INDENT
                    )
                if event.payload and "line" in event.payload:
                    print_key_value(
                        self.console, "line", str(event.payload["line"]), prefix=INDENT
                    )

        return None

    def _execute_makereport(self, event: Event) -> None:
        logging.debug("rich_writer: pytest_runtest_makereport")

        if not self.quiet:
            print_hook_info(
                self.console,
                "pytest_runtest_makereport",
                info=event.item_id or "",
                prefix=INDENT,
            )
        return None

    def _execute_logreport(self, event: Event) -> None:
        logging.debug("rich_writer: pytest_runtest_logreport")

        if not self.quiet:
            if self.verbose:
                self.console.print()

            info = event.item_id or ""
            report = None
            if event.payload and "report" in event.payload:
                report = event.payload["report"]

            if report is not None:
                if not self.verbose:
                    info += f"    when={report.when}"

            print_hook_info(
                self.console,
                "pytest_runtest_logreport",
                info=info,
                prefix=INDENT,
            )

            if self.verbose and report is not None:
                self._print_logreport(report)
        return None

    def _execute_logfinish(self, event: Event) -> None:
        logging.debug("rich_writer: pytest_runtest_logfinish")

        if not self.quiet:
            if self.verbose:
                self.console.print()
            print_hook_info(
                self.console,
                "pytest_runtest_logfinish",
                info=event.item_id or "",
                prefix=INDENT,
            )
        return None

    def _execution_finished(self, event: Event) -> None:
        if not self.quiet and not self.config.option.collectonly:
            print_separator(self.console, "Test Execution finished")
        return None

    def _configure_event_handlers(self) -> dict[str, EventCallback]:
        return {
            events.Environment: self._environment_received,
            events.TestRunStarted: self._test_run_started,
            events.TestRunFinished: self._test_run_finished,
            # Collection
            events.CollectionStarted: self._collection_started,
            events.CollectStart: self._collect_start,
            events.CollectMakeReport: self._collect_makereport,
            events.CollectFile: self._collect_file,
            events.ModuleCollectionError: self._pycollect_module_error,
            events.ItemsDeselected: self._collect_deselected,
            events.ModifyItems: self._collect_modifyitems,
            events.CollectionFinished: self._collection_finished,
            # Test Execution
            events.ExecutionStarted: self._execution_started,
            events.ExecuteItemStarted: self._execute_logstart,
            events.ExecuteItemReport: self._execute_logreport,
            events.ExecuteItemFinished: self._execute_logfinish,
            events.ExecutionFinished: self._execution_finished,
        }

    # endregion

    # region report output
    def _print_environment(self) -> None:
        if self.quiet or not self.verbose:
            return None

        print_key(self.console, "pytest config")

        width = min(MIN_WIDTH - len(INDENT), self.console.width)

        table = rich.table.Table(
            width=width,
            show_header=False,
        )
        table.add_column("name", style="keyname")
        table.add_column("value", style="white")
        table.add_row("python version", platform.python_version())
        table.add_row("pytest version", _pytest._version.version)
        table.add_row("pluggy version", pluggy.__version__)
        table.add_row("platform", sys.platform)

        rootpath = str(self.config.rootpath)
        table.add_row("root path", rootpath)

        inipath = str(self.config.inipath)
        table.add_row("config path", inipath)

        plugins = self.config.pluginmanager.list_plugin_distinfo()
        plugin_names = ", ".join(_plugin_nameversions(plugins))
        table.add_row("plugins", plugin_names)

        padding = rich.padding.Padding(table, (0, 0, 0, len(INDENT)))
        self.console.print(padding)

        self.console.print()

        table = rich.table.Table(
            width=width,
            # show_header=False,
            border_style="green",
        )
        item_count = 3
        for col in range(item_count * 2):
            if col % 2 == 0:
                name = "option"
            else:
                name = "value"
            table.add_column(name, header_style="green")

        def chunk(lst, n):
            """Yield successive n-sized chunks from lst."""
            for i in range(0, len(lst), n):
                yield lst[i : i + n]  # noqa

        options = vars(self.config.option)
        keys = sorted(options.keys())
        rows_of_keys = chunk(keys, item_count)
        for row in rows_of_keys:
            row_items = []
            for key in row:
                row_items.append(key)
                v = options[key]
                if isinstance(v, str):
                    row_items.append(f'"{v}"')
                else:
                    row_items.append(str(v))
            table.add_row(*row_items)
        self.console.print(Padding(table, (0, 0, 0, len(INDENT))))

    def _print_collect_report(self, report: pytest.CollectReport) -> None:
        print_key_value(self.console, "nodeid", report.nodeid, prefix=INDENT)

        table = rich.table.Table(show_header=False, show_edge=False, show_lines=False)
        table.add_column("name", style="keyname", width=15)
        table.add_column("value", width=61)

        table.add_row("outcome", f"[{report.outcome}]{report.outcome}[/]")

        if report.caplog:
            table.add_row(
                "caplog",
                strip_escape_from_string(report.caplog),
            )

        if report.capstderr:
            table.add_row(
                "capstderr",
                strip_escape_from_string(report.capstderr),
            )

        if report.capstdout:
            width = self.console.width - len(INDENT) * 3
            stdout_text = "\n".join(
                wrap(
                    strip_escape_from_string(report.capstdout),
                    width=width,
                    initial_indent=INDENT * 2,
                    subsequent_indent=INDENT * 2,
                )
            ).strip()
            table.add_row("capstdout", stdout_text)

        padding = rich.padding.Padding(table, (0, 0, 0, 8))
        self.console.print(padding)

    def _print_logreport(self, report) -> None:
        table = rich.table.Table(show_header=False, show_edge=False, show_lines=False)
        table.add_column(
            "name",
            style="keyname",
            width=12,
        )
        table.add_column("value", width=71)

        module, line, func = report.location
        table.add_row("when", report.when)
        table.add_row("outcome", f"[{report.outcome}]{report.outcome}[/]")
        table.add_row("function", func.replace("[", "\\[]"))
        table.add_row("module", module)
        table.add_row("line", str(line))
        table.add_row("start", str(report.start))
        table.add_row("stop", str(report.stop))
        table.add_row("duration", str(report.duration))
        # table.add_row("keywords", str(report.keywords))

        padding = rich.padding.Padding(table, (0, 0, 0, 8))
        self.console.print(padding)

    def print_testrun_results(self) -> None:
        if self.config.option.collectonly:
            return None

        if not self.quiet:
            self.console.print()
        print_separator(self.console, "Test Run results")

        collect_error_count = len(self.results.collect.error)
        execute_error_count = len(self.results.execute.error)

        self._print_counts_table(collect_error_count, execute_error_count)

        if collect_error_count + execute_error_count > 0:
            self.console.print()

        if collect_error_count > 0:
            self._print_collect_errors(collect_error_count)

        if execute_error_count > 0:
            self._print_execute_errors(collect_error_count)

        if len(self.results.execute.failed) > 0:
            self._print_failed()

        if len(self.results.execute.passed) > 0:
            self._print_passed()

        if len(self.results.execute.skipped) > 0:
            self._print_skipped()

        if len(self.results.execute.xfailed) > 0:
            self._print_xfailed()

        if len(self.results.execute.xpassed) > 0:
            self._print_xpassed()

        if len(self.results.collect.deselected) > 0:
            self._print_deselected()

        print(f"\n{INDENT}Test Count = {self.results.collect.count}")

    def _print_counts_table(self, collect_error_count, execute_error_count):
        error_count = collect_error_count + execute_error_count
        failed_count = len(self.results.execute.failed)
        passed_count = len(self.results.execute.passed)
        skipped_count = len(self.results.execute.skipped)
        xfailed_count = len(self.results.execute.xfailed)
        xpassed_count = len(self.results.execute.xpassed)
        deselected_count = len(self.results.collect.deselected)

        results_table = rich.table.Table(box=rich.box.SQUARE, border_style="dim white")
        for column in (
            "error",
            "failed",
            "passed",
            "skipped",
            "xfailed",
            "xpassed",
            "deselected",
        ):
            results_table.add_column(column, style=column, header_style=column)

        results_table.add_row(
            str(error_count),
            str(failed_count),
            str(passed_count),
            str(skipped_count),
            str(xfailed_count),
            str(xpassed_count),
            str(deselected_count),
        )
        padded_table = Padding(results_table, (0, 0, 0, len(INDENT)))
        self.console.print(padded_table)

    def _print_failed(self):
        self.console.print()
        print_separator(
            self.console,
            f"Failed ({len(self.results.execute.failed)})",
            color="failed",
        )
        blank_line = True
        for nodeid in sorted(self.results.execute.failed):
            if blank_line:
                blank_line = False
            else:
                if self.verbose:
                    self.console.print()

            print_value(self.console, f"{INDENT}{nodeid}", color="failed")

            if self.verbose:
                info = self.results.execute.nodes[nodeid]
                if info.stages[TestStage.Setup].exception is not None:
                    self._print_exc(info.stages[TestStage.Setup].exception)

                if info.stages[TestStage.Call].exception is not None:
                    self._print_exc(info.stages[TestStage.Call].exception)

                if info.stages[TestStage.Teardown].exception is not None:
                    self._print_exc(info.stages[TestStage.Teardown].exception)

    def _print_passed(self):
        self.console.print()
        print_separator(
            self.console,
            f"Passed ({len(self.results.execute.passed)})",
            color="passed",
        )
        for nodeid in sorted(self.results.execute.passed):
            print_value(self.console, nodeid, prefix=INDENT, color="passed")

    def _print_skipped(self):
        self.console.print()
        print_separator(
            self.console,
            f"Skipped ({len(self.results.execute.skipped)})",
            color="skipped",
        )
        for nodeid in sorted(self.results.execute.skipped):
            self.console.print(f"{INDENT}[skipped]{nodeid}[/]")

            skipinfo = self.results.collect.skip.get(nodeid, None)
            extra = ""
            if self.verbose and skipinfo is not None:
                reason = ", ".join([x.reason for x in skipinfo if x.reason is not None])
                if reason:
                    extra += f"reason={reason}"

                if extra:
                    self.console.print(f"{INDENT*2}{extra}", highlight=False)

    def _print_xfailed(self):
        self.console.print()
        print_separator(
            self.console,
            f"XFailed ({len(self.results.execute.xfailed)})",
            color="xfailed",
        )
        for nodeid in self.results.execute.xfailed:
            self.console.print(f"{INDENT}[xfailed]{nodeid}[/]")

            xfailinfo = self.results.collect.xfail.get(nodeid, None)
            extra = ""
            if self.verbose and xfailinfo is not None:
                reasons = ", ".join(
                    [x.reason for x in xfailinfo if x.reason is not None]
                )
                if reasons:
                    extra += f"reason={reasons}"

                raises = ", ".join(
                    [str(x.raises.__name__) for x in xfailinfo if x.raises is not None]
                )
                if raises:
                    if extra:
                        extra += ". "
                    extra += f"raises={raises}"

                if extra:
                    self.console.print(f"{INDENT*2}{extra}", highlight=False)

    def _print_xpassed(self):
        self.console.print()
        print_separator(
            self.console,
            f"XPassed ({len(self.results.execute.xpassed)})",
            color="xpassed",
        )
        for nodeid in self.results.execute.xpassed:
            print_value(self.console, nodeid, prefix=INDENT, color="xpassed")

            xfailinfo = self.results.collect.xfail.get(nodeid, None)
            extra = ""
            if self.verbose and xfailinfo is not None:
                reasons = ", ".join(
                    [x.reason for x in xfailinfo if x.reason is not None]
                )
                if reasons:
                    extra += f"reason={reasons}"

                raises = ", ".join(
                    [str(x.raises.__name__) for x in xfailinfo if x.raises is not None]
                )
                if raises:
                    if extra:
                        extra += ". "
                    extra += f"raises={raises}"

                if extra:
                    self.console.print(f"{INDENT*2}{extra}", highlight=False)

    def _print_deselected(self):
        self.console.print()
        print_separator(
            self.console,
            f"Deselected ({len(self.results.collect.deselected)})",
            color="deselected",
        )
        for nodeid in self.results.collect.deselected:
            print_value(self.console, nodeid, prefix=INDENT, color="deselected")

    def _print_execute_errors(self, collect_error_count):
        if len(self.results.collect.error) > 0:
            self.console.print()

        print_separator(
            self.console,
            f"Execution Errors ({collect_error_count})",
            color="error",
        )
        print_first = True
        for moduleid in sorted(self.results.execute.error):
            if print_first:
                print_first = False
            else:
                self.console.print()

            print_value(self.console, f"{INDENT}{moduleid}", color="error")
            node = self.results.execute.nodes[moduleid]
            exc = node.stages[TestStage.Setup].exception
            if exc is not None:
                self._print_exc(exc)

    def _print_collect_errors(self, collect_error_count):
        print_separator(
            self.console,
            f"Collection Errors ({collect_error_count})",
            color="error",
        )
        print_first = True
        for nodeid, exc in self.results.collect.error.items():
            if print_first:
                print_first = False
            else:
                self.console.print()

            print_value(self.console, f"{INDENT}{nodeid}", color="error")
            self._print_exc(exc)

    def _print_exc(self, exc: BaseException):
        collector_path = Path(__file__).parent / "collector"
        width = MIN_WIDTH - len(INDENT)
        tb = rich.traceback.Traceback.from_exception(
            type(BaseException),
            exc,
            exc.__traceback__,
            suppress=(_pytest, pluggy, importlib, str(collector_path)),
            max_frames=1,
            width=width,
        )
        pad = Padding(tb, (0, 0, 0, 4))
        self.console.print(pad)

    def _print_event_log(self):
        log = self.results.events
        for event in log:
            print(event)

    # endregion


def strip_escape(data: bytes) -> bytes:
    """Strip 7-bit and 8-bit C1 ANSI sequences
    https://stackoverflow.com/a/14693789/3253026
    """
    ansi_escape_8bit = re.compile(
        rb"(?:\x1B[@-Z\\-_]|[\x80-\x9A\x9C-\x9F]|(?:\x1B\[|\x9B)[0-?]*[ -/]*[@-~])"
    )
    return ansi_escape_8bit.sub(b"", data)


def strip_escape_from_string(text: str) -> str:
    return strip_escape(text.encode("utf-8")).decode("utf-8")


def _remove_cwd(dirname: str) -> str:
    if dirname is None:
        return

    if dirname.startswith(str(Path.cwd())):
        p = Path(dirname)
        return ".../" + p.name

    return dirname
