"""
Testing utilities.
"""

import re
import sys

from test_imports.states import BootstrapStates

import unittest


class TestsBase(unittest.TestCase):
    """
    The base unit tests class, used as a foundation for all other unit tests.
    """

    def clear_modules(self) -> None:
        """
        Clear all `tests.modules*` from `sys.modules` cache.
        """
        test_modules = [
            name for name in sys.modules if re.match(r"tests.module\d+$", name)
        ]
        for name in test_modules:
            del sys.modules[name]

    def setUp(self) -> None:
        """
        Clear `sys.modules` cache, so that each test ignores previous imports.
        """
        self.clear_modules()

    def tearDown(self) -> None:
        """
        Check that the worker cleaned up after itself.
        """
        try:
            self.assertFalse(
                bool(BootstrapStates._states),
                "States should be cleaned up after we're done with patching",
            )
        except Exception:
            BootstrapStates.clear()
            raise
