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

"""The ``playlists`` module provides :class:`PlaylistsPlugin` and
several associated :class:`hooke.command.Command`\s for handling
lists of :class:`hooke.playlist.Playlist` classes.
"""

from ..command import Command, Argument, Failure
from ..playlist import FilePlaylist
from . import Builtin
from .playlist import PlaylistNameArgument, PlaylistAddingCommand


class PlaylistsPlugin (Builtin):
    def __init__(self):
        super(PlaylistsPlugin, self).__init__(name='playlists')
        self._commands = [
            NextCommand(self), PreviousCommand(self), JumpCommand(self),
            IndexCommand(self), PlaylistListCommand(self), NewCommand(self)]


# Define commands

class NextCommand (Command):
    """Move `hooke.playlists` to the next playlist.
    """
    def __init__(self, plugin):
        super(NextCommand, self).__init__(
            name='next playlist',
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
	hooke.playlists.next()

class PreviousCommand (Command):
    """Move `hooke.playlists` to the previous playlist.
    """
    def __init__(self, plugin):
        super(PreviousCommand, self).__init__(
            name='previous playlist',
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
	hooke.playlists.previous()

class JumpCommand (Command):
    """Move `hooke.playlists` to a given playlist.
    """
    def __init__(self, plugin):
        super(JumpCommand, self).__init__(
            name='jump to playlist',
            arguments=[
                Argument(name='index', type='int', optional=False, help="""
Index of target curve.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
	hooke.playlists.jump(params['index'])

class IndexCommand (Command):
    """Print the index of the current playlist.

    The first playlist has index 0.
    """
    def __init__(self, plugin):
        super(IndexCommand, self).__init__(
            name='playlist index',
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
	outqueue.put(hooke.playlists.index())

class PlaylistListCommand (Command):
    """Get the playlists in `hooke.playlists`.
    """
    def __init__(self, plugin):
        super(PlaylistListCommand, self).__init__(
            name='playlists',
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
	outqueue.put(list(hooke.playlists))


class NewCommand (PlaylistAddingCommand):
    """Create a new playlist.
    """
    def __init__(self, plugin):
        super(NewCommand, self).__init__(
            name='new playlist',
            arguments=[
                Argument(name='file', type='file', optional=True,
                         help="""
Default filename for future saves.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        p = FilePlaylist(
            drivers=hooke.drivers,
            path=params['file'],
            )
        self._set_playlist(hooke, params, p)
        outqueue.put(p)
