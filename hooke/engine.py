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

from .ui import CloseEngine, CommandMessage


class CommandEngine (object):
    def run(self, hooke, ui_to_command_queue, command_to_ui_queue):
        """Get a :class:`hooke.ui.QueueMessage` from the incoming
        `ui_to_command_queue` and act accordingly.

        If the message is a :class:`hooke.ui.CommandMessage` instance,
        the command run may read subsequent input from
        `ui_to_command_queue` (if it is an interactive command).  The
        command may also put assorted data into `command_to_ui_queue`.

        When the command completes, it will put a
        :class:`hooke.command.CommandExit` instance into
        `command_to_ui_queue`, at which point the `CommandEngine` will
        be ready to receive the next :class:`hooke.ui.QueueMessage`.
        """
        log = logging.getLogger('hooke')
        while True:
            log.debug('engine waiting for command')
            msg = ui_to_command_queue.get()
            if isinstance(msg, CloseEngine):
                command_to_ui_queue.put(hooke)
                log.debug(
                    'engine closing, placed hooke instance in return queue')
                break
            assert isinstance(msg, CommandMessage), type(msg)
            log.debug('engine running %s' % msg.command.name)
            msg.command.run(hooke, ui_to_command_queue, command_to_ui_queue,
                            **msg.arguments)
