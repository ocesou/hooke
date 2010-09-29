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

"""The `playlist` module provides a :class:`Playlist` and its subclass
:class:`FilePlaylist` for manipulating lists of
:class:`hooke.curve.Curve`\s.
"""

import copy
import hashlib
import os
import os.path
import types

import yaml
from yaml.representer import RepresenterError

from .command_stack import CommandStack
from .curve import Curve
from .util.itertools import reverse_enumerate


class NoteIndexList (list):
    """A list that keeps track of a "current" item and additional notes.

    :attr:`index` (i.e. "bookmark") is the index of the currently
    current curve.  Also keep a :class:`dict` of additional information
    (:attr:`info`).
    """
    def __init__(self, name=None):
        super(NoteIndexList, self).__init__()
        self._set_default_attrs()
        self.__setstate__({'name': name})

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        return u'<%s %s>' % (self.__class__.__name__, self.name)

    def __repr__(self):
        return self.__str__()

    def _set_default_attrs(self):
        self._default_attrs = {
            'info': {},
            'name': None,
            '_index': 0,
            }

    def __getstate__(self):
        return self.__dict__.copy()

    def __setstate__(self, state):
        self._set_default_attrs()
        if state == True:
            return
        self.__dict__.update(self._default_attrs)
        try:
            self.__dict__.update(state)
        except TypeError, e:
            print state, type(state), e
        if self.info in [None, {}]:
            self.info = {}

    def _setup_item(self, item):
        """Perform any required initialization before returning an item.
        """
        pass

    def index(self, value=None, *args, **kwargs):
        """Extend `list.index`, returning the current index if `value`
        is `None`.
        """
        if value == None:
            return self._index
        return super(NoteIndexList, self).index(value, *args, **kwargs)

    def current(self, load=True):
        if len(self) == 0:
            return None
        item = self[self._index]
        if load == True:
            self._setup_item(item)
        return item

    def jump(self, index):
        if len(self) == 0:
            self._index = 0
        else:
            self._index = index % len(self)

    def next(self):
        self.jump(self._index + 1)

    def previous(self):
        self.jump(self._index - 1)

    def items(self, reverse=False):
        """Iterate through `self` calling `_setup_item` on each item
        before yielding.

        Notes
        -----
        Updates :attr:`_index` during the iteration so
        :func:`~hooke.plugin.curve.current_curve_callback` works as
        expected in :class:`~hooke.command.Command`\s called from
        :class:`~hooke.plugin.playlist.ApplyCommand`.  After the
        iteration completes, :attr:`_index` is restored to its
        original value.
        """
        index = self._index
        items = self
        if reverse == True:
            items = reverse_enumerate(self)
        else:
            items = enumerate(self)
        for i,item in items:
            self._index = i
            self._setup_item(item)
            yield item
        self._index = index

    def filter(self, keeper_fn=lambda item:True, load_curves=True,
               *args, **kwargs):
        c = copy.deepcopy(self)
        if load_curves == True:
            items = c.items(reverse=True)
        else:
            items = reversed(c)
        for item in items: 
            if keeper_fn(item, *args, **kwargs) != True:
                c.remove(item)
        try: # attempt to maintain the same current item
            c._index = c.index(self.current())
        except ValueError:
            c._index = 0
        return c


class Playlist (NoteIndexList):
    """A :class:`NoteIndexList` of :class:`hooke.Curve`\s.

    Keeps a list of :attr:`drivers` for loading curves.
    """
    def __init__(self, drivers, name=None):
        super(Playlist, self).__init__(name=name)
        self.drivers = drivers

    def _set_default_attrs(self):
        super(Playlist, self)._set_default_attrs()
        self._default_attrs['drivers'] = []
        # List of loaded curves, see :meth:`._setup_item`.
        self._default_attrs['_loaded'] = []
        self._default_attrs['_max_loaded'] = 100  # curves to hold in memory simultaneously.

    def __setstate__(self, state):
        super(Playlist, self).__setstate__(state)
        if self.drivers in [None, {}]:
            self.drivers = []
        if self._loaded in [None, {}]:
            self._loaded = []

    def append_curve(self, curve):
        self.append(curve)

    def append_curve_by_path(self, path, info=None, identify=True, hooke=None):
        path = os.path.normpath(path)
        c = Curve(path, info=info)
        c.set_hooke(hooke)
        if identify == True:
            c.identify(self.drivers)
        self.append(c)
        return c

    def _setup_item(self, curve):
        if curve != None and curve not in self._loaded:
            if curve not in self:
                self.append(curve)
            if curve.driver == None:
                c.identify(self.drivers)
            if curve.data == None:
                curve.load()
            self._loaded.append(curve)
            if len(self._loaded) > self._max_loaded:
                oldest = self._loaded.pop(0)
                oldest.unload()

    def unload(self, curve):
        "Inverse of .`_setup_item`."
        curve.unload()
        try:
            self._loaded.remove(curve)
        except ValueError:
            pass


