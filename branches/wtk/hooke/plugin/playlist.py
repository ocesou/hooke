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

"""The ``playlist`` module provides :class:`PlaylistPlugin` and
several associated :class:`hooke.command.Command`\s for handling
:mod:`hooke.playlist` classes.
"""

import glob
import os.path

from ..command import Command, Argument, Failure
from ..playlist import FilePlaylist
from ..plugin import Builtin


class PlaylistPlugin (Builtin):
    def __init__(self):
        super(PlaylistPlugin, self).__init__(name='playlist')
        self._commands = [
            NextCommand(self), PreviousCommand(self), JumpCommand(self),
            GetCommand(self), IndexCommand(self), CurveListCommand(self),
            SaveCommand(self), LoadCommand(self),
            AddCommand(self), AddGlobCommand(self),
            RemoveCommand(self), FilterCommand(self), NoteFilterCommand(self)]


# Define common or complicated arguments

def current_playlist_callback(hooke, command, argument, value):
    if value != None:
        return value
    playlist = hooke.playlists.current()
    if playlist == None:
        raise Failure('No playlists loaded')
    return playlist

PlaylistArgument = Argument(
    name='playlist', type='playlist', callback=current_playlist_callback,
    help="""
:class:`hooke.playlist.Playlist` to act on.  Defaults to the current
playlist.
""".strip())

def playlist_name_callback(hooke, command, argument, value):
    i = 0
    names = [p.name for p in hooke.playlists]
    while True:
        name = 'playlist-%d' % i
        if name not in names:
            return name
        i += 1

PlaylistNameArgument = Argument(
    name='name', type='string', optional=True, callback=playlist_name_callback,
    help="""
Name of the new playlist (defaults to an auto-generated name).
""".strip())

def all_drivers_callback(hooke, command, argument, value):
    return hooke.drivers


# Define commands

