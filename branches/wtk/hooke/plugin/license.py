# Copyright (C) 2010 W. Trevor King <wking@drexel.edu>
#
# This file is part of Hooke.
#
# Hooke is free software: you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# Hooke is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with Hooke.  If not, see
# <http://www.gnu.org/licenses/>.

"""The ``license`` module provides :class:`LicensePlugin` and
associated :class:`hooke.command.Command`\s for displaying Hooke's
licensing information.
"""

from .. import __license__
from ..command import Command, Argument, Failure
from ..plugin import Builtin


class LicensePlugin (Builtin):
    def __init__(self):
        super(LicensePlugin, self).__init__(name='license')
        self._commands = [LicenseCommand(self)]


# Define commands

class LicenseCommand (Command):
    """Show licensing information.
    """
    def __init__(self, plugin):
        super(LicenseCommand, self).__init__(
            name='license',
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
	outqueue.put(__license__)
