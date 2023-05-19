from textwrap import indent, wrap

from rich import console

INDENT = "    "
MIN_WIDTH = 100


def format_hook_info(
    name: str,
    info: str = "",
    prefix: str = "",
) -> str:
    name = name.ljust(28, " ")
    if info:
        info = info.replace("[", "\\[")
        return f"{prefix}[hook]hook[/]: [hookname]{name}[/] [white]{info}[/]"
    else:
        return f"{prefix}[hook]hook[/]: [hookname]{name}[/]"


def print_hook_info(
    console: console.Console,
    name: str,
    info: str = "",
    prefix: str = "",
) -> None:
    output = format_hook_info(name, info, prefix)
    console.print(output)


def format_separator(
    text: str = "",
    separator="=",
    color: str = "separator",
    width: int = 80,
) -> str:
    if text != "":
        char_count = int((width - (len(text) + 2)) / 2)
        chars = separator * char_count
        sep = chars + f" {text} " + chars

        if len(sep) < width:
            sep += separator * (width - len(sep))

        sep = f"[{color}]{sep}[/]"

        return sep
    else:
        return f"[{color}]" + (separator * width) + "[/]"


def print_separator(
    console: console.Console,
    text: str = "",
    separator="=",
    color: str = "separator",
) -> None:
    width = min(MIN_WIDTH, console.width)
    output = format_separator(text, separator, color, width=width)
    console.print(output)


def format_key(key: str, prefix: str = "", color: str = "white") -> str:
    return f"{prefix}[{color}]{key}[/]:"


def print_key(
    console: console.Console,
    key: str,
    prefix: str = "",
    color: str = "white",
) -> None:
    output = format_key(key, prefix, color=color)
    console.print(output)


def format_value(
    value: str,
    prefix: str = "",
    color: str = "white",
    wrap_text: bool = True,
    width: int = 80,
) -> str:
    if wrap_text:
        value = "\n".join(
            wrap(
                value,
                initial_indent=prefix,
                subsequent_indent=prefix,
                width=width - len(prefix) - 8,
            )
        )
    else:
        value = indent(value, prefix=prefix)
    value = value.replace("[", "\\[")
    return f"[{color}]{value}[/]"


def print_value(
    console: console.Console,
    value: str,
    prefix: str = "",
    color: str = "white",
    wrap_text: bool = True,
) -> None:
    output = format_value(value, prefix, color, wrap_text, width=console.width)
    console.print(output)


def format_key_value(
    key: str,
    value: str,
    prefix: str = "",
    key_color="keyname",
    value_color="white",
) -> str:
    value = value.replace("[", "\\[")
    return f"{prefix}[{key_color}]{key}[/]: [{value_color}]{value}[/]"


def print_key_value(
    console: console.Console,
    key: str,
    value: str,
    prefix: str = "",
    key_color="keyname",
    value_color="white",
) -> None:
    output = format_key_value(key, value, prefix, key_color, value_color)
    console.print(output, highlight=False)
