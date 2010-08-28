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

"""The `engine` module provides :class:`CommandEngine` for executing
:class:`hooke.command.Command`\s.
"""

import logging
from Queue import Queue, Empty

from .command import NullQueue


class QueueMessage (object):
    def __str__(self):
        return self.__class__.__name__


class CloseEngine (QueueMessage):
    pass


class CommandMessage (QueueMessage):
    """A message storing a command to run, `command` should be the
    name of a :class:`hooke.command.Command` instance, and `arguments`
    should be a :class:`dict` with `argname` keys and `value` values
    to be passed to the command.
    """
    def __init__(self, command, arguments=None):
        self.command = command
        if arguments == None:
            arguments = {}
        self.arguments = arguments
        self.explicit_user_call = True
        """Message is explicitly user-executed.  This is useful for
        distinguishing auto-generated calls (for which
        `explicit_user_call` should be `False` such as the GUIs
        current status requests.
        """

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        """Return a unicode representation of the `CommandMessage`.

        Examples
        --------
        >>> from .compat.odict import odict
        >>> cm = CommandMessage('command A')
        >>> print unicode(cm)
        <CommandMessage command A>
        >>> cm.arguments = odict([('param a','value a'), ('param b', 'value b')])
        >>> print unicode(cm)
        <CommandMessage command A {param a: value a, param b: value b}>

        The parameters are sorted by name, so you won't be surprised
        in any doctests, etc.

        >>> cm.arguments = odict([('param b','value b'), ('param a', 'value a')])
        >>> print unicode(cm)
        <CommandMessage command A {param a: value a, param b: value b}>
        """
        if len(self.arguments) > 0:
            return u'<%s %s {%s}>' % (
                self.__class__.__name__, self.command,
                ', '.join(['%s: %s' % (key, value)
                           for key,value in sorted(self.arguments.items())]))
        return u'<%s %s>' % (self.__class__.__name__, self.command)

    def __repr__(self):
        return self.__str__()


class CommandEngine (object):
    def run(self, hooke, ui_to_command_queue, command_to_ui_queue):
        """Get a :class:`QueueMessage` from the incoming
        `ui_to_command_queue` and act accordingly.

        If the message is a :class:`CommandMessage` instance, the
        command run may read subsequent input from
        `ui_to_command_queue` (if it is an interactive command).  The
        command may also put assorted data into `command_to_ui_queue`.

        When the command completes, it will put a
        :class:`hooke.command.CommandExit` instance into
        `command_to_ui_queue`, at which point the `CommandEngine` will
        be ready to receive the next :class:`QueueMessage`.
        """
        log = logging.getLogger('hooke')
        log.debug('engine starting')
        for playlist in hooke.playlists:  # Curve._hooke is not pickled.
            for curve in playlist:
                curve.set_hooke(hooke)
        while True:
            log.debug('engine waiting for command')
            msg = ui_to_command_queue.get()
            if isinstance(msg, CloseEngine):
                command_to_ui_queue.put(hooke)
                log.debug(
                    'engine closing, placed hooke instance in return queue')
                break
            assert isinstance(msg, CommandMessage), type(msg)
            log.debug('engine running %s' % msg)
            cmd = hooke.command_by_name[msg.command]
            cmd.run(hooke, ui_to_command_queue, command_to_ui_queue,
                    **msg.arguments)

    def run_command(self, hooke, command, arguments):
        """Run the command named `command` with `arguments` using
        :meth:`~hooke.engine.CommandEngine.run_command`.

        This allows commands to execute sub commands and enables
        :class:`~hooke.command_stack.CommandStack` execution.

        Note that these commands *do not* have access to the usual UI
        communication queues, so make sure they will not need user
        interaction.
        """
        log = logging.getLogger('hooke')
        log.debug('engine running internal %s'
                  % CommandMessage(command, arguments))
        outqueue = Queue()
        cmd = hooke.command_by_name[command]
        cmd.run(hooke, NullQueue(), outqueue, **arguments)
        while True:
            try:
                msg = outqueue.get(block=False)
            except Empty:
                break
            log.debug('engine message from %s (%s): %s' % (command, type(msg), msg))
