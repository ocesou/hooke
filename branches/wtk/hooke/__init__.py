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

"""The hooke module does all the legwork for Hooke_.

.. _hooke: http://code.google.com/p/hooke/

To facilitate faster loading, submodules are not imported by default.
The available submodules are:

* :mod:`hooke.config`
* :mod:`hooke.compat`
"""
try:
    from .license import LICENSE as __license__
except ImportError, e:
    import logging
    logging.warn('Could not load LICENSE from hooke.license')
    __license__ = 'All rights reserved.' 


__version__ = (1, 0, 0, 'alpha', None, 'Ninken')
"""Version tuple::

    (major, minor, release, type, patch, name)

Where 

  * type: Python uses alpha, beta, candidate, and final.  Whatever
    so long as the alphabetic sort gets them in the right order.
  * patch: either manually incremented for each release, the packaging
    date string, YYYYMMDD, date of last commit, whatever.

See `Greg Noel's post on scons-devel`_ for a good explaination of why this
versioning scheme is a good idea.

.. _Greg Noel's post on scons-devel
  http://thread.gmane.org/gmane.comp.programming.tools.scons.devel/8740
"""

def version(depth=-1, version_tuple=None):
    """Return a nicely formatted version string.::

        major.minor.release.type[.patch] (name)

    Examples
    --------

    Since I seem to be unable to override __version__ in a Doctest,
    we'll pass the version tuple in as an argument.  You can ignore
    `version_tuple`.

    >>> v = (1, 2, 3, 'devel', '20100501', 'Kenzo')

    If depth -1, a full version string is returned

    >>> version(depth=-1, version_tuple=v)
    '1.2.3.devel.20100501 (Kenzo)'

    Otherwise, only the first depth fields are used.

    >>> version(depth=3, version_tuple=v)
    '1.2.3'
    >>> version(depth=4, version_tuple=v)
    '1.2.3.devel'

    Here's an example dropping the patch.

    >>> v = (1, 2, 3, 'devel', None, 'Kenzo')
    >>> version(depth=-1, version_tuple=v)
    '1.2.3.devel (Kenzo)'
    """
    if version_tuple == None:
        version_tuple = __version__
    patch_index = 4
    if version_tuple[patch_index] == None: # No patch field, drop that entry
        version_tuple = version_tuple[0:patch_index] \
            + version_tuple[patch_index+1:]
        if depth >= patch_index:
            depth -= 1
    fields = version_tuple[0:depth]
    string = '.'.join([str(x) for x in fields])
    if depth == -1 or depth == len(version_tuple):
        string += ' (%s)' % version_tuple[-1]
    return string
