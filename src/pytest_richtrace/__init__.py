import platform
import re
import sys
from pathlib import Path
from pprint import pprint
from textwrap import indent, wrap
from typing import Any, List, NamedTuple, Optional, Union
from urllib.parse import urlunsplit

import _pytest._version
import pluggy
import pytest
import rich
import rich.console
import rich.theme
from _pytest.config import PytestPluginManager
from _pytest.main import Session
from _pytest.nodes import File
from _pytest.python import PyCollector
from _pytest.reports import TestReport
from _pytest.terminal import TerminalReporter, _plugin_nameversions

INDENT = "    "


def pytest_addoption(parser: pytest.Parser, pluginmanager: PytestPluginManager) -> None:
    """
    Add options to the pytest command line for the richtrace plugin
    :param parser: The pytest command line parser
    """
    group = parser.getgroup("richtrace")
    group.addoption(
        "--rich-trace",
        dest="rich_trace",
        action="store_true",
        help="Enable the richtrace plugin",
    )
    group.addoption(
        "--output-svg",
        dest="output_svg",
        help="Output the trace as an SVG file",
    )
    group.addoption(
        "--output-html",
        dest="output_html",
        help="Output the trace as an HTML file",
    )
    group.addoption(
        "--output-text",
        dest="output_text",
        help="Output the trace as a text file",
    )


def pytest_configure(config: pytest.Config) -> None:
    """
    Configure the richtrace
    :param config: The pytest config object
    """
    if config.option.rich_trace:
        config.pluginmanager.register(PytestRichTrace(config))


