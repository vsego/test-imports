"""
Exceptions specific to this package.
"""


class TestImportsError(Exception):
    """
    Base exception for other exceptions specific to this package.
    """


class TestImportsRevertError(TestImportsError):
    """
    Exception raised when `BootstrapState.revert` is called for inactive state.
    """


class TestImportsPatchingError(TestImportsError):
    """
    Base exception for patching exceptions.
    """


class TestImportsPatchedError(TestImportsPatchingError):
    """
    Exception raised when `FailImports.patch` is (re)used on patched system.
    """


class TestImportsUnpatchedError(TestImportsPatchingError):
    """
    Exception raised when `FailImports.unpatch` is used on non-patched system.
    """
