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

"""Configuration defaults, read/write, and template file creation for
Hooke.
"""

import ConfigParser as configparser
import os.path
import textwrap
import unittest

from .compat.odict import odict as OrderedDict


DEFAULT_PATHS = [
    '/usr/share/hooke/hooke.cfg',
    '/etc/hooke/hooke.cfg',
    '~/.hooke.cfg',
    '.hooke.cfg',
    ]
"""We start with the system files, and work our way to the more
specific user files, so the user can override the sysadmin who
in turn overrides the developer defaults.
"""

class Setting (object):
    """An entry (section or option) in HookeConfigParser.
    """
    def __init__(self, section, option=None, value=None, help=None, wrap=True):
        self.section = section
        self.option = option
        self.value = str(value)
        self.help = help
        self.wrap = wrap

    def __eq__(self, other):
        for attr in ['__class__', 'section', 'option', 'value', 'help']:
            value = getattr(self, attr)
            o_value = getattr(other, attr)
            if o_value != value:
                return False
        return True

    def is_section(self):
        return self.option == None

    def is_option(self):
        return not self.is_section()

    def write(self, fp, value=None, comments=True, wrapper=None):
        if comments == True and self.help != None:
            text = self.help
            if self.wrap == True:
                if wrapper == None:
                    wrapper = textwrap.TextWrapper(
                        initial_indent='# ',
                        subsequent_indent='# ')
                text = wrapper.fill(text)
            else:
                text = '# ' + '\n# '.join(text.splitlines())
            fp.write(text.rstrip()+'\n')
        if self.is_section():
            fp.write("[%s]\n" % self.section)
        else:
            fp.write("%s = %s\n" % (self.option,
                                    str(value).replace('\n', '\n\t')))

DEFAULT_SETTINGS = [
    Setting('conditions', help='Default environmental conditions in case they are not specified in the force curve data.'),
    Setting('conditions', 'temperature', '301', help='Temperature in Kelvin'),
    # Logging settings
    Setting('loggers', help='Configure loggers, see\nhttp://docs.python.org/library/logging.html#configuration-file-format', wrap=False),
    Setting('loggers', 'keys', 'root, hooke', help='Hooke only uses the hooke logger, but other included modules may also use logging and you can configure their loggers here as well.'),
    Setting('handlers', help='Configure log handlers, see\nhttp://docs.python.org/library/logging.html#configuration-file-format', wrap=False),
    Setting('handlers', 'keys', 'hand1'),
    Setting('formatters', help='Configure log formatters, see\nhttp://docs.python.org/library/logging.html#configuration-file-format', wrap=False),
    Setting('formatters', 'keys', 'form1'),
    Setting('logger_root', help='Configure the root logger, see\nhttp://docs.python.org/library/logging.html#configuration-file-format', wrap=False),
    Setting('logger_root', 'level', 'NOTSET'),
    Setting('logger_root', 'handlers', 'hand1'),
    Setting('logger_hooke', help='Configure the hooke logger, see\nhttp://docs.python.org/library/logging.html#configuration-file-format', wrap=False),
    Setting('logger_hooke', 'level', 'DEBUG'),
    Setting('logger_hooke', 'handlers', 'hand1', help='No specific handlers here, just propagate up to the root logger'),
    Setting('logger_hooke', 'propagate', '0'),
    Setting('logger_hooke', 'qualname', 'hooke'),
    Setting('handler_hand1', help='Configure the default log handler, see\nhttp://docs.python.org/library/logging.html#configuration-file-format', wrap=False),
    Setting('handler_hand1', 'class', 'StreamHandler'),
    Setting('handler_hand1', 'level', 'NOTSET'),
    Setting('handler_hand1', 'formatter', 'form1'),
    Setting('handler_hand1', 'args', '(sys.stderr,)'),
    Setting('formatter_form1', help='Configure the default log formatter, see\nhttp://docs.python.org/library/logging.html#configuration-file-format', wrap=False),
    Setting('formatter_form1', 'format', '%(asctime)s %(levelname)s %(message)s'),
    Setting('formatter_form1', 'datefmt', '', help='Leave blank for ISO8601, e.g. "2003-01-23 00:29:50,411".'),
    Setting('formatter_form1', 'class', 'logging.Formatter'),
    ]

def get_setting(settings, match):
    """Return the first Setting object matching both match.section and
    match.option.
    """
    for s in settings:
        if s.section == match.section and s.option == match.option:
            return s
    return None

