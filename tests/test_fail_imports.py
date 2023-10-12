import io
import os
import re
import sys
import unittest.mock

from test_imports import (
    fail_imports, TestImportsWorker, TestImportsPatchedError,
    TestImportsUnpatchedError,
)
from test_imports.states import BootstrapStates

from .utils import TestsBase


class TestException(Exception):
    pass


class TestFailImports(TestsBase):

    # Set `debug` to `True` if you need help fixing tests or just tracing what
    # is happening.
    kwargs = {
        "exception": TestException,
        "debug": False,
        "hide_modules": ("tests.module*",),
    }

    def test_context_manager(self) -> None:
        import tests.module1
        with fail_imports("tests.module1", **self.kwargs):
            with self.assertRaises(TestException):
                import tests.module1  # noqa: W0611

    def test_context_manager_hide_modules_str(self) -> None:
        # hide_modules should be a sequence of strings, but it's an easy enough
        # mistake to make it a string, so we try to account for that.
        import math  # noqa: W0611
        self.assertTrue("math" in sys.modules)
        with fail_imports("tests.module1", hide_modules="tests.module*"):
            # Without treating this right, we'd hide `["t", "e",..., "*"]` and
            # this would've hidden `math`.
            self.assertTrue("math" in sys.modules)

    def test_context_manager_no_names(self) -> None:
        with self.assertRaises(ValueError):
            with fail_imports():
                pass

    def test_context_manager_wrong_name_type(self) -> None:
        with self.assertRaises(TypeError):
            with fail_imports(object()):
                pass

    def test_context_manager_regex(self) -> None:
        import tests.module1
        with fail_imports(re.compile(r"tests\.module\d$"), **self.kwargs):
            with self.assertRaises(TestException):
                import tests.module1  # noqa: W0611
            with self.assertRaises(TestException):
                import tests.module2  # noqa: W0611
            with self.assertRaises(TestException):
                import tests.module3  # noqa: W0611

    def test_context_manager_from(self) -> None:
        from . import module1
        with fail_imports("tests.module1", **self.kwargs):
            with self.assertRaises(TestException):
                from . import module1  # noqa: W0611

    def test_context_manager_nosys(self) -> None:
        sys.modules.pop("tests.module1", None)
        with fail_imports("tests.module1", **self.kwargs):
            with self.assertRaises(TestException):
                import tests.module1  # noqa: W0611

    def test_context_manager_nosys_from(self) -> None:
        sys.modules.pop("tests.module1", None)
        with fail_imports("tests.module1", **self.kwargs):
            with self.assertRaises(TestException):
                from . import module1  # noqa: W0611

    def test_context_manager_nosys_from_all(self) -> None:
        sys.modules.pop("tests.module1", None)
        with fail_imports("tests.module1", **self.kwargs):
            with self.assertRaises(TestException):
                from . import module2  # noqa: W0611

    def test_context_manager_submodule_from1(self) -> None:
        with fail_imports("tests.module1", **self.kwargs):
            with self.assertRaises(TestException):
                from .module2 import module1  # noqa: W0611

    def test_context_manager_submodule_from2(self) -> None:
        sys.modules.pop("tests.module1", None)
        from .module2 import module1  # noqa: W0611
        with fail_imports("tests.module1", **self.kwargs):
            with self.assertRaises(TestException):
                from .module2 import module1  # noqa: W0611

    def test_context_manager_submodule_star(self) -> None:
        with fail_imports("tests.module1", **self.kwargs):
            with self.assertRaises(TestException):
                import tests.module3  # noqa: W0611

    def test_context_manager_submodule_all(self) -> None:
        with fail_imports("tests.module1", **self.kwargs):
            with self.assertRaises(TestException):
                import tests.module4  # noqa: W0611
        with fail_imports("tests.module2", **self.kwargs):
            with self.assertRaises(TestException):
                import tests.module4  # noqa: W0611

    def test_context_manager_submodule_func(self) -> None:
        with fail_imports("tests.module1", **self.kwargs):
            import tests.module5
            with self.assertRaises(TestException):
                tests.module5.f()

    def test_context_manager_submodules(self) -> None:
        with fail_imports("os", **self.kwargs):
            with self.assertRaises(TestException):
                import os  # noqa: W0611
            with self.assertRaises(TestException):
                import os.path  # noqa: W0611

        with fail_imports("os.*", **self.kwargs):
            import os  # noqa: W0611
            with self.assertRaises(TestException):
                import os.path  # noqa: W0611

    def test_decorator(self) -> None:
        @fail_imports("tests.module1", **self.kwargs)
        def f() -> None:
            import tests.module1  # noqa: W0611

        import tests.module1  # noqa: W0611
        with self.assertRaises(TestException):
            f()

    def test_context_manager_debug(self) -> None:
        kwargs = dict(**self.kwargs)
        kwargs["debug"] = True
        regex = (
            r"DEBUG: BootstrapState\(<bound method"
            r" TestImportsWorker.wrapper_find_and_load of"
            r" <test_imports.worker.TestImportsWorker object at 0x[0-9a-f]+>>,"
            r" <bound method TestImportsWorker.wrapper_handle_fromlist of"
            r" <test_imports.worker.TestImportsWorker object at"
            r" 0x[0-9a-f]+>>\)" + "\n"
        )

        with unittest.mock.patch(
            "sys.stdout", new_callable=io.StringIO,
        ) as mock_stdout:
            with fail_imports("tests.module1", **kwargs):
                pass

        self.assertTrue(re.match(regex, mock_stdout.getvalue()))

        kwargs["debug"] = False

        with unittest.mock.patch(
            "sys.stdout", new_callable=io.StringIO,
        ) as mock_stdout:
            with fail_imports("tests.module1", **kwargs):
                pass

        self.assertEqual(mock_stdout.getvalue(), "")

    def test_context_manager_debug_import(self) -> None:
        expected = (
            "DEBUG: TestImportsWorker.wrapper_find_and_load("
            "'tests.module1', <built-in function __import__>)\n"
        )

        with fail_imports("tests.module1", **self.kwargs) as fi:
            with unittest.mock.patch(
                "sys.stdout", new_callable=io.StringIO,
            ) as mock_stdout:
                fi.debug = True
                with self.assertRaises(TestException):
                    import tests.module1  # noqa: W0611

        self.assertEqual(mock_stdout.getvalue(), expected)

        with fail_imports("tests.module1", **self.kwargs) as fi:
            with unittest.mock.patch(
                "sys.stdout", new_callable=io.StringIO,
            ) as mock_stdout:
                fi.debug = False
                with self.assertRaises(TestException):
                    import tests.module1  # noqa: W0611

        self.assertEqual(mock_stdout.getvalue(), "")

    def test_context_manager_debug_from_import(self) -> None:
        regex = (
            r"DEBUG: TestImportsWorker.wrapper_handle_fromlist\(<module"
            r" 'tests' from '.*?" + os.sep + r"__init__.py'>,"
            r" \('module1',\), <built-in function __import__>,"
            r" recursive=False\)" + "\n"
        )

        with fail_imports("tests.module1", **self.kwargs) as fi:
            with unittest.mock.patch(
                "sys.stdout", new_callable=io.StringIO,
            ) as mock_stdout:
                fi.debug = True
                with self.assertRaises(TestException):
                    from tests import module1  # noqa: W0611

        self.assertTrue(re.match(regex, mock_stdout.getvalue()))

        with fail_imports("tests.module1", **self.kwargs) as fi:
            with unittest.mock.patch(
                "sys.stdout", new_callable=io.StringIO,
            ) as mock_stdout:
                fi.debug = False
                with self.assertRaises(TestException):
                    from tests import module1  # noqa: W0611

        self.assertEqual(mock_stdout.getvalue(), "")

    def test_patch(self) -> None:
        fi = fail_imports("tests.module1", **self.kwargs)
        self.assertTrue(fi.patch())
        self.assertFalse(fi.patch(strict=False))
        with self.assertRaises(TestImportsPatchedError):
            fi.patch(strict=True)
        self.assertEqual(len(BootstrapStates._states), 1)
        BootstrapStates.clear()

    def test_unpatch(self) -> None:
        fi = fail_imports("tests.module1", **self.kwargs)
        fi.patch()
        self.assertTrue(fi.unpatch())
        self.assertFalse(fi.unpatch(strict=False))
        with self.assertRaises(TestImportsUnpatchedError):
            fi.unpatch(strict=True)

    def test_patch_not_loaded_module(self) -> None:
        with fail_imports("tests.this_module_does_not_exist", **self.kwargs):
            pass

    def test_normalize_none_names(self) -> None:
        self.assertEqual(TestImportsWorker._normalize_sequence(None), tuple())

    def test_modules_removal(self) -> None:
        # Check that the matching modules loaded during the session (not
        # before!) still get removed from `sys.modules` when the session is
        # over.
        sys.modules.pop("tests.module1", None)
        sys.modules.pop("tests.module5", None)
        with fail_imports("tests.module1", **self.kwargs):
            import tests.module5  # noqa: W0611
            with self.assertRaises(TestException):
                import tests.module1  # noqa: W0611
            self.assertTrue("tests.module5" in sys.modules)
        self.assertTrue("tests.module5" not in sys.modules)

    def test_modules_nonremoval(self) -> None:
        # Check that the matching modules loaded during before the session do
        # not get removed from `sys.modules` when the session is over, even
        # though they are removed during the session (when in `hide_modules`
        # argument).
        sys.modules.pop("tests.module1", None)
        sys.modules.pop("tests.module5", None)
        import tests.module5  # noqa: W0611
        self.assertTrue("tests.module5" in sys.modules)
        with fail_imports("tests.module1", **self.kwargs):
            self.assertTrue("tests.module5" not in sys.modules)
            with self.assertRaises(TestException):
                import tests.module1  # noqa: W0611
            self.assertTrue("tests.module5" not in sys.modules)
        self.assertTrue("tests.module5" in sys.modules)
