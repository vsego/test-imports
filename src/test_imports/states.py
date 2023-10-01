"""
Class for holding the states of `_find_and_load` and `_handle_fromlist`.
"""

import importlib._bootstrap  # type: ignore
import sys
from types import ModuleType
from typing import Sequence, Pattern, Final

from .exceptions import TestImportsRevertError
from .types import T_find_and_load, T_handle_fromlist


class BootstrapState:
    """
    Class for holding the states of `_find_and_load` and `_handle_fromlist`.
    """

    def __init__(self, module_regexes: Sequence[Pattern]) -> None:
        self._active = True
        self.original_find_and_load = importlib._bootstrap._find_and_load
        self.original_handle_fromlist = importlib._bootstrap._handle_fromlist
        self._module_regexes = module_regexes
        self._hidden_modules: dict[str, ModuleType] = dict()
        # Add removal of modules not in _hidden_modules when unpatching!
        self._hide_modules()

    def __repr__(self) -> str:
        class_name = type(self).__name__
        modules_str = ", ".join(sorted(self._hidden_modules))
        if modules_str:
            modules_str = f"; {modules_str}"
        fal = importlib._bootstrap._find_and_load
        hf = importlib._bootstrap._handle_fromlist
        return f"{class_name}({fal!r}, {hf!r}{modules_str})"

    def is_hidden(self, module_name: str) -> bool:
        """
        Return `True` if `module_name` is among hidden modules.
        """
        return module_name in self._hidden_modules

    def _get_matching_modules(self) -> set[str]:
        """
        Return a set of names in `sys.modules` matching some `_module_regexes`.
        """
        return {
            module_name
            for module_name in sys.modules
            if any(regex.match(module_name) for regex in self._module_regexes)
        }

    def _hide_modules(self) -> None:
        """
        Hide modules matching `self._module_regexes` from `sys.modules`.
        """
        for module_name in self._get_matching_modules():
            self._hidden_modules[module_name] = sys.modules.pop(module_name)

    def _unload_matching_modules(self) -> None:
        """
        Remove modules matching `self._module_regexes` from `sys.modules`.
        """
        for module_name in self._get_matching_modules():
            sys.modules.pop(module_name)

    def revert(self) -> None:
        """
        Revert the system to the state before the current one was applied.

        Calling this undoes the patch that created this state, as well as
        "unloading" mocked and hidden modules.
        """
        if not self._active:
            raise TestImportsRevertError(f"{self} already reverted")
        try:
            self._unload_matching_modules()
            sys.modules.update(self._hidden_modules)
            importlib._bootstrap._find_and_load = (
                self.original_find_and_load
            )
            importlib._bootstrap._handle_fromlist = (
                self.original_handle_fromlist
            )
        finally:
            self._active = False


class BootstrapStates:
    """
    Class for patching `_find_and_load` and keeping its old states.
    """

    _states: Final[list[BootstrapState]] = list()
    _original_find_and_load = importlib._bootstrap._find_and_load
    _original_handle_fromlist = importlib._bootstrap._handle_fromlist

    @classmethod
    def patch(
        cls,
        patch_find_and_load: T_find_and_load,
        patch_handle_fromlist: T_handle_fromlist,
        module_regexes: Sequence[Pattern],
    ) -> BootstrapState:
        """
        Patch `importlib._bootstrap.*` functions and return bootstrap state.
        """
        result = BootstrapState(module_regexes)
        cls._states.append(result)
        importlib._bootstrap._find_and_load = patch_find_and_load
        importlib._bootstrap._handle_fromlist = patch_handle_fromlist
        return result

    @classmethod
    def unpatch(cls, state: BootstrapState | None = None) -> None:
        """
        Undo patches from `state` to the last one.
        """
        try:
            index = 0 if state is None else cls._states.index(state)
        except ValueError:
            pass
        else:
            for st in reversed(cls._states[index:]):
                if st._active:
                    st.revert()
            del cls._states[index:]

    @classmethod
    def clear(cls) -> None:
        """
        Undo all the patches done since the creation of this class.
        """
        cls.unpatch()
        importlib._bootstrap._find_and_load = cls._original_find_and_load
        importlib._bootstrap._handle_fromlist = cls._original_handle_fromlist
