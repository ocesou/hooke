# Copyright

"""Define :func:`caller_name`.

This is useful, for example, to declare the `@callback` decorator for
making GUI writing less tedious.  See :mod:`hooke.util.callback` and
:mod:`hooke.ui.gui` for examples.
"""

import sys


def frame(depth=1):
    """Return the frame for the function `depth` up the call stack.

    Notes
    -----
    The `ZeroDivisionError` trick is from stdlib's traceback.py.  See
    the Python Refrence Manual on `traceback objects`_ and `frame
    objects`_.

    .. _traceback objects:
      http://docs.python.org/reference/datamodel.html#index-873
    .. _frame objects:
      http://docs.python.org/reference/datamodel.html#index-870
    """
    try:
        raise ZeroDivisionError
    except ZeroDivisionError:
        traceback = sys.exc_info()[2]
    f = traceback.tb_frame
    for i in range(depth):
        f = f.f_back
    return f

def caller_name(depth=1):
    """Return the name of the function `depth` up the call stack.

    Examples
    --------

    >>> def x(depth):
    ...     y(depth)
    >>> def y(depth):
    ...     print caller_name(depth)
    >>> x(1)
    y
    >>> x(2)
    x
    >>> x(0)
    caller_name

    Notes
    -----
    See the Python Refrence manual on `frame objects`_ and
    `code objects`_.

    .. _frame objects:
      http://docs.python.org/reference/datamodel.html#index-870
    .. _code objects:
      http://docs.python.org/reference/datamodel.html#index-866
    """
    f = frame(depth=depth+1)
    return f.f_code.co_name
