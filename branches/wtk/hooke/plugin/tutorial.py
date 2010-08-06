# Copyright (C) 2007-2010 Massimo Sandal <devicerandom@gmail.com>
#                         W. Trevor King <wking@drexel.edu>
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

"""This plugin contains example commands to teach how to write an
Hooke plugin, including description of main Hooke internals.
"""

import logging
import StringIO

from numpy import arange

from ..command import Command, Argument, Failure
from ..config import Setting
from ..interaction import PointRequest, PointResponse
from ..util.si import ppSI, split_data_label
from . import Plugin
from .curve import CurveArgument


class TutorialPlugin (Plugin):
    """An example plugin explaining how to code plugins.

    Unlike previous versions of Hooke, the class name is no longer
    important.  Plugins identify themselves to
    :func:`hooke.util.pluggable.construct_graph` by being subclasses
    of :class:`hooke.plugin.Plugin`.  However, for consistency we
    suggest the following naming scheme, show here for the 'tutorial'
    plugin:

    ===========  ==============
    module file  tutorial.py
    class name   TutorialPlugin
    .name        'tutorial'
    ===========  ==============

    To ensure filename sanity,
    :func:`hooke.util.pluggable.construct_graph` requires that
    :attr:`name` does match the submodule name, but don't worry,
    you'll get a clear exception message if you make a mistake.
    """
    def __init__(self):
        """TutorialPlugin initialization code.

        We call our base class' :meth:`__init__` and setup
        :attr:`_commands`.
        """
        # This is the plugin initialization.  When Hooke starts and
        # the plugin is loaded, this function is executed.  If there
        # is something you need to do when Hooke starts, code it in
        # this function.
        print 'I am the Tutorial plugin initialization!'

        # This super() call similar to the old-style
        #   Plugin.__init__
        # but super() is more robust under multiple inheritance.
        # See Guido's introduction:
        #   http://www.python.org/download/releases/2.2.3/descrintro/#cooperation
        # And the related PEPs:
        #   http://www.python.org/dev/peps/pep-0253/
        #   http://www.python.org/dev/peps/pep-3135/
        super(TutorialPlugin, self).__init__(name='tutorial')

        # We want :meth:`commands` to return a list of
        # :class:`hooke.command.Command` instances.  Rather than
        # instantiate the classes for each call to :meth:`commands`,
        # we instantiate them in a list here, and rely on
        # :meth:`hooke.plugin.Plugin.commands` to return copies of
        # that list.
        self._commands = [DoNothingCommand(self), HookeInfoCommand(self),
                          PointInfoCommand(self),]

    def dependencies(self):
        """Return a list  of names of :class:`hooke.plugin.Plugin`\s we
        require.

        Some plugins use features from other plugins.  Hooke makes sure that
        plugins are configured in topological order and that no plugin is
        enabled if it is missing dependencies.
        """
        return ['vclamp']

    def default_settings(self):
        """Return a list of :class:`hooke.config.Setting`\s for any
        configurable plugin settings.

        The suggested section setting is::

            Setting(section=self.setting_section, help=self.__doc__)

        You only need to worry about this if your plugin has some
        "magic numbers" that the user may want to tweak, but that
        won't be changing on a per-command basis.

        You should lead off the list of settings with the suggested
        section setting mentioned above.
        """
        return [
            # We disable help wrapping, since we've wrapped
            # TutorialPlugin.__doc__ ourselves, and it's more than one
            # paragraph (textwrap.fill, used in
            # :meth:`hooke.config.Setting.write` only handles one
            # paragraph at a time).
            Setting(section=self.setting_section, help=self.__doc__,
                    wrap=False),
            Setting(section=self.setting_section, option='favorite color',
                    value='orange', help='Your personal favorite color.'),
            ]


# Define common or complicated arguments

# Often, several commands in a plugin will use similar arguments.  For
# example, many curves in the 'playlist' plugin need a playlist to act
# on.  Rather than repeating an argument definition in several times,
# you can keep your code DRY (Don't Repeat Yourself) by defining the
# argument at the module level and referencing it during each command
# initialization.

def color_callback(hooke, command, argument, value):
    """If `argument` is `None`, default to the configured 'favorite color'.

    :class:`hooke.command.Argument`\s may have static defaults, but
    for dynamic defaults, they use callback functions (like this one).
    """
    if value != None:
        return value
    return command.plugin.config['favorite color']

ColorArgument = Argument(
    name='color', type='string', callback=color_callback,
    help="Pick a color, any color.")
# See :func:`hooke.ui.gui.panel.propertyeditor.prop_from_argument` for
# a situation where :attr:`type` is important.


