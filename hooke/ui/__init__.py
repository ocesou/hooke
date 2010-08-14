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

"""The `ui` module provides :class:`UserInterface` and various subclasses.
"""

import ConfigParser as configparser
import logging

from .. import version
from ..config import Setting
from ..util.pluggable import IsSubclass, construct_odict

try:
    from ..license import short_license
except ImportError, e:
    logging.warn('Could not load short_license from hooke.license')
    from .. import __license__
    def short_license(extra_info, **kwargs):
        return __license__


USER_INTERFACE_MODULES = [
    'commandline',
    'gui',
    ]
"""List of user interface modules.  TODO: autodiscovery
"""

USER_INTERFACE_SETTING_SECTION = 'user interfaces'
"""Name of the config section which controls UI selection.
"""


class UserInterface (object):
    """A user interface to drive the :class:`hooke.engine.CommandEngine`.
    """
    def __init__(self, name):
        self.name = name
        self.setting_section = '%s user interface' % (self.name)
        self.config = {}

    def default_settings(self):
        """Return a list of :class:`hooke.config.Setting`\s for any
        configurable UI settings.

        The suggested section setting is::

            Setting(section=self.setting_section, help=self.__doc__)
        """
        return []

    def reload_config(self, config):
        """Update the user interface for new config settings.

        Should be called with the new `config` upon recipt of
        `ReloadUserInterfaceConfig` from the `CommandEngine` or when
        loading the initial configuration.
        """
        try:
            self.config = dict(config.items(self.setting_section))
        except configparser.NoSectionError:
            self.config = {}

    def run(self, commands, ui_to_command_queue, command_to_ui_queue):
        return

    # Assorted useful tidbits for subclasses

    def _submit_command(self, command_message, ui_to_command_queue):
        log = logging.getLogger('hooke')
        log.debug('executing %s' % command_message)
        ui_to_command_queue.put(command_message)

    def _splash_text(self, extra_info, **kwargs):
        return ("""
Hooke version %s

%s
----
""" % (version(), short_license(extra_info, **kwargs))).strip()

    def _playlist_status(self, playlist):
        if len(playlist) > 0:
            return '%s (%s/%s)' % (playlist.name, playlist.index() + 1,
                                   len(playlist))
        return 'The playlist %s does not contain any valid force curve data.' \
            % self.name


USER_INTERFACES = construct_odict(
    this_modname=__name__,
    submodnames=USER_INTERFACE_MODULES,
    class_selector=IsSubclass(UserInterface, blacklist=[UserInterface]))
""":class:`hooke.compat.odict.odict` of :class:`UserInterface`
instances keyed by `.name`.
"""

def default_settings():
    settings = [Setting(USER_INTERFACE_SETTING_SECTION,
                        help='Select the user interface (only one).')]
    for i,ui in enumerate(USER_INTERFACES.values()):
        help = ui.__doc__.split('\n', 1)[0]
        settings.append(Setting(USER_INTERFACE_SETTING_SECTION,
                                ui.name, str(i==0), help=help))
        # i==0 to enable the first by default
    for ui in USER_INTERFACES.values():
        settings.extend(ui.default_settings())
    return settings

def load_ui(config, name=None):
    if name == None:
        uis = [c for c,v in config.items(USER_INTERFACE_SETTING_SECTION) if v == 'True']
        assert len(uis) == 1, 'Can only select one UI, not %d: %s' % (len(uis),uis)
        name = uis[0]
    ui = USER_INTERFACES[name]
    ui.reload_config(config)
    return ui