def playlist_path(path):
    """Normalize playlist path extensions.

    Examples
    --------
    >>> print playlist_path('playlist')
    playlist.hkp
    >>> print playlist_path('playlist.hkp')
    playlist.hkp
    >>> print playlist_path(None)
    None
    """
    if path == None:
        return None
    if not path.endswith('.hkp'):
        path += '.hkp'
    return path


class FilePlaylist (Playlist):
    """A file-backed :class:`Playlist`.

    Examples
    --------

    >>> p = FilePlaylist(drivers=['Driver A', 'Driver B'])
    >>> p.append(Curve('dummy/path/A'))
    >>> p.append(Curve('dummy/path/B'))

    The data-type is pickleable, to ensure we can move it between
    processes with :class:`multiprocessing.Queue`\s.

    >>> import pickle
    >>> s = pickle.dumps(p)
    >>> z = pickle.loads(s)
    >>> for curve in z:
    ...     print curve
    <Curve A>
    <Curve B>
    >>> print z.drivers
    ['Driver A', 'Driver B']

    The data-type is also YAMLable (see :mod:`hooke.util.yaml`).

    >>> s = yaml.dump(p)
    >>> z = yaml.load(s)
    >>> for curve in z:
    ...     print curve
    <Curve A>
    <Curve B>
    >>> print z.drivers
    ['Driver A', 'Driver B']
    """
    version = '0.2'

    def __init__(self, drivers, name=None, path=None):
        super(FilePlaylist, self).__init__(drivers, name)
        self.path = self._base_path = None
        self.set_path(path)
        self.relative_curve_paths = True
        self._relative_curve_paths = False

    def _set_default_attrs(self):
        super(FilePlaylist, self)._set_default_attrs()
        self._default_attrs['relative_curve_paths'] = True
        self._default_attrs['_relative_curve_paths'] = False
        self._default_attrs['_digest'] = None

    def __getstate__(self):
        state = super(FilePlaylist, self).__getstate__()
        assert 'version' not in state, state
        state['version'] = self.version
        return state

    def __setstate__(self, state):
        if 'version' in state:
            version = state.pop('version')
            assert version == FilePlaylist.version, (
                'invalid version %s (%s) != %s (%s)'
                % (version, type(version),
                   FilePlaylist.version, type(FilePlaylist.version)))
        super(FilePlaylist, self).__setstate__(state)

    def set_path(self, path):
        orig_base_path = getattr(self, '_base_path', None)
        if path == None:
            if self._base_path == None:
                self._base_path = os.getcwd()
        else:
            path = playlist_path(path)
            self.path = path
            self._base_path = os.path.dirname(os.path.abspath(
                os.path.expanduser(self.path)))
            if self.name == None:
                self.name = os.path.basename(path)
        if self._base_path != orig_base_path:
            self.update_curve_paths()

    def update_curve_paths(self):
        for curve in self:
            curve.set_path(self._curve_path(curve.path))

    def _curve_path(self, path):
        if self._base_path == None:
            self._base_path = os.getcwd()
        path = os.path.join(self._base_path, path)
        if self._relative_curve_paths == True:
            path = os.path.relpath(path, self._base_path)
        return path

    def append_curve(self, curve):
        curve.set_path(self._curve_path(curve.path))
        super(FilePlaylist, self).append_curve(curve)

    def append_curve_by_path(self, path, *args, **kwargs):
        path = self._curve_path(path)
        super(FilePlaylist, self).append_curve_by_path(path, *args, **kwargs)

    def is_saved(self):
        return self.digest() == self._digest

    def digest(self):
        r"""Compute the sha1 digest of the flattened playlist
        representation.

        Examples
        --------

        >>> root_path = os.path.sep + 'path'
        >>> p = FilePlaylist(drivers=[],
        ...                  path=os.path.join(root_path, 'to','playlist'))
        >>> p.info['note'] = 'An example playlist'
        >>> c = Curve(os.path.join(root_path, 'to', 'curve', 'one'))
        >>> c.info['note'] = 'The first curve'
        >>> p.append_curve(c)
        >>> c = Curve(os.path.join(root_path, 'to', 'curve', 'two'))
        >>> c.info['note'] = 'The second curve'
        >>> p.append_curve(c)
        >>> p.digest()
        'f\xe26i\xb98i\x1f\xb61J7:\xf2\x8e\x1d\xde\xc3}g'
        """
        string = self.flatten()
        return hashlib.sha1(string).digest()

    def flatten(self):
        """Create a string representation of the playlist.

        A playlist is a YAML document with the following minimal syntax::

            !!python/object/new:hooke.playlist.FilePlaylist
            state:
              version: '0.2'
            listitems:
            - !!python/object:hooke.curve.Curve
              path: /path/to/curve/one
            - !!python/object:hooke.curve.Curve
              path: /path/to/curve/two

        Relative paths are interpreted relative to the location of the
        playlist file.

        Examples
        --------

        >>> from .engine import CommandMessage

        >>> root_path = os.path.sep + 'path'
        >>> p = FilePlaylist(drivers=[],
        ...                  path=os.path.join(root_path, 'to','playlist'))
        >>> p.info['note'] = 'An example playlist'
        >>> c = Curve(os.path.join(root_path, 'to', 'curve', 'one'))
        >>> c.info['note'] = 'The first curve'
        >>> p.append_curve(c)
        >>> c = Curve(os.path.join(root_path, 'to', 'curve', 'two'))
        >>> c.info['attr with spaces'] = 'The second curve\\nwith endlines'
        >>> c.command_stack.extend([
        ...         CommandMessage('command A', {'arg 0':0, 'arg 1':'X'}),
        ...         CommandMessage('command B', {'arg 0':1, 'curve':c}),
        ...         ])
        >>> p.append_curve(c)
        >>> print p.flatten()  # doctest: +REPORT_UDIFF
        # Hooke playlist version 0.2
        !!python/object/new:hooke.playlist.FilePlaylist
        listitems:
        - !!python/object:hooke.curve.Curve
          info: {note: The first curve}
          name: one
          path: curve/one
        - &id001 !!python/object:hooke.curve.Curve
          command_stack: !!python/object/new:hooke.command_stack.CommandStack
            listitems:
            - !!python/object:hooke.engine.CommandMessage
              arguments: {arg 0: 0, arg 1: X}
              command: command A
              explicit_user_call: true
            - !!python/object:hooke.engine.CommandMessage
              arguments:
                arg 0: 1
                curve: *id001
              command: command B
              explicit_user_call: true
          info: {attr with spaces: 'The second curve
        <BLANKLINE>
              with endlines'}
          name: two
          path: curve/two
        state:
          _base_path: /path/to
          info: {note: An example playlist}
          name: playlist.hkp
          path: /path/to/playlist.hkp
          version: '0.2'
        <BLANKLINE>
        >>> p.relative_curve_paths = False
        >>> print p.flatten()  # doctest: +REPORT_UDIFF
        # Hooke playlist version 0.2
        !!python/object/new:hooke.playlist.FilePlaylist
        listitems:
        - !!python/object:hooke.curve.Curve
          info: {note: The first curve}
          name: one
          path: /path/to/curve/one
        - &id001 !!python/object:hooke.curve.Curve
          command_stack: !!python/object/new:hooke.command_stack.CommandStack
            listitems:
            - !!python/object:hooke.engine.CommandMessage
              arguments: {arg 0: 0, arg 1: X}
              command: command A
              explicit_user_call: true
            - !!python/object:hooke.engine.CommandMessage
              arguments:
                arg 0: 1
                curve: *id001
              command: command B
              explicit_user_call: true
          info: {attr with spaces: 'The second curve
        <BLANKLINE>
              with endlines'}
          name: two
          path: /path/to/curve/two
        state:
          _base_path: /path/to
          info: {note: An example playlist}
          name: playlist.hkp
          path: /path/to/playlist.hkp
          relative_curve_paths: false
          version: '0.2'
        <BLANKLINE>
        """
        rcp = self._relative_curve_paths
        self._relative_curve_paths = self.relative_curve_paths
        self.update_curve_paths()
        self._relative_curve_paths = rcp

        yaml_string = yaml.dump(self, allow_unicode=True)
        self.update_curve_paths()
        return ('# Hooke playlist version %s\n' % self.version) + yaml_string

    def save(self, path=None, makedirs=True):
        """Saves the playlist to a YAML file.
        """
        self.set_path(path)
        dirname = os.path.dirname(self.path) or '.'
        if makedirs == True and not os.path.isdir(dirname):
            os.makedirs(dirname)
        with open(self.path, 'w') as f:
            f.write(self.flatten())
            self._digest = self.digest()


