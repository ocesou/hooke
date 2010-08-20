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

"""The ``playlist`` module provides :class:`PlaylistPlugin` and
several associated :class:`hooke.command.Command`\s for handling
:mod:`hooke.playlist` classes.
"""

import glob
import logging
import os.path

from ..command import Command, Argument, Failure
from ..curve import NotRecognized
from ..playlist import FilePlaylist
from ..util.itertools import reverse_enumerate
from . import Builtin


class PlaylistPlugin (Builtin):
    def __init__(self):
        super(PlaylistPlugin, self).__init__(name='playlist')
        self._commands = [
            NextCommand(self), PreviousCommand(self), JumpCommand(self),
            GetCommand(self), IndexCommand(self), CurveListCommand(self),
            SaveCommand(self), LoadCommand(self),
            AddCommand(self), AddGlobCommand(self),
            RemoveCommand(self), ApplyCommand(self),
            FilterCommand(self),
            ]


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
    if value != None:
        return value
    i = 0
    names = [p.name for p in hooke.playlists]
    while True:
        name = 'playlist-%d' % i
        if name not in names:
            return name
        i += 1

PlaylistNameArgument = Argument(
    name='output playlist', type='string', optional=True,
    callback=playlist_name_callback,
    help="""
Name of the new playlist (defaults to an auto-generated name).
""".strip())

def all_drivers_callback(hooke, command, argument, value):
    return hooke.drivers


# Define useful command subclasses

class PlaylistCommand (Command):
    """A :class:`~hooke.command.Command` operating on a
    :class:`~hooke.playlist.Playlist`.
    """
    def __init__(self, **kwargs):
        if 'arguments' in kwargs:
            kwargs['arguments'].insert(0, PlaylistArgument)
        else:
            kwargs['arguments'] = [PlaylistArgument]
        super(PlaylistCommand, self).__init__(**kwargs)

    def _playlist(self, hooke, params):
        """Get the selected playlist.

        Notes
        -----
        `hooke` is intended to attach the selected playlist to the
        local hooke instance; the returned playlist should not be
        effected by the state of `hooke`.
        """
        # HACK? rely on params['playlist'] being bound to the local
        # hooke (i.e. not a copy, as you would get by passing a
        # playlist through the queue).  Ugh.  Stupid queues.  As an
        # alternative, we could pass lookup information through the
        # queue...
        return params['playlist']


class PlaylistAddingCommand (Command):
    """A :class:`~hooke.command.Command` adding a
    :class:`~hooke.playlist.Playlist`.
    """
    def __init__(self, **kwargs):
        if 'arguments' in kwargs:
            kwargs['arguments'].insert(0, PlaylistNameArgument)
        else:
            kwargs['arguments'] = [PlaylistNameArgument]
        super(PlaylistAddingCommand, self).__init__(**kwargs)

    def _set_playlist(self, hooke, params, playlist):
        """Attach a new playlist.
        """
        playlist_names = [p.name for p in hooke.playlists]
        if playlist.name in playlist_names or playlist.name == None:
            playlist.name = params['output playlist']  # HACK: override input name.  How to tell if it is callback-generated?
        hooke.playlists.append(playlist)


# Define commands

