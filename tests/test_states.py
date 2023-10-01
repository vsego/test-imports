# NOTE: Most of the states' functionality is tasted in `fail_impots.py`. The
# tests here only focus on fringe cases that don't occur much - if ever - in
# the main code.

import re

from test_imports import (
    BootstrapState, BootstrapStates, TestImportsRevertError,
)

from .utils import TestsBase


class TestException(Exception):
    pass


class TestStates(TestsBase):

    def test_revert_inactive_state(self) -> None:
        state = BootstrapState([re.compile("some_module")])
        state.revert()
        with self.assertRaises(TestImportsRevertError):
            state.revert()

    def test_unpatch_nonexistent_state(self) -> None:
        foo_state = BootstrapState([re.compile("foo")])
        BootstrapStates._states.append(foo_state)

        # Try to unpatch a state that does not exist. This should fail silently
        # because the state may have been legitimately reverted if another,
        # older one, was already reverted manually.
        BootstrapStates.unpatch(BootstrapState([re.compile("bar")]))

        # Still only one state (so, nothing was unpatched).
        self.assertTrue(len(BootstrapStates._states) == 1)
        # And that one state is "foo".
        self.assertTrue(BootstrapStates._states[0] is foo_state)
        BootstrapStates._states.clear()
