from .event import EventName

Environment: EventName = "test:run:environment"

TestRunStarted: EventName = "test:run:started"
TestRunFinished: EventName = "test:run:finished"

CollectionStarted: EventName = "test:collection:started"
CollectionFinished: EventName = "test:collection:finished"

CollectMakeReport: EventName = "test:collect:makereport"

# start collecting in a test "container" e.g. module, class
CollectStart: EventName = "test:collect:start"

# Collect a generic file
CollectFile: EventName = "test:collect:file"

# Collect items in a Python module
CollectPyModule: EventName = "test:collect:py:module"

# Collect items in a Python file
CollectPyFile: EventName = "test:collect:py:file"

# Item to be tested has been collected
ItemCollected: EventName = "test:item:collected"

ModifyItems: EventName = "test:collect:modify_items"

CollectReport: EventName = "test:collect:report"

# Item to be tested has been deselected
ItemsDeselected: EventName = "test:item:deselected"

# Errors
ModuleCollectionError: EventName = "test:module:collection:error"
ItemCollectionError: EventName = "test:item:collection:error"

# Test Execution Loop
ExecutionStarted: EventName = "test:execution:started"
ExecutionFinished: EventName = "test:execution:finished"

# Item Test Execution
ExecuteItemStarted: EventName = "test:execute:item:started"
ExecuteItemSetup: EventName = "test:execute:item:setup"
ExecuteItemCall: EventName = "test:execute:item:call"
ExecuteItemTeardown: EventName = "test:execute:item:teardown"
ExecuteItemReport: EventName = "test:execute:item:report"
ExecuteItemFinished: EventName = "test:execute:item:finished"
