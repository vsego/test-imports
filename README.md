# Test Python imports

A Python package for failing and mocking imports in automated tests.

**Note:** This package was made with CPython in mind. There are no guarantees that it will work with other versions.

## Content

1. [Failing imports](#failing-imports)
2. [Mocking imports](#mocking-imports)

## Failing imports

This was the original motive to create the package. I needed to test the behaviour of another package that had optional support for [`PIL`](https://python-pillow.org), and I wanted the tests to check the behaviour both when the package is present and when it is not.

The usage is straightforward:

```python
from test_imports import fail_imports


def f() -> bool:
    try:
        import PIL.Image
    except ImportError:
        return False
    else:
        return True


def test_success() -> None:
    assert f() is True


@fail_imports("PIL")
def test_decorator_fail() -> None:
    assert f() is False


def test_context_manager_fail() -> None:
    with fail_imports("PIL"):
        assert f() is False


test_success()
test_decorator_fail()
test_context_manager_fail()
```

All positional arguments in `fail_imports` are treated as the modules whose imports are to fail. Each of them can be:

* a compiled regular expression, matched (using `re.match`, i.e., anchored at the beginning of the string) against names of the modules being imported; or

* a string, which is matched literally, except for the asterisk, which is used to match any substring. The matching is done on complete strings.  
  For example, `"foo.bar*"` will match `foo.bar` and `foo.bard`, but not `foodbar` (because dot is matched literally, not as in regular expressions). Further, `"foo.*r"` will match `foo.bar`, but not `foo.bard` because only the whole strings are matched. If you want `foo.bard` to match, the expression needs to be `foo.*r*`, or you can supply a compiled regular expression that would match it.

This function also supports some customisation through keyword-only arguments:

* `hide_modules` is a sequence of module names matching patterns (as described above) that won't be failed, but will be removed from `sys.modules`, thus causing them to "reload". This helps test imports inside those modules because, if they are not "reloaded", their imports are not re-executed.

* `exception` is either a class or an instance of the exception to be raised when an import fails. Unsurprisingly, this defaults to `ModuleNotFoundError`.

* `debug` is a Boolean flag. If set to `True`, the package will produce extra prints in an attempt to help with its usage.

## Mocking imports

Like more "normal" mocking, the mocking of modules is used to replace one object with another one, pretending to be the original. On the surface, mocking imports is easy:

```python
from test_imports import mock_imports


def test_success() -> None:
    import math
    assert hasattr(math, "sin")
    assert not hasattr(math, "digits")


@mock_imports(math="string")
def test_decorator_fail() -> None:
    import math
    assert not hasattr(math, "sin")
    assert hasattr(math, "digits")


def test_context_manager_fail() -> None:
    with mock_imports(math="string"):
        import math
        assert not hasattr(math, "sin")
        assert hasattr(math, "digits")


test_success()
test_decorator_fail()
test_context_manager_fail()
```

However, mocking definitions are a bit more complicated than the ones for `fail_imports`.

First, there is a problem of mocking modules inside packages. One cannot do `fail_imports(PIL.Image="mock_pil_image")` because dots cannot be a part of arguments' names. Instead, we use double underscores (similar to, for example, Django):

```python
with mock_imports(PIL__Image="math"):
    from PIL import Image
    assert not hasattr(Image, "new")
    assert hasattr(Image, "sin")
```

There is also a potential problem of collisions in names between the function's arguments and mocked modules. For example, there is a package [debug](https://pypi.org/project/debug/), which we could not mock if `debug` was used as a keyword argument to turn on debugging outputs. That's why argument names are prefixed with `"TI_"` (so, `TI_debug=True` instead of `debug=True`).

Both of these can still cause potential conflicts. Some module can have double underscores in its name and some package's name could start with `TI_`. To account for these cases, `mock_imports` takes two positional-only arguments:

* `prefix` is the prefix for keyword-only arguments that are recognised by this function. For example, if `prefix` is set to its default version `"TI_"`, then the debugging value is assigned as `TI_debug`. Any names beginning with `"TI_"` that are not recognised as arguments are considered invalid.  
  In other words, if you want to mock a module with a name starting with `"TI_"` (for example, `TI_module`), you need to change this prefix to something else and adjust keyword-arguments accordingly.

* `dot` is the string used instead of dot in module names.

   So, these two calls are equivalent:

```python
mock_imports(PIL__Image="mock_pil_image", TI_debug=True)
# and
mock_imports(
    "PREFIX_", "__xxx__", PIL__xxx__Image="mock_pil_image", PREFIX_debug=True,
)
```

This still does not allow matching with asterisk or with regular expressions, but it would hardly make sense to do so (mocking multiple different modules with the same one). However, if really needed, one can use the following Python "trick":

```python
mock_imports(**{"tests.module*": math})
```

This will will load `math` instead of any module with a full name beginning with `"tests.module"`.

The remaining arguments are keyword only (always prefix their names with `prefix`!):

* `hide_modules` is as above: a sequence of module names matching patterns (as described above) that won't be failed, but will be removed from `sys.modules`, thus causing them to "reload". This helps test imports inside those modules because, if they are not "reloaded", their imports are not re-executed.

* `reload` is a Boolean flag. If `True`, every imported module or its mock is reloaded on import. Depending on how they are written, this may help reset mocked modules from previous tests.

* `debug` is a Boolean flag. If set to `True`, the package will produce extra prints in an attempt to help with its usage.
