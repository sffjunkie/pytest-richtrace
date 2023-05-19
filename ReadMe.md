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

![--collect-only output](/output-collect-only.svg | width=70rem)

### Full test run

- Quiet

    ```shell
    pytest --rich-trace -q
    ```

    ![quiet output](/output-quiet.svg | width=70rem)
