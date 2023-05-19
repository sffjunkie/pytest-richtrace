# pytest-richtrace

A pytest plugin that dumps the stages of the pytest testing process to the terminal.

It uses `rich` to add formatting to the output.

## Installation

Install using pip

```shell
pip install pytest_richtrace
```

## Usage

To activate the plugin add the `--rich-trace` option to the `pytest` command line.

## Sample output

### Using --collect-only

```shell
pytest --rich-trace --collect-only
```

![--collect-only output](docs/quickstart/output-collect-only.svg | width=70rem)

### Full test run

#### Quiet output

```shell
pytest --rich-trace -q
```

![quiet output](docs/quickstart/output-quiet.svg | width=70rem)

#### Normal output

```shell
pytest --rich-trace
```

![normal output](docs/quickstart/output.svg | width=70rem)

### Verbose output

```shell
pytest --rich-trace --verbose
```

![verbose output](docs/quickstart/output-verbose.svg | width=70rem)

### --collect-only output

```shell
pytest --rich-trace --collect-only
```

![collect-only output](docs/quickstart/output-collect-only.svg | width=70rem)
