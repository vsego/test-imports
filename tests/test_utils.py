import re
import string
from typing import Pattern
from test_imports.utils import (
    check_exception, raise_exception, normalize_name, str_to_pattern,
    pop_bool, pop_hide_modules, check_no_extra_kwargs, kwargs_to_sub_modules,
)

from .utils import TestsBase


class TestException(Exception):
    pass


class TestUtils(TestsBase):

    def test_check_exception(self) -> None:
        check_exception(TestException)
        check_exception(TestException())

    def test_check_exception_fail(self) -> None:
        with self.assertRaises(TypeError):
            check_exception(object)
        with self.assertRaises(TypeError):
            check_exception(object())

    def test_raise_exception(self) -> None:
        with self.assertRaises(TestException):
            raise_exception(TestException)
        with self.assertRaises(TestException):
            raise_exception(TestException())

    def test_raise_exception_fail(self) -> None:
        with self.assertRaises(TypeError):
            raise_exception(object)
        with self.assertRaises(TypeError):
            raise_exception(object())

    def test_normalize_name_str(self) -> None:
        test_name = "nomen_est_omen"
        result = normalize_name(test_name)
        self.assertTrue(isinstance(result, Pattern))
        self.assertEqual(result.pattern, test_name + "$")

    def test_normalize_name_star_str(self) -> None:
        test_name = "nomen_*_omen*"
        expected = r"nomen_.*_omen.*$"
        result = normalize_name(test_name)
        self.assertTrue(isinstance(result, Pattern))
        self.assertEqual(result.pattern, expected)

    def test_normalize_name_star_module(self) -> None:
        import tests.module5
        test_name = tests.module5
        expected = r"tests\.module5$"
        result = normalize_name(test_name)
        self.assertTrue(isinstance(result, Pattern))
        self.assertEqual(result.pattern, expected)

    def test_normalize_name_pattern(self) -> None:
        test_pattern = re.compile("nomen_est_omen")
        result = normalize_name(test_pattern)
        self.assertTrue(result is test_pattern)

    def test_normalize_name_junk(self) -> None:
        with self.assertRaises(TypeError):
            normalize_name(object())

    def test_str_to_pattern(self) -> None:
        result = str_to_pattern("omen--est--nomen", dot="--")
        expected = r"omen\.est\.nomen$"
        self.assertTrue(isinstance(result, Pattern))
        self.assertEqual(result.pattern, expected)

    def test_pop_bool(self) -> None:
        for value in (True, False, object()):
            kwargs = {"nomen_est_omen": value, "foo": "bar"}
            result = pop_bool("nomen_est_omen", "", kwargs)
            self.assertEqual(result, bool(value), f"value: {value!r}")
            self.assertEqual(kwargs, {"foo": "bar"})

    def test_pop_bool_prefix(self) -> None:
        for value in (True, False, object()):
            kwargs = {"pfx_nomen_est_omen": value, "foo": "bar"}
            result = pop_bool("nomen_est_omen", "pfx_", kwargs)
            self.assertEqual(result, bool(value), f"value: {value!r}")
            self.assertEqual(kwargs, {"foo": "bar"})

    def test_pop_hide_modules(self) -> None:
        import tests.module2
        re_module3 = re.compile(r"tests\.module3")
        modules = ["tests.module1", tests.module2, re_module3]
        kwargs = {"hide_modules": modules, "foo": "bar"}
        result = pop_hide_modules("", kwargs)
        self.assertTrue(result is modules)
        self.assertEqual(kwargs, {"foo": "bar"})

    def test_pop_hide_modules_wrong_type(self) -> None:
        with self.assertRaises(TypeError):
            pop_hide_modules("", {"hide_modules": object()})
        with self.assertRaises(TypeError):
            pop_hide_modules("", {"hide_modules": [object()]})

    def test_check_no_extra_kwargs(self) -> None:
        kwargs = {key: "" for key in string.ascii_letters}

        # `s.startswith("")` is `True` for all strings, so make sure to not get
        # a false positive here.
        check_no_extra_kwargs("", kwargs)

        # Normal usage, no problem.
        check_no_extra_kwargs("pfx_", kwargs)

        # Two items starting with the prefix _are_ a problem.
        kwargs["pfx_bad1"] = ""
        kwargs["pfx_bad2"] = ""
        with self.assertRaises(ValueError) as context:
            check_no_extra_kwargs("pfx_", kwargs)
        self.assertEqual(
            str(context.exception),
            "invalid arguments starting with prefix 'pfx_': 'pfx_bad1',"
            " 'pfx_bad2'",
        )

    def test_kwargs_to_sub_modules_ok(self) -> None:
        result = kwargs_to_sub_modules(
            "__",
            {
                # Don't process `"__"` in target.
                "math": "fake__math",
                # Correctly process the module to be replaced, but subbing
                # `"__"` with `.` and then converting it all to a regular
                # expression with joker `"*"` replaced by `".*"`.
                "tests__module*": "one_mock_to_rule_them_all",
            },
        )
        expected = {
            re.compile(r"math$"): "fake__math",
            re.compile(r"tests\.module.*$"): "one_mock_to_rule_them_all",
        }
        self.assertEqual(result, expected)

    def test_kwargs_to_sub_modules_fail_type(self) -> None:
        with self.assertRaises(TypeError):
            kwargs_to_sub_modules("__", ["foo", "bar"])
        with self.assertRaises(TypeError):
            kwargs_to_sub_modules("__", {"foo": object()})
