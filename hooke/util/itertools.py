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