class DoNothingCommand (Command):
    """This is a boring but working example of an actual Hooke command.
    
    As for :class:`hooke.plugin.Plugin`\s, the class name is not
    important, but :attr:`name` is.  :attr:`name` is used (possibly
    with some adjustment) as the name for accessing the command in the
    various :class:`hooke.ui.UserInterface`\s.  For example the
    `'do nothing'` command can be run from the command line UI with::

       hooke> do_nothing

    Note that if you now start Hooke with the command's plugin
    activated and you type in the Hooke command line "help do_nothing"
    you will see this very text as output. That is because we set
    :attr:`_help` to this class' docstring on initialization.
    """
    def __init__(self, plugin):
        # See the comments in TutorialPlugin.__init__ for details
        # about super() and the docstring of
        # :class:`hooke.command.Command` for details on the __init__()
        # arguments.
        super(DoNothingCommand, self).__init__(
            name='do nothing',
            arguments=[ColorArgument],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        """This is where the command-specific magic will happen.

        If you haven't already, read the Architecture section of
        :file:`doc/hacking.txt` (also available `online`_).  It
        explains the engine/UI setup in more detail.

        .. _online:
          http://www.physics.drexel.edu/~wking/rsrch/hooke/hacking.html#architecture

        The return value (if any) of this method is ignored.  You
        should modify the :class:`hooke.hooke.Hooke` instance passed
        in via `hooke` and/or return things via `outqueue`.  `inqueue`
        is only important if your command requires mid-command user
        interaction.

        By the time this method is called, all the argument
        preprocessing (callbacks, defaults, etc.) have already been
        handled by :meth:`hooke.command.Command.run`.
        """
        # On initialization, :class:`hooke.hooke.Hooke` sets up a
        # logger to use for Hooke-related messages.  Please use it
        # instead of debugging 'print' calls, etc., as it is more
        # configurable.
        log = logging.getLogger('hooke')
        log.debug('Watching %s paint dry' % params['color'])


class HookeInfoCommand (Command):
    """Get information about the :class:`hooke.hooke.Hooke` instance.
    """
    def __init__(self, plugin):
        super(HookeInfoCommand, self).__init__(
            name='hooke info',
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        outqueue.put('Hooke info:')
        # hooke.config contains a :class:`hooke.config.HookeConfigParser`
        # with the current hooke configuration settings.
        config_file = StringIO.StringIO()
        hooke.config.write(config_file)
        outqueue.put('configuration:\n  %s'
                     % '\n  '.join(config_file.getvalue().splitlines()))
        # The plugin's configuration settings are also available.
        outqueue.put('plugin config: %s' % self.plugin.config)
        # hooke.plugins contains :class:`hooke.plugin.Plugin`\s defining
        # :class:`hooke.command.Command`\s.
        outqueue.put('plugins: %s'
                     % ', '.join([plugin.name for plugin in hooke.plugins]))
        # hooke.drivers contains :class:`hooke.driver.Driver`\s for
        # loading curves.
        outqueue.put('drivers: %s'
                     % ', '.join([driver.name for driver in hooke.drivers]))
        # hooke.playlists contains a
        # :class:`hooke.playlist.NoteIndexList` of
        # :class:`hooke.playlist.Playlist`\s.  Each playlist may
        # contain several :class:`hooke.curve.Curve`\s representing a
        # grouped collection of data.
        playlist = hooke.playlists.current()
        if playlist == None:
            return
        outqueue.put('current playlist: %s (%d of %d)'
                     % (playlist.name,
                        hooke.playlists.index(),
                        len(hooke.playlists)))
        curve = playlist.current()
        if curve == None:
            return
        outqueue.put('current curve: %s (%d of %d)'
                     % (curve.name,
                        playlist.index(),
                        len(playlist)))


class PointInfoCommand (Command):
    """Get information about two user-selected points.

    Ordinarily a command that knew it would need user selected points
    would declare an appropriate argument (see, for example,
    :class:`hooke.plugin.cut.CutCommand`).  However, here we find the
    points via user-interaction to show how user interaction works.
    """
    def __init__(self, plugin):
        super(PointInfoCommand, self).__init__(
            name='point info',
            arguments=[
                CurveArgument,
                Argument(name='block', type='int', default=0,
                    help="""
Data block that points are selected from.  For an approach/retract
force curve, `0` selects the approaching curve and `1` selects the
retracting curve.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        data = params['curve'].data[params['block']]
        while True:
            # Ask the user to select a point.
            outqueue.put(PointRequest(
                    msg="Select a point",
                    curve=params['curve'],
                    block=params['block']))

            # Get the user's response
            result = inqueue.get()
            if not isinstance(result, PointResponse):
                inqueue.put(result)  # put the message back in the queue
                raise Failure(
                    'expected a PointResponse instance but got %s.'
                    % type(result))
            point = result.value

            # Act on the response
            if point == None:
                break
            values = []
            for column_name in data.info['columns']:
                name,unit = split_data_label(column_name)
                column_index = data.info['columns'].index(column_name)
                value = data[point,column_index]
                si_value = ppSI(value, unit, decimals=2)
                values.append('%s: %s' % (name, si_value))

            outqueue.put('selected point %d: %s'
                         % (point, ', '.join(values)))
