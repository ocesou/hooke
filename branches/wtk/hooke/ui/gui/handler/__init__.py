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

from ....util.pluggable import IsSubclass, construct_graph


HANDLER_MODULES = [
    'boolean',
    'float',
#    'int'
#    'point',
    'selection',
    'string'
    ]
"""List of handler modules.  TODO: autodiscovery
"""

class Handler (object):
    """Base class for :class:`~hooke.interaction.Request` handlers.
    
    :attr:`name` identifies the request type and should match the
    module name.
    """
    def __init__(self, name):
        self.name = name

    def run(self, hooke_frame, msg):
        raise NotImplemented

    def _cancel(self, *args, **kwargs):
        # TODO: somehow abort the running command


HANDLERS = construct_odict(
    this_modname=__name__,
    submodnames=USER_INTERFACE_MODULES,
    class_selector=IsSubclass(UserInterface, blacklist=[UserInterface]))
""":class:`hooke.compat.odict.odict` of :class:`Handler`
instances keyed by `.name`.
"""
