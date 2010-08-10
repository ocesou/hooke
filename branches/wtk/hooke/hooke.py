# Copyright (C) 2008-2010 Fabrizio Benedetti
#                         Massimo Sandal <devicerandom@gmail.com>
#                         Rolf Schmidt <rschmidt@alcor.concordia.ca>
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

"""Hooke - A force spectroscopy review & analysis tool.
"""

if False: # Queue pickle error debugging code
    """The Hooke class is passed back from the CommandEngine process
    to the main process via a :class:`multiprocessing.queues.Queue`,
    which uses :mod:`pickle` for serialization.  There are a number of
    objects that are unpicklable, and the error messages are not
    always helpful.  This block of code hooks you into the Queue's
    _feed method so you can print out useful tidbits to help find the
    particular object that is gumming up the pickle works.
    """
    import multiprocessing.queues
    import sys
    feed = multiprocessing.queues.Queue._feed
    def new_feed (buffer, notempty, send, writelock, close):
        def s(obj):
            print 'SEND:', obj, dir(obj)
            for a in dir(obj):
                attr = getattr(obj, a)
                #print '  ', a, attr, type(attr)
            if obj.__class__.__name__ == 'Hooke':
                # Set suspect attributes to None until you resolve the
                # PicklingError.  Then fix whatever is breaking the
                # pickling.
                #obj.commands = None
                #obj.drivers = None
                #obj.plugins = None
                #obj.ui = None
                pass
            sys.stdout.flush()
            send(obj)
        feed(buffer, notempty, s, writelock, close)
    multiprocessing.queues.Queue._feed = staticmethod(new_feed)

import logging
import logging.config
import multiprocessing
import optparse
import os.path
import Queue
import unittest
import StringIO
import sys

from . import version
from . import engine
from . import config as config_mod
from . import playlist
from . import plugin as plugin_mod
from . import driver as driver_mod
from . import ui


class Hooke (object):
    def __init__(self, config=None, debug=0):
        self.debug = debug
        default_settings = (config_mod.DEFAULT_SETTINGS
                            + plugin_mod.default_settings()
                            + driver_mod.default_settings()
                            + ui.default_settings())
        if config == None:
            config = config_mod.HookeConfigParser(
                paths=config_mod.DEFAULT_PATHS,
                default_settings=default_settings)
            config.read()
        self.config = config
        self.load_log()
        self.load_plugins()
        self.load_drivers()
        self.load_ui()
        self.command = engine.CommandEngine()
        self.playlists = playlist.NoteIndexList()

    def load_log(self):
        config_file = StringIO.StringIO()
        self.config.write(config_file)
        logging.config.fileConfig(StringIO.StringIO(config_file.getvalue()))
        # Don't attach the logger because it contains an unpicklable
        # thread.lock.  Instead, grab it directly every time you need it.
        #self.log = logging.getLogger('hooke')

    def load_plugins(self):
        self.plugins = plugin_mod.load_graph(
            plugin_mod.PLUGIN_GRAPH, self.config, include_section='plugins')
        self.commands = []
        for plugin in self.plugins:
            self.commands.extend(plugin.commands())

    def load_drivers(self):
        self.drivers = plugin_mod.load_graph(
            driver_mod.DRIVER_GRAPH, self.config, include_section='drivers')

    def load_ui(self):
        self.ui = ui.load_ui(self.config)

    def close(self):
        self.config.write() # Does not preserve original comments

class HookeRunner (object):
    def run(self, hooke):
        """Run Hooke's main execution loop.

        Spawns a :class:`hooke.engine.CommandEngine` subprocess and
        then runs the UI, rejoining the `CommandEngine` process after
        the UI exits.
        """
        ui_to_command,command_to_ui,command = self._setup_run(hooke)
        try:
            hooke.ui.run(hooke.commands, ui_to_command, command_to_ui)
        finally:
            hooke = self._cleanup_run(ui_to_command, command_to_ui, command)
        return hooke

    def run_lines(self, hooke, lines):
        """Run the pre-set commands `lines` with the "command line" UI.

        Allows for non-interactive sessions that are otherwise
        equivalent to :meth:'.run'.
        """
        cmdline = ui.load_ui(hooke.config, 'command line')
        ui_to_command,command_to_ui,command = self._setup_run(hooke)
        try:
            cmdline.run_lines(
                hooke.commands, ui_to_command, command_to_ui, lines)
        finally:
            hooke = self._cleanup_run(ui_to_command, command_to_ui, command)
        return hooke

    def _setup_run(self, hooke):
        ui_to_command = multiprocessing.Queue()
        command_to_ui = multiprocessing.Queue()
        manager = multiprocessing.Manager()
        command = multiprocessing.Process(name='command engine',
            target=hooke.command.run, args=(hooke, ui_to_command, command_to_ui))
        command.start()
        return (ui_to_command, command_to_ui, command)

    def _cleanup_run(self, ui_to_command, command_to_ui, command):
        log = logging.getLogger('hooke')
        log.debug('cleanup sending CloseEngine')
        ui_to_command.put(ui.CloseEngine())
        hooke = None
        while not isinstance(hooke, Hooke):
            log.debug('cleanup waiting for Hooke instance from the engine.')
            hooke = command_to_ui.get(block=True)
            log.debug('cleanup got %s instance' % type(hooke))
        command.join()
        return hooke


def main():
    p = optparse.OptionParser()
    p.add_option(
        '--version', dest='version', default=False, action='store_true',
        help="Print Hooke's version information and exit.")
    p.add_option(
        '-s', '--script', dest='script', metavar='FILE',
        help='Script of command line Hooke commands to run.')
    p.add_option(
        '-c', '--command', dest='commands', metavar='COMMAND',
        action='append', default=[],
        help='Add a command line Hooke command to run.')
    options,arguments = p.parse_args()
    if len(arguments) > 0:
        print >> sys.stderr, 'More than 0 arguments to %s: %s' \
            % (sys.argv[0], arguments)
        p.print_help(sys.stderr)
        sys.exit(1)

    hooke = Hooke(debug=__debug__)
    runner = HookeRunner()

    if options.version == True:
        print version()
        sys.exit(0)
    if options.script != None:
        f = open(os.path.expanduser(options.script), 'r')
        options.commands.extend(f.readlines())
        f.close
    if len(options.commands) > 0:
        try:
            hooke = runner.run_lines(hooke, options.commands)
        finally:
            hooke.close()
        sys.exit(0)

    try:
        hooke = runner.run(hooke)
    finally:
        hooke.close()
