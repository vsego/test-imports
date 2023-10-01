import sys

from test_imports import mock_imports, TestImportsWorker

from .utils import TestsBase


class TestMockImports(TestsBase):

    def test_mock_inside_package(self) -> None:
        with mock_imports(tests__module5="tests.module1"):
            import tests.module5
            self.assertEqual(tests.module5.FOO, 17)

    def test_mock_between_packages(self) -> None:
        from html.parser import HTMLParser
        with mock_imports(tests__module5="html.parser"):
            import tests.module5
            self.assertTrue(tests.module5.HTMLParser is HTMLParser)
            self.assertEqual(tests.module5.__spec__.parent, "tests")

    def test_parentless_mock(self) -> None:
        import string
        expected = string.ascii_letters
        with mock_imports(math="string"):
            import math
            self.assertEqual(math.ascii_letters, expected)
            with self.assertRaises(AttributeError):
                math.sin

    def test_do_not_delete_original(self) -> None:
        # This one is a bit complicated.
        # What happens here is loading `html.parser` instead of another module
        # (`math`). Normally, this would mean:
        # 1. Load `html.parser`, which - among other things - loads `html` if
        #    needed and creates its attribute `parser`.
        # 2. Fake the data in `parser` to pretend that it's `math`.
        # 3. Remove it from `html`, because it was not supposed to be loaded
        #    there.
        # This creates a problem if `html.parser` was loaded before because now
        # `parser` no longer exists in `html`. Note that `html.parser` would
        # still be in `sys.modules` and packages that already imported it would
        # not be reimporting it, this failing to use it. Consider this in some
        # module:
        #   import html.parser
        #   f():
        #       print(html.parser.HTMLParser.__name__)
        # This usually works fine. However, if `parser` is deleted from `html`
        # (as an attribute), then calling `f()` will fail because it doesn't
        # reload `html.parser`.
        # The worker accounts for this scenario by grabbing the attribute
        # `parser` of module `html` (if they exist) before mocking, and then
        # reinstating it instead of deleting it (or leaving whatever the
        # importing code put there (which would be `html.parser` module).

        def cleanup():
            try:
                delattr(sys.modules["html"], "parser")
            except Exception:
                pass
            sys.modules.pop("html", None)
            sys.modules.pop("html.parser", None)

        # Test the original import (i.e., legit `html.parser`).
        cleanup()
        import html.parser
        HTMLParser = html.parser.HTMLParser
        with mock_imports(math="html.parser"):
            import math
            self.assertTrue(math.HTMLParser is HTMLParser)
            self.assertTrue(html.parser.HTMLParser is HTMLParser)

        # Test the same, but `html.parser` was manually assigned a value, which
        # we want preserved because the mocker should not interfere with the
        # stuff that it's loading under a different name.
        # You really shouldn't do this to your code, but we're enduring that
        # the mocker behaves nicely even if you do.
        cleanup()
        import html.parser
        HTMLParser = html.parser.HTMLParser

        # Overwrite `html.parser`. This test is making sure that this
        # particular override is not overwritten by the process of mocking the
        # import of `html.parser` as an unrelated module (`math`). In other
        # words, even though the process of loading `html.parser` might reset
        # it to the actual module, we want it to stay `"FOO"`.
        html.parser = "FOO"

        with mock_imports(math="html.parser"):
            import math
            self.assertTrue(math.HTMLParser is HTMLParser)
            self.assertEqual(html.parser, "FOO")

        # And what if the attribute doesn't exist? It should keep not existing!
        delattr(html, "parser")
        sys.modules.pop("html.parser", None)

        with mock_imports(math="html.parser"):
            import math
            self.assertFalse(hasattr(html, "parser"))

    def test_sub_with_module(self) -> None:
        with mock_imports(math=sys):
            import math
            self.assertTrue(math.modules is sys.modules)

    def test_sub_with_module_reload(self) -> None:
        import tests.module5
        tests.module5.FOO = 23

        with mock_imports(math="tests.module5", TI_reload=False):
            import math
            self.assertEqual(math.FOO, 23)

        with mock_imports(math="tests.module5", TI_reload=True):
            import math
            self.assertEqual(math.FOO, 19)

    def test_swap(self) -> None:
        # Why not? :-D
        with mock_imports(math="string", string="math"):
            import math
            import string
            self.assertEqual(math.digits, "0123456789")
            self.assertEqual(string.sin(0), 0)

    def test_fromlist(self) -> None:
        sys.modules.pop("html.parser", None)
        sys.modules.pop("html", None)
        import math
        with mock_imports(html__parser="math", TI_reload=True):
            from html import parser
            self.assertEqual(parser.sin(0), math.sin(0))

    def test_invalid_type(self) -> None:
        with self.assertRaises(TypeError):
            with TestImportsWorker(sub_modules=dict(math=object())):
                import math  # noqa: W0611