class HookeConfigParser (configparser.RawConfigParser):
    """A wrapper around configparser.RawConfigParser.

    You will probably only need .read and .write.

    Examples
    --------

    >>> import sys
    >>> c = HookeConfigParser(paths=DEFAULT_PATHS,
    ...                       default_settings=DEFAULT_SETTINGS)
    >>> c.write(sys.stdout) # doctest: +ELLIPSIS
    # Default environmental conditions in case they are not specified in
    # the force curve data.
    [conditions]
    # Temperature in Kelvin
    temperature = 301
    <BLANKLINE>
    # Configure loggers, see
    # http://docs.python.org/library/logging.html#configuration-file-format
    [loggers]
    # Hooke only uses the hooke logger, but other included modules may
    # also use logging and you can configure their loggers here as well.
    keys = root, hooke
    ...
    """
    def __init__(self, paths=None, default_settings=None, defaults=None,
                 dict_type=OrderedDict, indent='# ', **kwargs):
        # Can't use super() because RawConfigParser is a classic class
        #super(HookeConfigParser, self).__init__(defaults, dict_type)
        configparser.RawConfigParser.__init__(self, defaults, dict_type)
        if paths == None:
            paths = []
        self._config_paths = paths
        if default_settings == None:
            default_settings = []
        self._default_settings = default_settings
        for key in ['initial_indent', 'subsequent_indent']:
            if key not in kwargs:
                kwargs[key] = indent
        self._comment_textwrap = textwrap.TextWrapper(**kwargs)
        self._setup_default_settings()

    def _setup_default_settings(self):
        for setting in self._default_settings: #reversed(self._default_settings):
            # reversed cause: http://docs.python.org/library/configparser.html
            # "When adding sections or items, add them in the reverse order of
            # how you want them to be displayed in the actual file."
            if setting.section not in self.sections():
                self.add_section(setting.section)
            if setting.option != None:
                self.set(setting.section, setting.option, setting.value)

    def read(self, filenames=None):
        """Read and parse a filename or a list of filenames.

        If filenames is None, it defaults to ._config_paths.  If a
        filename is not in ._config_paths, it gets appended to the
        list.  We also run os.path.expanduser() on the input filenames
        internally so you don't have to worry about it.

        Files that cannot be opened are silently ignored; this is
        designed so that you can specify a list of potential
        configuration file locations (e.g. current directory, user's
        home directory, systemwide directory), and all existing
        configuration files in the list will be read.  A single
        filename may also be given.

        Return list of successfully read files.
        """
        if filenames == None:
            filenames = [os.path.expanduser(p) for p in self._config_paths]
        else:
            if isinstance(filenames, basestring):
                filenames = [filenames]
            paths = [os.path.abspath(os.path.expanduser(p))
                     for p in self._config_paths]
            for filename in filenames:
                if os.path.abspath(os.path.expanduser(filename)) not in paths:
                    self._config_paths.append(filename)
        # Can't use super() because RawConfigParser is a classic class
        #return super(HookeConfigParser, self).read(filenames)
        return configparser.RawConfigParser.read(self, filenames)

    def _write_setting(self, fp, section=None, option=None, value=None,
                       **kwargs):
        """Print, if known, a nicely wrapped comment form of a
        setting's .help.
        """
        match = get_setting(self._default_settings, Setting(section, option))
        if match == None:
            match = Setting(section, option, value, **kwargs)
        match.write(fp, value=value, wrapper=self._comment_textwrap)

    def write(self, fp=None, comments=True):
        """Write an .ini-format representation of the configuration state.

        This expands on RawConfigParser.write() by optionally adding
        comments when they are known (i.e. for ._default_settings).
        However, comments are not read in during a read, so .read(x)
        .write(x) may `not preserve comments`_.

        .. _not preserve comments: http://bugs.python.org/issue1410680

        Examples
        --------

        >>> import sys, StringIO
        >>> c = HookeConfigParser()
        >>> instring = '''
        ... # Some comment
        ... [section]
        ... option = value
        ...
        ... '''
        >>> c._read(StringIO.StringIO(instring), 'example.cfg')
        >>> c.write(sys.stdout)
        [section]
        option = value
        <BLANKLINE>
        """
        local_fp = fp == None
        if local_fp:
            fp = open(os.path.expanduser(self._config_paths[-1]), 'w')
        if self._defaults:
            self._write_setting(fp, configparser.DEFAULTSECT,
                                help="Miscellaneous options")
            for (key, value) in self._defaults.items():
                self._write_setting(fp, configparser.DEFAULTSECT, key, value)
            fp.write("\n")
        for section in self._sections:
            self._write_setting(fp, section)
            for (key, value) in self._sections[section].items():
                if key != "__name__":
                    self._write_setting(fp, section, key, value)
            fp.write("\n")
        if local_fp:
            fp.close()

    def optionxform(self, option):
        """

        Overrides lowercasing behaviour of
        :meth:`ConfigParser.RawConfigParser.optionxform`.
        """
        return option


class TestHookeConfigParser (unittest.TestCase):
    def test_queue_safe(self):
        """Ensure :class:`HookeConfigParser` is Queue-safe.
        """
        from multiprocessing import Queue
        q = Queue()
        a = HookeConfigParser(
            paths=DEFAULT_PATHS, default_settings=DEFAULT_SETTINGS)
        q.put(a)
        b = q.get(a)
        for attr in ['_dict', '_defaults', '_sections', '_config_paths',
                     '_default_settings']:
            a_value = getattr(a, attr)
            b_value = getattr(b, attr)
            self.failUnless(
                a_value == b_value,
                'HookeConfigParser.%s did not survive Queue: %s != %s'
                % (attr, a_value, b_value))
