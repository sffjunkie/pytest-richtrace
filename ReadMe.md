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

### Full test run

#### Quiet output

```shell
pytest --rich-trace -q
```

<img src="docs/quickstart/output-quiet.svg" width="700px" alt="quiet output">

#### Normal output

```shell
pytest --rich-trace
```

<img src="docs/quickstart/output.svg" width="700px" alt="normal output">

### Verbose output

```shell
pytest --rich-trace --verbose
```

<img src="docs/quickstart/output-verbose.svg" width="700px" alt="verbose output">

### --collect-only output

```shell
pytest --rich-trace --collect-only
```

<img src="docs/quickstart/output-collect-only.svg" width="700px" alt="--collect-only output">
