# Copyright (C) 2010 Massimo Sandal <devicerandom@gmail.com>
#                    W. Trevor King <wking@drexel.edu>
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

"""The `panel` module provides optional submodules that add GUI panels.
"""

from ....util.pluggable import IsSubclass, construct_odict


PANEL_MODULES = [
    'commands',
    'note',
#    'notebook',
    'output',
    'playlist',
    'plot',
    'propertyeditor',
#    'results',
#    'selection',
#    'welcome',
    ]
"""List of panel modules.  TODO: autodiscovery
"""

class Panel (object):
    """Base class for Hooke GUI panels.
    
    :attr:`name` identifies the request type and should match the
    module name.
    """
    def __init__(self, name=None, callbacks=None, **kwargs):
        super(Panel, self).__init__(**kwargs)
        self.name = name
        self.managed_name = name.capitalize()
        self._hooke_frame = kwargs.get('parent', None)
        if callbacks == None:
            callbacks = {}
        self._callbacks = callbacks


PANELS = construct_odict(
    this_modname=__name__,
    submodnames=PANEL_MODULES,
    class_selector=IsSubclass(Panel, blacklist=[Panel]),
    instantiate=False)
""":class:`hooke.compat.odict.odict` of :class:`Panel`
instances keyed by `.name`.
"""
