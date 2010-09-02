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

"""Define the :class:`Singleton` class.

>>> class A (Singleton):
...     def init(self):
...         print 'initializing instance of %s at (%s)' % (
...             self.__class__.__name__, id(self))

>>> A_instances = [A() for i in range(3)]  # doctest: +ELLIPSIS
initializing instance of A at (...)
>>> for i in A_instances[1:]:
...     print id(i) == id(A_instances[0])
True
True

Singletons can also be subclassed.

>>> class B (A):
...     pass
>>> B_instances = [B() for i in range(3)]  # doctest: +ELLIPSIS
initializing instance of B at (...)
>>> for i in B_instances[1:]:
...     print id(i) == id(B_instances[0])
True
True
>>> id(A_instances[0]) == id(B_instances[0])
False
"""

class Singleton (object):
    """A singleton class.

    To create a singleton class, you subclass from Singleton; each
    subclass will have a single instance, no matter how many times its
    constructor is called. To further initialize the subclass
    instance, subclasses should override 'init' instead of __init__ -
    the __init__ method is called each time the constructor is called.

    Notes
    -----
    Original implementation from Guido van Rossum's
    `Unifying types and classes in Python 2.2`_.

    .. Unifying types and classes in Python 2.2:
      http://www.python.org/download/releases/2.2.3/descrintro/#__new__
    """
    def __new__(cls, *args, **kwds):
        it = cls.__dict__.get('__it__')
        if it is not None:
            return it
        cls.__it__ = it = object.__new__(cls)
        it.init(*args, **kwds)
        return it

    def init(self, *args, **kwds):
        pass
