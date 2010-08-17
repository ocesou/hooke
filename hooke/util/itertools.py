# Copyright

from __future__ import absolute_import

from itertools import izip


def reverse_enumerate(x):
    """Iterate through `enumerate(x)` backwards.

    This is a memory-efficient version of `reversed(list(enumerate(x)))`.
    

    Examples
    --------
    >>> a = ['a', 'b', 'c']
    >>> it = reverse_enumerate(a)
    >>> type(it)
    <type 'itertools.izip'>
    >>> list(it)
    [(2, 'c'), (1, 'b'), (0, 'a')]
    >>> list(reversed(list(enumerate(a))))
    [(2, 'c'), (1, 'b'), (0, 'a')]

    Notes
    -----
    `Original implemenation`_ by Christophe Simonis.

    .. _Original implementation:
      http://christophe-simonis-at-tiny.blogspot.com/2008/08/python-reverse-enumerate.html
    """
    return izip(xrange(len(x)-1, -1, -1), reversed(x))

#  LocalWords:  itertools