def from_string(string):
    u"""Load a playlist from a string.

    Examples
    --------

    Minimal example.

    >>> string = '''# Hooke playlist version 0.2
    ... !!python/object/new:hooke.playlist.FilePlaylist
    ... state:
    ...   version: '0.2'
    ... listitems:
    ... - !!python/object:hooke.curve.Curve
    ...   path: curve/one
    ... - !!python/object:hooke.curve.Curve
    ...   path: curve/two
    ... '''
    >>> p = from_string(string)
    >>> p.set_path('/path/to/playlist')
    >>> for curve in p:
    ...     print curve.name, curve.path
    one /path/to/curve/one
    two /path/to/curve/two

    More complicated example.

    >>> string = '''# Hooke playlist version 0.2
    ... !!python/object/new:hooke.playlist.FilePlaylist
    ... listitems:
    ... - !!python/object:hooke.curve.Curve
    ...   info: {note: The first curve}
    ...   name: one
    ...   path: /path/to/curve/one
    ... - &id001 !!python/object:hooke.curve.Curve
    ...   command_stack: !!python/object/new:hooke.command_stack.CommandStack
    ...     listitems:
    ...     - !!python/object:hooke.engine.CommandMessage
    ...       arguments: {arg 0: 0, arg 1: X}
    ...       command: command A
    ...     - !!python/object:hooke.engine.CommandMessage
    ...       arguments:
    ...         arg 0: 1
    ...         curve: *id001
    ...       command: command B
    ...   info: {attr with spaces: 'The second curve
    ... 
    ...       with endlines'}
    ...   name: two
    ...   path: /path/to/curve/two
    ... state:
    ...   _base_path: /path/to
    ...   _index: 1
    ...   info: {note: An example playlist}
    ...   name: playlist.hkp
    ...   path: /path/to/playlist.hkp
    ...   version: '0.2'
    ... '''
    >>> p = from_string(string)
    >>> p.set_path('/path/to/playlist')
    >>> p._index
    1
    >>> p.info
    {'note': 'An example playlist'}
    >>> for curve in p:
    ...     print curve.name, curve.path
    one /path/to/curve/one
    two /path/to/curve/two
    >>> p[-1].info['attr with spaces']
    'The second curve\\nwith endlines'
    >>> type(p[-1].command_stack)
    <class 'hooke.command_stack.CommandStack'>
    >>> p[0].command_stack
    []
    >>> type(p[0].command_stack)
    <class 'hooke.command_stack.CommandStack'>
    >>> p[-1].command_stack  # doctest: +NORMALIZE_WHITESPACE
    [<CommandMessage command A {arg 0: 0, arg 1: X}>,
     <CommandMessage command B {arg 0: 1, curve: <Curve two>}>]
    >>> type(p[1].command_stack)
    <class 'hooke.command_stack.CommandStack'>
    >>> c2 = p[-1]
    >>> c2.command_stack[-1].arguments['curve'] == c2
    True
    """
    return yaml.load(string)

def load(path=None, drivers=None, identify=True, hooke=None):
    """Load a playlist from a file.
    """
    path = playlist_path(path)
    with open(path, 'r') as f:
        text = f.read()
    playlist = from_string(text)
    playlist.set_path(path)
    playlist._digest = playlist.digest()
    if drivers != None:
        playlist.drivers = drivers
    playlist.set_path(path)
    for curve in playlist:
        curve.set_hooke(hooke)
        if identify == True:
            curve.identify(playlist.drivers)
    return playlist


class Playlists (NoteIndexList):
    """A :class:`NoteIndexList` of :class:`FilePlaylist`\s.
    """
    pass