class PytestRichTrace:
    def __init__(
        self,
        config: pytest.Config,
    ):
        super().__init__()
        self.config = config
        self.quiet = "quiet" in config.option
        self.theme = rich.theme.Theme(
            styles={"hook": "green", "hookname": "bold", "key_name": "blue"}
        )

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

        self.console = rich.console.Console(theme=self.theme, record=record)
        self.indent = INDENT

    def pytest_sessionstart(
        self,
        session: Session,
    ) -> None:
        self._separator(f"{__name__} - Test run started")
        self._dump_config(self.config)
        self.console.print()
        self.console.print("[hook]hook[/]: [hookname]pytest_sessionstart[/]")
        self._separator("Session started")

    def pytest_report_header(
        self, config: pytest.Config, startdir
    ) -> Union[str, List[str]]:
        """string or list of strings to be displayed as header info for terminal reporting"""
        self.console.print("[hook]hook[/]: [hookname]pytest_report_header[/]")
        startdir = PytestRichTrace._remove_cwd(startdir)
        self.console.print(f"{INDENT}startdir: {startdir}")
        inipath = PytestRichTrace._remove_cwd(config.inipath)
        self.console.print(f"{INDENT}configfile: {inipath}")

        plugins = self.config.pluginmanager.list_plugin_distinfo()
        plugin_names = ", ".join(_plugin_nameversions(plugins))
        self.console.print(f"{INDENT}plugins: {plugin_names}")

        py_platform = sys.platform
        py_version = platform.python_version()
        pytest_version = _pytest._version.version
        pluggy_version = pluggy.__version__
        return f"{INDENT}header text: platform {py_platform} -- Python {py_version}, pytest-{pytest_version}, pluggy-{pluggy_version}\n"

    # region Test Collection

    def pytest_collection(self):
        if not self.quiet:
            self.console.print()
        self.console.print("[hook]hook[/]: [hookname]pytest_collection[/]")
        self._separator("Collection started")

    def pytest_collectstart(self, collector: PyCollector):
        self.console.print(f"[hook]hook[/]: [hookname]pytest_collectstart[/]")
        self.console.print(
            f"{INDENT}[key_name]collecting[/]: {collector.__class__.__name__}"
        )

        if collector.parent is not None:
            parent_name = f"{collector.parent.name}::"
        else:
            parent_name = ""

        self.console.print(
            f"{INDENT}[key_name]nodeid[/]: {parent_name}{collector.name}"
        )
        self.console.print()

    def pytest_make_collect_report(self, collector, report=None):
        """Creates/Modifies the collect report"""
        self.console.print("[hook]hook[/]: [hookname]pytest_make_collect_report[/]")
        self.console.print(f"{INDENT}collector: {repr(collector)}")
        if report is not None:
            self._dump_collect_report(report)

    def pytest_collect_file(
        self, path: "LocalPath", parent: pytest.Collector
    ) -> Optional[pytest.Collector]:
        self.console.print("[hook]hook[/]: [hookname]pytest_collect_file[/]")
        self.console.print(f"{INDENT}[key_name]path[/]: {str(path)}")

    def pytest_pycollect_makemodule(
        self, path: "LocalPath", parent
    ) -> Optional[pytest.Module]:
        self.console.print("[hook]hook[/]: [hookname]pytest_pycollect_makemodule[/]")
        self.console.print(f"{INDENT}[key_name]path[/]: {str(path)}")

    def pytest_itemcollected(self, item: pytest.Item):
        """Item collected"""
        self.console.print(
            "[hook]hook[/] [hookname]pytest_itemcollected[/]", repr(item)
        )

    def pytest_deselected(self, items: list[pytest.Item]):
        self.console.print("[hook]hook[/]: [hookname]pytest_deselected[/]", items)

    def pytest_collection_modifyitems(
        self, session: Session, config: pytest.Config, items: List[pytest.Item]
    ) -> None:
        self.console.print("[hook]hook[/]: [hookname]pytest_collection_modifyitems[/]")
        self.console.print(f"{INDENT}[key_name]items[/]:")
        item_text = "\n".join([repr(f) for f in items])
        self.console.print(indent(item_text, INDENT * 2))

    def pytest_collectreport(self, report: pytest.CollectReport):
        """Collector finished collecting"""
        self.console.print("[hook]hook[/]: [hookname]pytest_collectreport[/]")
        self._dump_collect_report(report)

    def pytest_report_collectionfinish(
        self,
        config: pytest.Config,
        start_path: str,
        startdir: str,
        items,
    ):
        self.console.print("[hook]hook[/]: [hookname]pytest_report_collectionfinish[/]")
        self.console.print(f"{INDENT}[key_name]config[/]: {config}")
        start_path = PytestRichTrace._remove_cwd(start_path)
        self.console.print(f"{INDENT}[key_name]start_path[/]: {start_path}")
        startdir = PytestRichTrace._remove_cwd(startdir)
        self.console.print(f"{INDENT}[key_name]startdir[/]: {startdir}")

        self.console.print(f"{INDENT}items:")
        item_text = "\n".join([repr(f) for f in items])
        self.console.print(indent(item_text, INDENT * 2))

    def pytest_collection_finish(self, session):
        self.console.print("[hook]hook[/]: [hookname]pytest_collection_finish[/]")
        self.console.print(f"{INDENT}[key_name]session[/]: {repr(session)}")
        self.console.print()
        self._separator("Collection finished")

    # endregion

    # region Test Execution
    def pytest_runtestloop(self, session: Session):
        self._separator("Test run started")

    def pytest_runtest_setup(self, item):
        """Called when run the 'setup' stage of a test"""
        self.console.print("[hook]hook[/]: [hookname]pytest_runtest_setup[/]", item)

    def pytest_runtest_call(self, item):
        """Called when run the 'call' stage of a test"""
        self.console.print("[hook]hook[/]: [hookname]pytest_runtest_call[/]", item)

    def pytest_runtest_teardown(self, item):
        """Called when run the 'teardown' stage of a test"""
        self.console.print("[hook]hook[/]: [hookname]pytest_runtest_teardown[/]", item)

    def pytest_runtest_logstart(self, nodeid, location):
        """Test starting"""
        self.console.print()
        lfile, line, lfunc = location
        self.console.print(f"[hook]hook[/]: [hookname]pytest_runtest_logstart[/]:")
        self.console.print(f"{INDENT}[key_name]nodeid[/]: {nodeid}")

        try:
            lclass, lmeth = lfunc.split(".")
            self.console.print(
                f"{INDENT}[key_name]method: {lmeth} of [key_name]class[/]: {lclass}"
            )
        except ValueError:
            self.console.print(f"{INDENT}[key_name]func[/]: {lfunc}")

        self.console.print(f"{INDENT}[key_name]in file[/]: {lfile}")
        self.console.print(f"{INDENT}[key_name]on line[/]: {line+1}")
        self.console.print()

    def pytest_runtest_makereport(self, item, call):
        """Runtest report"""
        # if call.when == "call":
        self.console.print(
            f"{INDENT}[hook]hook[/]: [hookname]pytest_runtest_makereport[/]"
        )
        self.console.print(f"{INDENT*2}[key_name]item[/]: ", item)
        self._dump_call(call)

    def pytest_runtest_logreport(
        self,
        report: TestReport,
    ) -> None:
        """setup, call, teardown"""
        # if report.when == "call":
        self.console.print(
            f"{INDENT}[hook]hook[/]: [hookname]pytest_runtest_logreport[/]"
        )
        self.console.print(f"{INDENT*2}{report}")

    def pytest_runtest_logfinish(self, nodeid, location):
        """Test ended"""
        self.console.print()
        self.console.print("[hook]hook[/]: [hookname]pytest_runtest_logfinish[/]")

    # endregion

    def pytest_sessionfinish(self, session: Session) -> None:
        """Session finished"""
        self.console.print("[hook]hook[/]: [hookname]pytest_sessionfinish[/]")
        self._separator("Test run complete")

    def pytest_terminal_summary(
        self,
        terminalreporter: TerminalReporter,
        exitstatus: pytest.ExitCode,
        config: pytest.Config,
    ) -> None:
        self._separator("Terminal summary")
        self.console.print("[hook]hook[/]: [hookname]pytest_terminal_summary[/]")
        if self.output_svg is not None:
            self.console.save_svg(self.output_svg)
        if self.output_html is not None:
            self.console.save_html(self.output_html)
        if self.output_text is not None:
            self.console.save_text(self.output_text)

    def _dump_config(self, config: pytest.Config):
        prefix = INDENT
        self.console.print(f"[blue]Using config[/]")
        rootpath = PytestRichTrace._remove_cwd(config.rootpath)
        self.console.print(f"{prefix}[key_name]rootpath[/]: {rootpath}")
        inipath = PytestRichTrace._remove_cwd(config.inipath)
        self.console.print(f"{prefix}[key_name]inipath[/]: {inipath}")
        options = "\n".join(
            wrap(
                str(config.option),
                # initial_indent=INDENT,
                subsequent_indent=INDENT * 2,
                width=self.console.width - len(prefix) * 2 - 8,
            )
        )
        self.console.print(f"{prefix}[key_name]option[/]: {options}")

    def _dump_call(self, call_info):
        prefix = INDENT * 2
        self.console.print(f"{prefix}[key_name]{call_info.when}[/]:")
        self.console.print(f"{prefix+INDENT}result: {call_info._result}")
        self.console.print(
            f"{prefix+INDENT}[key_name]start[/]: {call_info.start}, [key_name]stop[/]: {call_info.stop}, [key_name]duration[/]: {call_info.duration}"
        )
        if call_info.excinfo is not None:
            self.console.print(f"{prefix+INDENT}[key_name]exception[/]")
            self.console.print(indent(str(call_info.excinfo), INDENT * 4))

    def _dump_collect_report(self, report: pytest.CollectReport):
        prefix = INDENT
        self.console.print(f"{prefix}[key_name]nodeid[/]: {report.nodeid}")
        self.console.print(f"{prefix}[key_name]outcome[/]: {report.outcome}")

        if report.longrepr is not None:
            self.console.print(
                f"{prefix}[key_name]longreprtext[/]: {report.longreprtext}"
            )

        if report.caplog:
            self.console.print(
                f"{prefix}[key_name]caplog[/]: {strip_escape_from_string(report.caplog)}"
            )

        if report.capstderr:
            self.console.print(
                f"{prefix}[key_name]capstderr[/]: {strip_escape_from_string(report.capstderr)}"
            )

        if report.capstdout:
            width = self.console.width - len(prefix + INDENT)
            stdout_text = "\n".join(
                wrap(
                    strip_escape_from_string(report.capstdout),
                    width=width,
                    initial_indent=prefix + INDENT,
                    subsequent_indent=prefix + INDENT,
                )
            )
            self.console.print(f"{prefix}[key_name]capstdout[/]:")
            self.console.print(stdout_text)

        self.console.print(
            f"{prefix}[key_name]count_towards_summary[/]: {report.count_towards_summary}"
        )

        if report.head_line:
            self.console.print(f"{prefix}[key_name]head_line[/]: {report.head_line}")
        self.console.print()

    def _separator(self, text: str = ""):
        if text != "":
            equals_count = int((self.console.width - len(text) - 2) / 2)
            self.console.print(
                f"[green]{'=' * equals_count} {text} {'=' * equals_count}[/]"
            )
        else:
            self.console.print("[green]" + "=" * self.console.width + "[/]")

    @staticmethod
    def _remove_cwd(dirname: str) -> str | None:
        if dirname is None:
            return

        p = Path(dirname)
        if p == Path.cwd():
            return ".../" + p.name

        return dirname


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
