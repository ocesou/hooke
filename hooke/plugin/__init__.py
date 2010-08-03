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

"""The `plugin` module provides optional submodules that add new Hooke
commands.

All of the science happens in here.
"""

import ConfigParser as configparser

from ..config import Setting
from ..util.pluggable import IsSubclass, construct_graph


PLUGIN_MODULES = [
#    ('autopeak', True),
    ('convfilt', True),
    ('cut', True),
#    ('fclamp', True),
#    ('fit', True),
#    ('flatfilts-rolf', True),
    ('flatfilt', True),
#    ('jumpstat', True),
#    ('macro', True),
#    ('massanalysis', True),
#    ('multidistance', True),
#    ('multifit', True),
#    ('pcluster', True),
#    ('procplots', True),
#    ('review', True),
#    ('showconvoluted', True),
#    ('superimpose', True),
#    ('tccd', True),
#    ('tutorial', True),
    ('vclamp', True),
    ]
"""List of plugin modules and whether they should be included by
default.  TODO: autodiscovery
"""

BUILTIN_MODULES = [
    'config',
    'curve',
    'debug',
    'license',
    'note',
    'playlist',
    'playlists',
    'system',
    ]
"""List of builtin modules.  TODO: autodiscovery
"""

PLUGIN_SETTING_SECTION = 'plugins'
"""Name of the config section which controls plugin selection.
"""


# Plugins and settings

class Plugin (object):
    """A pluggable collection of Hooke commands.

    Fulfills the same role for Hooke that a software package does for
    an operating system.
    """
    def __init__(self, name):
        self.name = name
        self.setting_section = '%s plugin' % self.name
        self.config = {}
        self._commands = []

    def dependencies(self):
        """Return a list of names of :class:`Plugin`\s we require."""
        return []

    def default_settings(self):
        """Return a list of :class:`hooke.config.Setting`\s for any
        configurable plugin settings.

        The suggested section setting is::

            Setting(section=self.setting_section, help=self.__doc__)
        """
        return []

    def commands(self):
        """Return a list of :class:`hooke.command.Command`\s provided.
        """
        return list(self._commands)

class Builtin (Plugin):
    """A required collection of Hooke commands.

    These "core" plugins provide essential administrative commands
    (playlist handling, etc.).
    """
    pass

# Plugin utility functions

def argument_to_setting(section_name, argument):
    """Convert an :class:`~hooke.command.Argument` to a
    `~hooke.conf.Setting`.

    This is a lossy transition, because
    :class:`~hooke.command.Argument`\s store more information than
    `~hooke.conf.Setting`\s.
    """
    return Setting(section_name, option=argument.name, value=argument.default,
                   help=argument._help)

# Construct plugin dependency graph and load plugin instances.

PLUGIN_GRAPH = construct_graph(
    this_modname=__name__,
    submodnames=[name for name,include in PLUGIN_MODULES] + BUILTIN_MODULES,
    class_selector=IsSubclass(Plugin, blacklist=[Plugin, Builtin]))
"""Topologically sorted list of all possible :class:`Plugin`\s and
:class:`Builtin`\s.
"""

def default_settings():
    settings = [Setting(PLUGIN_SETTING_SECTION,
                        help='Enable/disable default plugins.')]
    for pnode in PLUGIN_GRAPH:
        if pnode.data.name in BUILTIN_MODULES:
            continue # builtin inclusion is not optional
        plugin = pnode.data
        default_include = [di for mod_name,di in PLUGIN_MODULES
                           if mod_name == plugin.name][0]
        help = 'Commands: ' + ', '.join([c.name for c in plugin.commands()])
        settings.append(Setting(
                section=PLUGIN_SETTING_SECTION,
                option=plugin.name,
                value=str(default_include),
                help=help,
                ))
    for pnode in PLUGIN_GRAPH:
        plugin = pnode.data
        settings.extend(plugin.default_settings())
    return settings

def load_graph(graph, config, include_section):
    items = []
    for node in graph:
        item = node.data
        try:
            include = config.getboolean(include_section, item.name)
        except configparser.NoOptionError:
            include = True # non-optional include (e.g. a Builtin)
        if include == True:
            try:
                item.config = dict(config.items(item.setting_section))
            except configparser.NoSectionError:
                pass
            items.append(item)
    return items
