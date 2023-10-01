"""
Common custom types used by the package.
"""

from collections.abc import Sequence, Mapping
from types import ModuleType
from typing import TypeAlias, Pattern, Type, Callable

from mypy_extensions import DefaultNamedArg


T_module: TypeAlias = ModuleType | str
T_input_module: TypeAlias = Pattern | str
T_input_modules: TypeAlias = Sequence[T_input_module]
T_input_hide_module: TypeAlias = Pattern | str | ModuleType
T_input_hide_modules: TypeAlias = Sequence[T_input_module | ModuleType]
T_input_modules_mapping: TypeAlias = Mapping[T_input_module, T_module]
T_modules_sequence: TypeAlias = tuple[Pattern, ...]
T_modules_mapping: TypeAlias = Mapping[Pattern, T_module]
T_exception: TypeAlias = Exception | Type[Exception]

T_import_vars: TypeAlias = Mapping[str, object] | None
T_import: TypeAlias = Callable[
    [str, T_import_vars, T_import_vars, Sequence[str], int],
    ModuleType,
]
T_find_and_load: TypeAlias = Callable[[str, T_import], ModuleType]
T_handle_fromlist: TypeAlias = Callable[
    [
        ModuleType,
        Sequence[str],
        T_import,
        DefaultNamedArg(bool, "recursive"),  # noqa: E0602
    ],
    ModuleType,
]
