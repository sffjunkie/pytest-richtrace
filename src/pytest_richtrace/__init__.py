import pytest
from _pytest.config import PytestPluginManager, hookimpl

from pytest_richtrace.plugin import PytestRichTrace


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
        "--rich-trace-events",
        dest="rich_trace_events",
        action="store_true",
        help="Enable printing of events",
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


@hookimpl(trylast=True)
def pytest_configure(config: pytest.Config) -> None:
    """
    Configure the richtrace plugin
    :param config: The pytest config object
    """
    if config.option.rich_trace:
        reporter = config.pluginmanager.get_plugin("terminalreporter")
        config.pluginmanager.unregister(plugin=reporter)

        PytestRichTrace(config)