class NextCommand (PlaylistCommand):
    """Move playlist to the next curve.
    """
    def __init__(self, plugin):
        super(NextCommand, self).__init__(
            name='next curve', help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
	self._playlist(hooke, params).next()


class PreviousCommand (PlaylistCommand):
    """Move playlist to the previous curve.
    """
    def __init__(self, plugin):
        super(PreviousCommand, self).__init__(
            name='previous curve', help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
	self._playlist(hooke, params).previous()


class JumpCommand (PlaylistCommand):
    """Move playlist to a given curve.
    """
    def __init__(self, plugin):
        super(JumpCommand, self).__init__(
            name='jump to curve',
            arguments=[
                Argument(name='index', type='int', optional=False, help="""
Index of target curve.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
	self._playlist(hooke, params).jump(params['index'])


class IndexCommand (PlaylistCommand):
    """Print the index of the current curve.

    The first curve has index 0.
    """
    def __init__(self, plugin):
        super(IndexCommand, self).__init__(
            name='curve index', help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
	outqueue.put(self._playlist(hooke, params).index())


class GetCommand (PlaylistCommand):
    """Return a :class:`hooke.playlist.Playlist`.
    """
    def __init__(self, plugin):
        super(GetCommand, self).__init__(
            name='get playlist', help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        outqueue.put(self._playlist(hooke, params))


class CurveListCommand (PlaylistCommand):
    """Get the curves in a playlist.
    """
    def __init__(self, plugin):
        super(CurveListCommand, self).__init__(
            name='playlist curves', help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
	outqueue.put(list(self._playlist(hooke, params)))


class SaveCommand (PlaylistCommand):
    """Save a playlist.
    """
    def __init__(self, plugin):
        super(SaveCommand, self).__init__(
            name='save playlist',
            arguments=[
                Argument(name='output', type='file',
                         help="""
File name for the output playlist.  Defaults to overwriting the input
playlist.  If the playlist does not have an input file (e.g. it was
created from scratch with 'new playlist'), this option is required.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
	self._playlist(hooke, params).save(params['output'])


class LoadCommand (PlaylistAddingCommand):
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
        p.load(hooke=hooke)
        self._set_playlist(hooke, params, p)
	outqueue.put(p)


class AddCommand (PlaylistCommand):
    """Add a curve to a playlist.
    """
    def __init__(self, plugin):
        super(AddCommand, self).__init__(
            name='add curve to playlist',
            arguments=[
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
        self._playlist(hooke, params).append_curve_by_path(
            params['input'], params['info'], hooke=hooke)


class AddGlobCommand (PlaylistCommand):
    """Add curves to a playlist with file globbing.

    Adding lots of files one at a time can be tedious.  With this
    command you can use globs (`data/curves/*.dat`) to add curves
    for all matching files at once.
    """
    def __init__(self, plugin):
        super(AddGlobCommand, self).__init__(
            name='glob curves to playlist',
            arguments=[
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
        p = self._playlist(hooke, params)
        for path in sorted(glob.glob(params['input'])):
            try:
                p.append_curve_by_path(path, params['info'], hooke=hooke)
            except NotRecognized, e:
                log = logging.getLogger('hooke')
                log.warn(unicode(e))
                continue
            outqueue.put(p[-1])

class RemoveCommand (PlaylistCommand):
    """Remove a curve from a playlist.
    """
    def __init__(self, plugin):
        super(RemoveCommand, self).__init__(
            name='remove curve from playlist',
            arguments=[
                Argument(name='index', type='int', optional=False, help="""
Index of target curve.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        self._playlist(hooke, params).pop(params['index'])
        self._playlist(hooke, params).jump(params.index())


class ApplyCommand (PlaylistCommand):
    """Apply a :class:`~hooke.command_stack.CommandStack` to each
    curve in a playlist.

    TODO: discuss `evaluate`.
    """
    def __init__(self, plugin):
        super(ApplyCommand, self).__init__(
            name='apply command stack to playlist',
            arguments=[
                Argument(name='commands', type='command stack',
                         help="""
Command stack to apply to each curve.  Defaults to the `command_stack`
plugin's current stack.
""".strip()),
                Argument(name='evaluate', type='bool', default=False,
                         help="""
Evaluate the applied command stack immediately.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        params = self.__setup_params(hooke=hooke, params=params)
        p = self._playlist(hooke, params)
        if params['evaluate'] == True:
            exec_cmd = hooke.command_by_name['execute command stack']
            for curve in p.items():
                hooke.run_command(exec_cmd.name,
                                  {'commands':params['commands'],
                                   'stack':True})
        else:
            for curve in p:
                for command in params['commands']:
                    curve.command_stack.append(command)
                curve.set_hooke(hooke)
                curve.unload()

    def __setup_params(self, hooke, params):
        if params['commands'] == None:
            cstack_plugin = [p for p in hooke.plugins
                             if p.name == 'command_stack'][0]
            params['commands'] = cstack_plugin.command_stack
        return params


class FilterCommand (PlaylistAddingCommand, PlaylistCommand):
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
            name=name, help=self.__doc__, plugin=plugin)
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
        p = self._playlist(hooke, params).filter(filter_fn,
            hooke=hooke, inqueue=inqueue, outqueue=outqueue, params=params)
        self._set_playlist(hooke, params, p)
        if hasattr(p, 'path') and p.path != None:
            p.set_path(os.path.join(os.path.dirname(p.path), p.name))
        outqueue.put(p)
