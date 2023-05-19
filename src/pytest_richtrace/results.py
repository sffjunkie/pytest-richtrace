from datetime import datetime
from enum import StrEnum
from typing import Type, TypeVar

from pydantic import BaseModel, Field

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


class XfailInfo(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    reason: str
    raises: Type[BaseException] | tuple[Type[BaseException], ...] | None
    run: bool
    strict: bool
    markers: list[Marker] = Field(default_factory=list)


class TestCollectionRecord(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    count: int = 0
    start: datetime | None = None
    stop: datetime | None = None
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
        if self.traceback is not None:
            yield "traceback", self.traceback


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
