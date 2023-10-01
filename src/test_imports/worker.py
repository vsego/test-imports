"""
The main class for imports testing.
"""

from collections.abc import Sequence
from contextlib import ContextDecorator
import sys
from types import ModuleType, TracebackType
from typing import Type, cast, Generator, Self, Any

from .exceptions import (
    TestImportsPatchedError, TestImportsUnpatchedError,
)
from .states import BootstrapState, BootstrapStates
from .types import (
    T_import, T_input_modules, T_input_hide_modules, T_input_modules_mapping,
    T_modules_sequence, T_modules_mapping,
)
from .utils import check_exception, raise_exception, normalize_name


_UNDEF = object()


class TestImportsWorker(ContextDecorator):
    """
    The main class for imports testing.
    """

    def __init__(
        self,
        *,
        fail_modules: T_input_modules | None = None,
        sub_modules: T_input_modules_mapping | None = None,
        hide_modules: T_input_hide_modules | None = None,
        fail_exception: Exception | Type[Exception] = ModuleNotFoundError,
        sub_module_reload: bool = False,
        debug: bool = False,
    ) -> None:
        self._created: bool = False
        if not (fail_modules or sub_modules):
            raise ValueError(
                "missing the names of the modules to fail or substitute",
            )
        self.fail_modules = self._normalize_sequence(fail_modules)
        self.sub_modules: T_modules_mapping = self._normalize_mapping(
            sub_modules,
        )
        self.hide_modules: T_modules_sequence = self._normalize_sequence(
            hide_modules,
        )
        check_exception(fail_exception)
        self.fail_exception = cast(Exception | Type[Exception], fail_exception)
        self.sub_module_reload = sub_module_reload
        self._state: BootstrapState | None = None
        self.debug = debug
        self._created = True

    def _debug(self, *args: Any) -> None:
        """
        Print `args` if `self.debug` is `True`.
        """
        if self.debug:
            print("DEBUG:", *args)

    @classmethod
    def _normalize_sequence(
        cls, sequence: T_input_modules | T_input_hide_modules | None,
    ) -> T_modules_sequence:
        """
        Return normalized `sequence`.

        For details, see :py:func:`.utils.normalize_name`.
        """
        if sequence is None:
            return tuple()
        else:
            return tuple(normalize_name(item) for item in sequence)

    @classmethod
    def _normalize_mapping(
        cls, modules_mapping: T_input_modules_mapping | None,
    ) -> T_modules_mapping:
        """
        Return normalized `modules_mapping`.

        For details, see :py:func:`.utils.normalize_name`.
        """
        if modules_mapping is None:
            return dict()
        else:
            return {
                normalize_name(key): value
                for key, value in modules_mapping.items()
            }

    def is_fail_match(self, name: str) -> bool:
        """
        Return `True` if `name` matches any of `self.fail_modules`.
        """
        return any(regex.match(name) for regex in self.fail_modules)

    def get_sub_match(self, name: str) -> str:
        """
        Return the name of the module that should be loaded instead of `name`.
        """
        try:
            substitute = next(
                substitute
                for regex, substitute in self.sub_modules.items()
                if regex.match(name)
            )
        except StopIteration:
            return name
        else:
            if isinstance(substitute, str):
                return substitute
            elif isinstance(substitute, ModuleType):
                return substitute.__name__
            else:
                raise TypeError(
                    f"substitute mappings can only be strings and modules (not"
                    f" {substitute!r}",
                )

    def fake_loaded_module_data(
        self,
        loaded_module: ModuleType,
        name: str,
        attrib_value: Any,
        import_: T_import,
    ) -> None:
        """
        Fake the data in `loaded_module` to appear as if it was named `name`.
        """
        sys.modules[name] = loaded_module
        if loaded_module.__name__ == name:
            # Nothing to do.
            return

        if loaded_module.__spec__ and loaded_module.__spec__.parent:
            loaded_parent = sys.modules[loaded_module.__spec__.parent]
            module_name = loaded_module.__name__.rpartition(".")[-1]
            if attrib_value is _UNDEF:
                delattr(loaded_parent, module_name)
            else:
                setattr(loaded_parent, module_name, attrib_value)

        fake_parent_name, _, fake_module_name = name.rpartition(".")

        if fake_parent_name:
            fake_parent_module = self.wrapper_find_and_load(
                fake_parent_name, import_,
            )
            setattr(fake_parent_module, fake_module_name, loaded_module)
        loaded_module.__name__ = fake_module_name
        if loaded_module.__spec__:
            loaded_module.__spec__.name = name

    def expand_fromlist(
        self, module: ModuleType, fromlist: Sequence[str],
    ) -> Generator[str, None, None]:
        """
        Return generator of items imported with `from module import fromlist`.
        """
        module_name = module.__name__
        for name in fromlist:
            if name == "*":
                try:
                    yield from (
                        f"{module_name}.{obj_name}"
                        for obj_name in module.__all__
                    )
                except AttributeError:
                    yield from (
                        f"{module_name}.{obj_name}"
                        for obj_name in dir(module)
                        if not obj_name.startswith("_")
                    )
            else:
                yield f"{module_name}.{name}"

    def get_fromlist_matches(
        self, module: ModuleType, fromlist: Sequence[str],
    ) -> Generator[str, None, None]:
        """
        Return generator of names imported with `from module import fromlist`.

        :param module: A module, d'oh.
        :param fromlist: A list of imports from `module`.
        :return: A generator of absolute import names from the expression
            `from module import fromlist` that match the fail-module criteria
            from the constructor.
        """
        return (
            name
            for name in self.expand_fromlist(module, fromlist)
            if self.is_fail_match(name)
        )

    def get_attrib(self, name: str, import_: T_import) -> object:
        """
        Return attribute defined by `name` or `_UNDEF` if there isn't one.

        When loading `package.module` and then renaming it to
        `fake_package.module`, the original value of the attribute `module` in
        `package` (which may have been imported somewhere) can be overwritten
        and we need to make sure that it's reset while setting up the mock.
        This method grabs it (if it exists) and then its return value is used
        in :py:meth:`wrapper_find_and_load` to set it back to the original
        value (if there was one).
        """
        if self._state is None:
            raise TestImportsUnpatchedError("not patched")  # pragma: no cover
        parent_name, _, module_name = name.rpartition(".")
        if parent_name:
            module = self._state.original_find_and_load(parent_name, import_)
            return getattr(module, module_name, _UNDEF)
        else:
            return _UNDEF

    def wrapper_find_and_load(
        self, name: str, import_: T_import,
    ) -> ModuleType:
        """
        Patch for :py:func:`importlib._bootstrap._find_and_load`.
        """
        self._debug(
            f"{type(self).__name__}.wrapper_find_and_load("
            f"{name!r}, {import_!r})",
        )

        if self._state is None:
            raise TestImportsUnpatchedError("not patched")  # pragma: no cover
        if self.is_fail_match(name):
            raise_exception(self.fail_exception, name)

        name_to_load = self.get_sub_match(name)
        attrib_value = _UNDEF
        if name != name_to_load:
            attrib_value = self.get_attrib(name_to_load, import_)
        modules_value = sys.modules.get(name_to_load, _UNDEF)

        existing_module: ModuleType | None = None
        if self.sub_module_reload or self._state.is_hidden(name_to_load):
            existing_module = sys.modules.pop(name_to_load, None)

        result = self._state.original_find_and_load(name_to_load, import_)

        if existing_module is not None:
            sys.modules[name_to_load] = existing_module
        if modules_value is _UNDEF:
            sys.modules.pop(name_to_load, None)
        elif isinstance(modules_value, ModuleType):
            sys.modules[name_to_load] = modules_value

        self.fake_loaded_module_data(result, name, attrib_value, import_)

        return result

    def wrapper_handle_fromlist(
        self,
        module: ModuleType,
        fromlist: Sequence[str],
        import_: T_import,
        *,
        recursive: bool = False,
    ) -> ModuleType:
        """
        Patch for :py:func:`importlib._bootstrap._handle_fromlist`.
        """
        self._debug(
            f"{type(self).__name__}.wrapper_handle_fromlist("
            f"{module!r}, {fromlist!r}, {import_!r}, recursive={recursive})",
        )
        if self._state is None:
            raise TestImportsUnpatchedError("not patched")  # pragma: no cover

        try:
            name = next(self.get_fromlist_matches(module, fromlist))
        except StopIteration:
            pass
        else:
            raise_exception(self.fail_exception, name)

        return self._state.original_handle_fromlist(
            module, fromlist, import_, recursive=recursive,
        )

    def patch(self, *, strict: bool = True) -> bool:
        """
        Patch the import system.

        :param strict: If `True`, raise `TestImportsPatchedError` when
            patching an already patched instance.
        """
        hide_modules = (
            self.fail_modules + tuple(self.sub_modules) + self.hide_modules
        )
        if self._state is None:
            self._state = BootstrapStates.patch(
                self.wrapper_find_and_load,
                self.wrapper_handle_fromlist,
                hide_modules,
            )
            self._debug(repr(self._state))
            return True
        else:
            if strict:
                raise TestImportsPatchedError("already patched")
            else:
                return False

    def unpatch(self, *, strict: bool = True) -> bool:
        """
        Unpatch the import system.

        :param strict: If `True`, raise `TestImportsUnpatchedError` when
            unpatching a non-patched instance.
        """
        if self._state is None:
            if strict:
                raise TestImportsUnpatchedError("not patched")
            else:
                return False
        else:
            BootstrapStates.unpatch(self._state)
            self._state = None
            return True

    def __enter__(self) -> Self:
        """
        Enable the use of this class as a context manager.
        """
        self.patch()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """
        Reset the old state when exiting context.
        """
        self.unpatch()

    def __del__(self) -> None:
        """
        Unpatch when garbage-collected.

        Do not rely on this and do your own cleanup instead!
        """
        if getattr(self, "_created", False):
            self.unpatch(strict=False)
