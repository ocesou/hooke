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

"""The driver module provides :class:`Driver`\s for identifying and
reading data files.

This allows Hooke to be data-file agnostic.  Drivers for various
commercial force spectroscopy microscopes are provided, and it's easy
to write your own to handle your lab's specific format.
"""

import logging
import os.path

from ..config import Setting
from ..util.pluggable import IsSubclass, construct_graph


DRIVER_MODULES = [
#    ('csvdriver', True),
#    ('hdf5', True),
    ('hemingway', True),
    ('jpk', True),
#    ('mcs', True),
#    ('mfp1dexport', True),
    ('mfp3d', True),
    ('picoforce', True),
    ('tutorial', True),
    ('wtk', True),
]
"""List of driver modules and whether they should be included by
default.  TODO: autodiscovery
"""

DRIVER_SETTING_SECTION = 'drivers'
"""Name of the config section which controls driver selection.
"""


class Driver (object):
    """Base class for file format drivers.
    
    :attr:`name` identifies your driver and should match the module
    name.
    """
    def __init__(self, name):
        self.name = name
        self.setting_section = '%s driver' % self.name

    def dependencies(self):
        """Return a list of :class:`Driver`\s we require."""
        return []

    def default_settings(self):
        """Return a list of :class:`hooke.config.Setting`\s for any
        configurable driver settings.

        The suggested section setting is::

            Setting(section=self.setting_section, help=self.__doc__)
        """
        return []

    def is_me(self, path):
        """Read the file and return True if the filetype can be
        managed by the driver.  Otherwise return False.
        """
        return False

    def read(self, path, info=None):
        """Read data from `path` and return a
        ([:class:`hooke.curve.Data`, ...], `info`) tuple.

        The input `info` :class:`dict` may contain attributes read
        from the :class:`~hooke.playlist.FilePlaylist`.

        See :class:`hooke.curve.Curve` for details.
        """
        raise NotImplementedError

    def logger(self):
        return logging.getLogger('hooke')

# Construct driver dependency graph and load default drivers.

DRIVER_GRAPH = construct_graph(
    this_modname=__name__,
    submodnames=[name for name,include in DRIVER_MODULES],
    class_selector=IsSubclass(Driver, blacklist=[Driver]))
"""Topologically sorted list of all possible :class:`Driver`\s.
"""

def default_settings():
    settings = [Setting(DRIVER_SETTING_SECTION,
                        help='Enable/disable default drivers.')]
    for dnode in DRIVER_GRAPH:
        driver = dnode.data
        default_include = [di for mod_name,di in DRIVER_MODULES
                           if mod_name == driver.name][0]
        help = driver.__doc__.split('\n', 1)[0]
        settings.append(Setting(
                section=DRIVER_SETTING_SECTION,
                option=driver.name,
                value=default_include,
                type='bool',
                help=help,
                ))
    for dnode in DRIVER_GRAPH:
        driver = dnode.data
        settings.extend(driver.default_settings())
    return settings
