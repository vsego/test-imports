"""
Interface functions for the worker class.
"""

from typing import Any, cast

from .types import (
    T_input_module, T_input_hide_modules, T_exception, T_input_modules_mapping,
)
from .utils import (
    pop_hide_modules, pop_bool, check_no_extra_kwargs, kwargs_to_sub_modules,
)
from .worker import TestImportsWorker


def fail_imports(
    *modules: T_input_module,
    hide_modules: T_input_hide_modules | None = None,
    exception: T_exception = ModuleNotFoundError,
    debug: bool = False,
) -> TestImportsWorker:
    """
    Return decorator / context manager for failing imports.

    :param modules: A list of strings or compiled regular expressions matching
        the modules that need to fail when their import is attempted.
    :param hide_modules: A sequence of strings, regular expressions, or modules
        to be hidden (removed from `sys.modules`). These will be put back in
        once the decorated function ends or the context manager exists.
    :param exception: A class or an instance of the exception to be raised when
        an import is failed by this decorator / context manager.
    :param debug: If `True`, some extra output is added, in order to allow
        easier debugging of failed modules.
    :return: Decorator or context manager used to fail import of `modules`.
    """
    return TestImportsWorker(
        fail_modules=modules,
        hide_modules=hide_modules,
        fail_exception=exception,
        debug=debug,
    )


def mock_imports(
    prefix: str = "TI_", dot: str = "__", /, **kwargs: Any,
) -> TestImportsWorker:
    """
    Return decorator / context manager for mocking imports.

    To make it simple to use, this function takes mocks as keyword-only
    arguments. For example, `mock_imports(PIL=="mock_pil")` will cause Python
    to load `mock_pil` every time `import PIL` is encountered.

    However, this limits the use of keyword arguments. For example, there is a
    package [debug](https://pypi.org/project/debug/), which we could not mock
    if it was used as a keyword argument to turn on debugging outputs.

    Another problem is that full module names can have dots (for example:
    `PIL.Image`). Obviously we cannot do `mock(PIL.Image="mock_pil_image")`, so
    we replace dots with double underscores (as in Django), i.e., this mock
    would be defined as `mock(PIL__Image="mock_pil_image")`. However, in theory
    at least, `"__"` could be used in some module name (existing or future) and
    cause issues.

    To overcome these problems, this function takes two positional-only
    arguments:

    :param prefix: A prefix for keyword-only arguments that are recognised by
        this function. For example, if `prefix` is set to its default version
        `"TI_"`, then the debugging value is assigned as `TI_debug`. Any names
        beginning with `"TI_"` that are not recognised as arguments are
        considered invalid. In other words, if you want to mock a module name,
        for example, `TI_module`, you need to change this prefix to something
        else and adjust keyword-arguments accordingly.
    :param dot: A string used instead of dot in module names.

    So, these two calls are equivalent:

    ```
    mock_imports(PIL__Image="mock_pil_image", TI_debug=True)
    # and
    mock_imports(
        "PFX_", "__xxx__", PIL__xxx__Image="mock_pil_image", PFX_debug=True,
    )
    ```

    Notice that this format disallows matching by regular expressions or by
    strings containing asterisks. This makes sense, because matching multiple
    similarly named modules with the single (same!) one hardly makes sense.
    However, if you're hellbent on doing it, you can use a bit of Python
    trickery: `mock_imports(**{"tests.module*": math})` will load `math`
    instead of any module with a full name beginning with `"tests.module"`.

    The keyword-only arguments are as follows (always prefix their names with
    `prefix`!):

    :param hide_modules: A sequence of strings, regular expressions, or modules
        to be hidden (removed from `sys.modules`). These will be put back in
        once the decorated function ends or the context manager exists.
    :param reload: If `True`, every imported module or its mock is reloaded on
        import. Depending on how they are written, this may help reset mocked
        modules from previous tests.
    :param debug: If `True`, some extra output is added, in order to allow
        easier debugging of failed modules.
    :return: Decorator or context manager used to mock import of modules.
    """
    hide_modules = pop_hide_modules(prefix, kwargs)
    reload = pop_bool("reload", prefix, kwargs)
    debug = pop_bool("debug", prefix, kwargs)

    check_no_extra_kwargs(prefix, kwargs)
    sub_modules = kwargs_to_sub_modules(dot, kwargs)

    return TestImportsWorker(
        sub_modules=cast(T_input_modules_mapping, sub_modules),
        hide_modules=hide_modules,
        sub_module_reload=reload,
        debug=debug,
    )