class NextCommand (Command):
    """Move playlist to the next curve.
    """
    def __init__(self, plugin):
        super(NextCommand, self).__init__(
            name='next curve',
            arguments=[PlaylistArgument],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
	params['playlist'].next()

class PreviousCommand (Command):
    """Move playlist to the previous curve.
    """
    def __init__(self, plugin):
        super(PreviousCommand, self).__init__(
            name='previous curve',
            arguments=[PlaylistArgument],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
	params['playlist'].previous()

class JumpCommand (Command):
    """Move playlist to a given curve.
    """
    def __init__(self, plugin):
        super(JumpCommand, self).__init__(
            name='jump to curve',
            arguments=[
                PlaylistArgument,
                Argument(name='index', type='int', optional=False, help="""
Index of target curve.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
	params['playlist'].jump(int(params['index'])) # HACK, int() should be handled by ui

class IndexCommand (Command):
    """Print the index of the current curve.

    The first curve has index 0.
    """
    def __init__(self, plugin):
        super(IndexCommand, self).__init__(
            name='curve index',
            arguments=[
                PlaylistArgument,
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
	outqueue.put(params['playlist']._index)

class GetCommand (Command):
    """Return a :class:`hooke.playlist.Playlist`.
    """
    def __init__(self, plugin):
        super(GetCommand, self).__init__(
            name='get playlist',
            arguments=[PlaylistArgument],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        outqueue.put(params['playlist'])

class CurveListCommand (Command):
    """Get the curves in a playlist.
    """
    def __init__(self, plugin):
        super(CurveListCommand, self).__init__(
            name='playlist curves',
            arguments=[PlaylistArgument],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
	outqueue.put(list(params['playlist']))

class SaveCommand (Command):
    """Save a playlist.
    """
    def __init__(self, plugin):
        super(SaveCommand, self).__init__(
            name='save playlist',
            arguments=[
                PlaylistArgument,
                Argument(name='output', type='file',
                         help="""
File name for the output playlist.  Defaults to overwriting the input
playlist.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
	params['playlist'].save(params['output'])

class LoadCommand (Command):
    """Load a playlist.
    """
    def __init__(self, plugin):
        super(LoadCommand, self).__init__(
            name='load playlist',
            arguments=[
                Argument(name='input', type='file', optional=False,
                         help="""
File name for the input playlist.
""".strip()),
                Argument(name='drivers', type='driver', optional=True,
                         count=-1, callback=all_drivers_callback,
                         help="""
Drivers for loading curves.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        p = FilePlaylist(drivers=params['drivers'], path=params['input'])
        p.load()
        hooke.playlists.append(p)
	outqueue.put(p)

class AddCommand (Command):
    """Add a curve to a playlist.
    """
    def __init__(self, plugin):
        super(AddCommand, self).__init__(
            name='add curve to playlist',
            arguments=[
                PlaylistArgument,
                Argument(name='input', type='file', optional=False,
                         help="""
File name for the input :class:`hooke.curve.Curve`.
""".strip()),
                Argument(name='info', type='dict', optional=True,
                         help="""
Additional information for the input :class:`hooke.curve.Curve`.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        params['playlist'].append_curve_by_path(params['input'],
                                                params['info'])

class AddGlobCommand (Command):
    """Add curves to a playlist with file globbing.

    Adding lots of files one at a time can be tedious.  With this
    command you can use globs (`data/curves/*.dat`) to add curves
    for all matching files at once.
    """
    def __init__(self, plugin):
        super(AddGlobCommand, self).__init__(
            name='glob curves to playlist',
            arguments=[
                PlaylistArgument,
                Argument(name='input', type='string', optional=False,
                         help="""
File name glob for the input :class:`hooke.curve.Curve`.
""".strip()),
                Argument(name='info', type='dict', optional=True,
                         help="""
Additional information for the input :class:`hooke.curve.Curve`.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        for path in sorted(glob.glob(params['input'])):
            params['playlist'].append_curve_by_path(path, params['info'])

class RemoveCommand (Command):
    """Remove a curve from a playlist.
    """
    def __init__(self, plugin):
        super(RemoveCommand, self).__init__(
            name='remove curve from playlist',
            arguments=[
                PlaylistArgument,
                Argument(name='index', type='int', optional=False, help="""
Index of target curve.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        params['playlist'].pop(params['index'])
        params['playlist'].jump(params._index)

class FilterCommand (Command):
    """Create a subset playlist via a selection function.

    Removing lots of curves one at a time can be tedious.  With this
    command you can use a function `filter` to select the curves you
    wish to keep.

    Notes
    -----
    There are issues with pickling functions bound to class
    attributes, because the pickle module doesn't know where those
    functions were originally defined (where it should point the
    loader).  Because of this, subclasses with hard-coded filter
    functions are encouraged to define their filter function as a
    method of their subclass.  See, for example,
    :meth:`NoteFilterCommand.filter`.
    """
    def __init__(self, plugin, name='filter playlist'):
        super(FilterCommand, self).__init__(
            name=name,
            arguments=[
                PlaylistArgument,
                PlaylistNameArgument,
                ],
            help=self.__doc__, plugin=plugin)
        if not hasattr(self, 'filter'):
            self.arguments.append(
                Argument(name='filter', type='function', optional=False,
                         help="""
Function returning `True` for "good" curves.
`filter(curve, hooke, inqueue, outqueue, params) -> True/False`.
""".strip()))

    def _run(self, hooke, inqueue, outqueue, params):
        if not hasattr(self, 'filter'):
            filter_fn = params['filter']
        else:
            filter_fn = self.filter
        p = params['playlist'].filter(filter_fn,
            hooke=hooke, inqueue=inqueue, outqueue=outqueue, params=params)
        p.name = params['name']
        if hasattr(p, 'path') and p.path != None:
            p.set_path(os.path.join(os.path.dirname(p.path), p.name))
        hooke.playlists.append(p)
        outqueue.put(p)

class NoteFilterCommand (FilterCommand):
    """Create a subset playlist of curves with `.info['note'] != None`.
    """
    def __init__(self, plugin):
        super(NoteFilterCommand, self).__init__(
            plugin, name='note filter playlist')

    def filter(self, curve, hooke, inqueue, outqueue, params):
        return 'note' in curve.info and curve.info['note'] != None
