# pytest-richtrace

A pytest plugin that dumps the stages of the pytest testing process to the terminal.

It uses `rich` to add formatting to the output.

## Sample output

### Using --collect-only

```shell
pytest -q --collect-only --rich-trace
```

<img src="./docs/output-collect-only.svg" style="width: 70rem;"/>

### Full test run

```shell
pytest -q --rich-trace
```

<img src="./docs/output.svg" style="width: 70rem;"/>
