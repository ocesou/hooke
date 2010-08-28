# Copyright (C) 2010 W. Trevor King <wking@drexel.edu>
#
# This file is part of Hooke.
#
# Hooke is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Hooke is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General
# Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with Hooke.  If not, see
# <http://www.gnu.org/licenses/>.

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

def caller_names(depth=1):
    """Iterate through the names of all functions up the call stack.

    Examples
    --------

    >>> def x():
    ...     y()
    >>> def y():
    ...     z()
    >>> def z():
    ...     print list(caller_names())
    >>> x()  # doctest: +ELLIPSIS
    ['z', 'y', 'x', ...]
    >>> y()  # doctest: +ELLIPSIS
    ['z', 'y', ...]
    >>> z()  # doctest: +ELLIPSIS
    ['z', ...]
    """
    depth = 2  # start at caller_names()'s caller.
    while True:
        try:
            yield caller_name(depth=depth)
        except AttributeError:
            return
        depth += 1
