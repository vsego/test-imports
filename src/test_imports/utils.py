"""
Utility functions.
"""

from collections.abc import Sequence, Mapping
import re
from types import ModuleType
from typing import Type, NoReturn, Pattern, Any, cast

from .types import (
    T_exception, T_input_module, T_input_hide_module, T_input_hide_modules,
    T_modules_mapping,
)


def check_exception(exception: T_exception) -> None:
    """
    Raise `TypeError` if `exception` is not an exception instance or class.
    """
    if (
        not (
            isinstance(exception, Exception)
            or issubclass(exception, Exception)
        )
    ):
        raise TypeError("exception must be an exception class or instance")


def raise_exception(
    exception: Exception | Type[Exception],
    message: str = "",
) -> NoReturn:
    """
    Raise exception `exception` with message `message`.

    :param exception: Exception class or instance to be raised.
    :param message: A message to be used when creating instance of `exception`.
        If `exception` is already an instance, `message` is ignored.
    """
    exc: Exception
    if isinstance(exception, Exception):
        exc = exception
    elif issubclass(exception, Exception):
        exc = exception(message)
    else:
        raise TypeError("exception must be an exception class or instance")
    raise exc


def normalize_name(name: T_input_module | T_input_hide_module) -> Pattern:
    """
    Return normalized `name` to be used as a matching regex for a module name.

    This package allows names matching by regular expressions, and thus saves
    them that way internally.

    If `name` is already a compiled regular expression, it is returned
    unchanged.

    If `name` is a module, its name (from its `__name__` attribute) is used
    instead.

    If `name` is a string, it is converted to a regular expression by applying
    these rules:
    1. Everything except `"*"` is matched literally.
    2. `"*"` matches any substring. For example, `"foo.b*r"` matches `foo.bar`,
       `foo.beer`, etc., but not `foodbar` because `"."` is interpreted
       literally.
    3. End anchor `$` is always added. If you want to avoid anchoring your
       search at the end, end `name` with `"*"`.
    """
    if isinstance(name, Pattern):
        return name

    if isinstance(name, ModuleType):
        name = name.__name__

    if isinstance(name, str):
        regex = ".*".join(re.escape(s) for s in name.split("*")) + "$"
        return re.compile(regex)
    else:
        raise TypeError(
            "name must be a compiled regex expression or a string",
        )


def str_to_pattern(name: str, *, dot: str) -> Pattern:
    """
    Return `name` converted to a compiled regex matching that name.

    Each substring `dot` is also replaced with a dot (`"."`), because these
    names come from keyword-only arguments that cannot contain actual dots.
    """
    return normalize_name(name.replace(dot, "."))


def pop_hide_modules(
    prefix: str, kwargs: dict[str, Any],
) -> T_input_hide_modules:
    """
    Pop and return properly cast `hide_modules` value from `kwargs`.

    This is an auxiliary function, used in :py:func:`interfaces.mock_imports`.
    """
    hide_modules_raw = kwargs.pop(f"{prefix}hide_modules", list())
    if (
        isinstance(hide_modules_raw, Sequence)
        and all(
            isinstance(value, Pattern | str | ModuleType)
            for value in hide_modules_raw
        )
    ):
        return cast(T_input_hide_modules, hide_modules_raw)
    else:
        raise TypeError(
            "hide_modules must be a sequence of values that are either"
            "strings, modules, or compiled regex patterns",
        )


def pop_bool(
    name: str, prefix: str, kwargs: dict[str, Any], *, default: bool = False,
) -> bool:
    """
    Pop and return properly cast value named `name` from `kwargs`.

    This is an auxiliary function, used in :py:func:`interfaces.mock_imports`.
    """
    return bool(kwargs.pop(f"{prefix}{name}", default))


def check_no_extra_kwargs(prefix: str, kwargs: dict[str, Any]) -> None:
    """
    Raise `ValueError` if `kwargs` has keys beginning with non-empty `prefix`.

    This is an auxiliary function, used in :py:func:`interfaces.mock_imports`.
    """
    if prefix:
        invalid_names = [
            repr(name) for name in kwargs if name.startswith(prefix)
        ]
        if invalid_names:
            raise ValueError(
                f"invalid arguments starting with prefix {prefix!r}:"
                f" {', '.join(invalid_names)}",
            )


def kwargs_to_sub_modules(
    dot: str, kwargs: dict[str, Any],
) -> T_modules_mapping:
    """
    Return `kwargs` properly converted to a modules mapping.

    This is an auxiliary function, used in :py:func:`interfaces.mock_imports`.
    """
    if (
        isinstance(kwargs, Mapping)
        and all(
            isinstance(value, ModuleType | str) for value in kwargs.values()
        )
    ):
        return cast(
            T_modules_mapping,
            {
                str_to_pattern(name, dot=dot): module
                for name, module in kwargs.items()
            },
        )
    else:
        raise TypeError(
            "modules substitutions must be either strings or loaded modules",
        )
