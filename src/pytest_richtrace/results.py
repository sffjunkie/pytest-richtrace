import traceback
from datetime import datetime
from enum import StrEnum
from typing import Type, TypeVar

from pydantic import BaseModel, Field, field_serializer

from .item import ModuleId, NodeId

Marker = str
PerfTime = float

E = TypeVar("E", bound=BaseException, covariant=True)


class TestStage(StrEnum):
    Collect = "collect"
    Setup = "setup"
    Call = "call"
    Teardown = "teardown"


class TestResult(StrEnum):
    Error = "error"
    Passed = "passed"
    Failed = "failed"
    Skipped = "skipped"
    XFailed = "xfailed"
    XPassed = "xpassed"
    Deselected = "deselected"
    Unknown = "unknown"


class SkipInfo(BaseModel):
    reason: str
    markers: list[Marker] = Field(default_factory=list)


RaisesType = Type[BaseException] | tuple[Type[BaseException], ...]


class XfailInfo(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    reason: str
    raises: RaisesType | None
    run: bool
    strict: bool
    markers: list[Marker] = Field(default_factory=list)

    @field_serializer("raises")
    def serialize_exception(self, exc: RaisesType | None, _info) -> str:
        if exc is None:
            return ""

        if isinstance(exc, tuple):
            excs = exc
        else:
            excs = (exc,)

        return ", ".join([str(exc.__name__) for exc in excs])


class TestCollectionRecord(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    count: int = 0
    start: datetime | None = None
    stop: datetime | None = None
    precise_start: PerfTime = 0.0
    precise_stop: PerfTime = 0.0
    error: dict[ModuleId, BaseException] = Field(default_factory=dict)
    skip: dict[NodeId, list[SkipInfo]] = Field(default_factory=dict)
    xfail: dict[NodeId, list[XfailInfo]] = Field(default_factory=dict)
    deselected: list[NodeId] = Field(default_factory=list)

    def __rich_repr__(self):
        yield "error", self.error
        yield "skip", self.skip
        yield "xfail", self.xfail
        if self.deselected:
            yield "deselected", self.deselected

    @field_serializer("error")
    def serialize_exception(
        self, exc_info: dict[ModuleId, BaseException], _info
    ) -> dict[ModuleId, str]:
        def format_exc(exc: BaseException) -> str:
            return "".join(traceback.format_exception_only(type(exc), exc)).rstrip("\n")

        return {k: format_exc(exc) for k, exc in exc_info.items()}


class TestExecutionResultRecord(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    outcome: str = ""
    when: str = ""
    function: str = ""
    module: ModuleId = ""
    line: int | None = None
    precise_start: PerfTime = 0.0
    precise_stop: PerfTime = 0.0
    xfail: bool = False
    xdist: bool = False
    exception: BaseException | None = None

    def duration(self) -> PerfTime:
        return self.precise_stop - self.precise_start

    def __rich_repr__(self):
        yield "outcome", self.outcome
        yield "when", self.when
        yield "function", self.function
        yield "module", self.module
        yield "line", self.line
        if self.exception is not None:
            yield "exception", self.exception

    @field_serializer("exception")
    def serialize_exception(self, exc, _info) -> str:
        if exc is None:
            return ""

        msg = "".join(traceback.format_exception_only(exc)).rstrip("\n")
        return msg


class TestExecutionNodeRecord(BaseModel):
    nodeid: NodeId
    stages: dict[TestStage, TestExecutionResultRecord] = Field(default_factory=dict)
    result: TestResult = TestResult.Unknown


class TestExecutionRecord(BaseModel):
    count: int = 0
    start: datetime | None = None
    stop: datetime | None = None
    precise_start: PerfTime = 0.0
    precise_stop: PerfTime = 0.0

    nodes: dict[NodeId, TestExecutionNodeRecord] = Field(default_factory=dict)

    passed: set[NodeId] = Field(default_factory=set)
    failed: set[NodeId] = Field(default_factory=set)
    skipped: set[NodeId] = Field(default_factory=set)
    xfailed: set[NodeId] = Field(default_factory=set)
    xpassed: set[NodeId] = Field(default_factory=set)
    error: set[NodeId] = Field(default_factory=set)

    def __rich_repr__(self):
        yield "passed", self.passed
        yield "failed", self.failed
        yield "skipped", self.skipped
        yield "xfailed", self.xfailed
        yield "xpassed", self.xpassed
        yield "error", self.error


class TestRunResults(BaseModel):
    run_id: str

    start: datetime | None = None
    stop: datetime | None = None
    precise_start: PerfTime = 0.0
    precise_stop: PerfTime = 0.0

    collect: TestCollectionRecord = Field(default_factory=TestCollectionRecord)
    execute: TestExecutionRecord = Field(default_factory=TestExecutionRecord)

    def __init__(self, **data):
        super().__init__(**data)

    def __rich_repr__(self):
        yield "run_id", self.run_id
        yield "collect", self.collect
        yield "execute", self.execute
