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

"""The ``command_stack`` module provides tools for managing and
executing stacks of :class:`~hooke.engine.CommandMessage`\s.
"""


class CommandStack (list):
    """Store a stack of commands.

    Examples
    --------
    >>> from .engine import CommandMessage
    >>> c = CommandStack([CommandMessage('CommandA', {'param':'A'})])
    >>> c.append(CommandMessage('CommandB', {'param':'B'}))
    >>> c.append(CommandMessage('CommandA', {'param':'C'}))
    >>> c.append(CommandMessage('CommandB', {'param':'D'}))

    Implement a dummy :meth:`execute_command` for testing.
    
    >>> def execute_cmd(hooke, command_message):
    ...     cm = command_message
    ...     print 'EXECUTE', cm.command, cm.arguments
    >>> c.execute_command = execute_cmd

    >>> c.execute(hooke=None)  # doctest: +ELLIPSIS
    EXECUTE CommandA {'param': 'A'}
    EXECUTE CommandB {'param': 'B'}
    EXECUTE CommandA {'param': 'C'}
    EXECUTE CommandB {'param': 'D'}

    :meth:`filter` allows you to select which commands get executed.
    If, for example, you are applying a set of commands to the current
    :class:`~hooke.curve.Curve`, you may only want to execute
    instances of :class:`~hooke.plugin.curve.CurveCommand`.  Here we
    only execute commands named `CommandB`.
    
    >>> def filter(hooke, command_message):
    ...     return command_message.command == 'CommandB'
    >>> c.filter = filter

    Apply the stack to the current curve.

    >>> c.execute(hooke=None)  # doctest: +ELLIPSIS
    EXECUTE CommandB {'param': 'B'}
    EXECUTE CommandB {'param': 'D'}

    Execute a new command and add it to the stack.

    >>> cm = CommandMessage('CommandC', {'param':'E'})
    >>> c.execute_command(hooke=None, command_message=cm)
    EXECUTE CommandC {'param': 'E'}
    >>> c.append(cm)
    >>> print [repr(cm) for cm in c]  # doctest: +NORMALIZE_WHITESPACE
    ["<CommandMessage CommandA {'param': 'A'}>",
     "<CommandMessage CommandB {'param': 'B'}>",
     "<CommandMessage CommandA {'param': 'C'}>",
     "<CommandMessage CommandB {'param': 'D'}>",
     "<CommandMessage CommandC {'param': 'E'}>"]
    """
    def execute(self, hooke):
        """Execute a stack of commands.

        See Also
        --------
        _execute, filter
        """
        for command_message in self:
            if self.filter(hooke, command_message) == True:
                self.execute_command(
                    hooke=hooke, command_message=command_message)

    def filter(self, hooke, command_message):
        """Return `True` to execute `command_message`, `False` otherwise.

        The default implementation always returns `True`.
        """
        return True

    def execute_command(self, hooke, command_message):
        hooke.run_command(command=command_message.command,
                          arguments=command_message.arguments)
