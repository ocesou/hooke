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

"""The `debug` module provides :class:`DebugPlugin` and associated
:class:`hooke.command.Command`\s which provide useful debugging
information.
"""

import platform
import sys

from .. import version
from ..command import Command, Argument
from ..plugin import Builtin


class DebugPlugin (Builtin):
    def __init__(self):
        super(DebugPlugin, self).__init__(name='debug')
        self._commands = [VersionCommand(self), DebugCommand(self)]


class VersionCommand (Command):
    """Get the Hooke version, as well as versions for important Python
    packages.  Useful for debugging.
    """
    def __init__(self, plugin):
        super(VersionCommand, self).__init__(
            name='version', help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        lines = [
            'Hooke ' + version(),
            '----',
            'Python ' + sys.version]
        for name,module in sorted(sys.modules.items()):
            if name == 'hooke':
                continue
            v = getattr(module, '__version__', None)
            if v != None:
                lines.append('%s %s' % (name, v))
        lines.extend([
                '----',
                'Platform: %s' % ' '.join(platform.uname()),
                'User interface: %s' % hooke.ui.name,
                '----',
                'Loaded plugins:'])
        lines.extend([p.name for p in hooke.plugins])
        lines.extend([
                '----',
                'Loaded drivers:'])
        lines.extend([d.name for d in hooke.drivers])
        outqueue.put('\n'.join(lines))


class DebugCommand (Command):
    """Get Hooke attributes.  Useful for debugging.
    """
    def __init__(self, plugin):
        super(DebugCommand, self).__init__(
            name='debug',
            arguments=[
                Argument(name='attribute', help="""
Hooke attribute to print.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        if params['attribute'] == None:
            outqueue.put(hooke)
        else:
            outqueue.put(getattr(hooke, params['attribute']))
