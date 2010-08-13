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

"""The `note` module provides :class:`NotePlugin` the associated
:class:`hooke.command.Command`\s for annotating several Hooke classes
(:mod:`hooke.playlist.Playlist`, :mod:`hooke.curve.Curve`, ...).
"""

from ..command import Command, Argument, Failure
from . import Builtin
from .curve import current_curve_callback


class NotePlugin (Builtin):
    def __init__(self):
        super(NotePlugin, self).__init__(name='note')
        self._commands = [
            SetNoteCommand(self), GetNoteCommand(self)]


class SetNoteCommand (Command):
    """Set the note on one of several Hooke objects.
    """
    def __init__(self, plugin):
        super(SetNoteCommand, self).__init__(
            name='set note',
            arguments=[
                Argument(
                    name='target', type='object',
                    callback=current_curve_callback,
                    help="""
Target object for the note.  Defaults to the current curve.
""".strip()),
                Argument(
                    name='note', type='string', optional=False,
                    help="""
The note text.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        params['target'].info['note'] = params['note']


class GetNoteCommand (Command):
    """Retrieve the note from one of several Hooke objects.
    """
    def __init__(self, plugin):
        super(GetNoteCommand, self).__init__(
            name='get note',
            arguments=[
                Argument(
                    name='target', type='object',
                    callback=current_curve_callback,
                    help="""
Target object for the note.  Defaults to the current curve.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        outqueue.put(params['target'].info['note'])
