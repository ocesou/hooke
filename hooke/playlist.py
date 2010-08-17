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
import xml.dom.minidom

from . import curve as curve
from .compat import minidom as minidom  # dynamically patch xml.sax.minidom
from .util.itertools import reverse_enumerate


class NoteIndexList (list):
    """A list that keeps track of a "current" item and additional notes.

    :attr:`index` (i.e. "bookmark") is the index of the currently
    current curve.  Also keep a :class:`dict` of additional information
    (:attr:`info`).
    """
    def __init__(self, name=None):
        super(NoteIndexList, self).__init__()
        self.name = name
        self.info = {}
        self._index = 0

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        return u'<%s %s>' % (self.__class__.__name__, self.name)

    def __repr__(self):
        return self.__str__()

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

    def current(self):
        if len(self) == 0:
            return None
        item = self[self._index]
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
        :class:`~hooke.plugin.playlist.ApplyCommandStack`.  After the
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

    def filter(self, keeper_fn=lambda item:True, *args, **kwargs):
        c = copy.deepcopy(self)
        for item in c.items(reverse=True):
            if keeper_fn(item, *args, **kwargs) != True:
                c.remove(item)
        try: # attempt to maintain the same current item
            c._index = c.index(self.current())
        except ValueError:
            c._index = 0
        return c


class Playlist (NoteIndexList):
    """A :class:`NoteIndexList` of :class:`hooke.curve.Curve`\s.

    Keeps a list of :attr:`drivers` for loading curves.
    """
    def __init__(self, drivers, name=None):
        super(Playlist, self).__init__(name=name)
        self.drivers = drivers
        self._loaded = [] # List of loaded curves, see :meth:`._setup_item`.
        self._max_loaded = 100 # curves to hold in memory simultaneously.

    def append_curve_by_path(self, path, info=None, identify=True, hooke=None):
        path = os.path.normpath(path)
        c = curve.Curve(path, info=info)
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


class FilePlaylist (Playlist):
    """A file-backed :class:`Playlist`.
    """
    version = '0.1'

    def __init__(self, drivers, name=None, path=None):
        super(FilePlaylist, self).__init__(drivers, name)
        self.path = None
        self.set_path(path)
        self._digest = None
        self._ignored_keys = [
            'experiment',  # class instance, not very exciting.
            ]

    def set_path(self, path):
        if path != None:
            if not path.endswith('.hkp'):
                path += '.hkp'
            self.path = path
            if self.name == None:
                self.name = os.path.basename(path)

    def append_curve_by_path(self, path, *args, **kwargs):
        if self.path != None:
            path = os.path.join(os.path.dirname(self.path), path)
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
        >>> c = curve.Curve(os.path.join(root_path, 'to', 'curve', 'one'))
        >>> c.info['note'] = 'The first curve'
        >>> p.append(c)
        >>> c = curve.Curve(os.path.join(root_path, 'to', 'curve', 'two'))
        >>> c.info['note'] = 'The second curve'
        >>> p.append(c)
        >>> p.digest()
        '\\\x14\x87\x88*q\xf8\xaa\xa7\x84f\x82\xa1S>\xfd3+\xd0o'
        """
        string = self.flatten()
        return hashlib.sha1(string).digest()

    def _clean_key(self, key):
        """Replace spaces in keys with \\u00B7 (middle dot).

        This character is deemed unlikely to occur in keys to our
        playlist and curve info dictionaries, while many keys have
        spaces in them.

        \\u00B7 is allowed in XML 1.0 as of the 5th edition.  See
        the `4th edition errata`_ for details.

        .. _4th edition errata:
          http://www.w3.org/XML/xml-V10-4e-errata#E09
        """
        return key.replace(' ', u'\u00B7')

    def _restore_key(self, key):
        """Restore keys encoded with :meth:`_clean_key`.
        """
        return key.replace(u'\u00B7', ' ')

    def flatten(self, absolute_paths=False):
        """Create a string representation of the playlist.

        A playlist is an XML document with the following syntax::

            <?xml version="1.0" encoding="utf-8"?>
            <playlist attribute="value">
              <curve path="/my/file/path/"/ attribute="value" ...>
              <curve path="...">
            </playlist>

        Relative paths are interpreted relative to the location of the
        playlist file.

        Examples
        --------

        >>> root_path = os.path.sep + 'path'
        >>> p = FilePlaylist(drivers=[],
        ...                  path=os.path.join(root_path, 'to','playlist'))
        >>> p.info['note'] = 'An example playlist'
        >>> c = curve.Curve(os.path.join(root_path, 'to', 'curve', 'one'))
        >>> c.info['note'] = 'The first curve'
        >>> p.append(c)
        >>> c = curve.Curve(os.path.join(root_path, 'to', 'curve', 'two'))
        >>> c.info['attr with spaces'] = 'The second curve\\nwith endlines'
        >>> p.append(c)
        >>> def _print(string):
        ...     escaped_string = unicode(string, 'utf-8').encode('unicode escape')
        ...     print escaped_string.replace('\\\\n', '\\n').replace('\\\\t', '\\t'),
        >>> _print(p.flatten())  # doctest: +NORMALIZE_WHITESPACE +REPORT_UDIFF
        <?xml version="1.0" encoding="utf-8"?>
        <playlist index="0" note="An example playlist" version="0.1">
           <curve note="The first curve" path="curve/one"/>
           <curve attr\\xb7with\\xb7spaces="The second curve&#xA;with endlines" path="curve/two"/>
        </playlist>
        >>> _print(p.flatten(absolute_paths=True))  # doctest: +NORMALIZE_WHITESPACE +REPORT_UDIFF
        <?xml version="1.0" encoding="utf-8"?>
        <playlist index="0" note="An example playlist" version="0.1">
           <curve note="The first curve" path="/path/to/curve/one"/>
           <curve attr\\xb7with\\xb7spaces="The second curve&#xA;with endlines" path="/path/to/curve/two"/>
        </playlist>
        """
        implementation = xml.dom.minidom.getDOMImplementation()
        # create the document DOM object and the root element
        doc = implementation.createDocument(None, 'playlist', None)
        root = doc.documentElement
        root.setAttribute('version', self.version) # store playlist version
        root.setAttribute('index', str(self._index))
        for key,value in self.info.items(): # save info variables
            if (key in self._ignored_keys
                or not isinstance(value, types.StringTypes)):
                continue
            root.setAttribute(self._clean_key(key), str(value))
        for curve in self: # save curves and their attributes
            curve_element = doc.createElement('curve')
            root.appendChild(curve_element)
            path = os.path.abspath(os.path.expanduser(curve.path))
            if absolute_paths == False:
                path = os.path.relpath(
                    path,
                    os.path.dirname(
                        os.path.abspath(
                            os.path.expanduser(self.path))))
            curve_element.setAttribute('path', path)
            for key,value in curve.info.items():
                if (key in self._ignored_keys
                    or not isinstance(value, types.StringTypes)):
                    continue
                curve_element.setAttribute(self._clean_key(key), str(value))
        string = doc.toprettyxml(encoding='utf-8')
        root.unlink() # break circular references for garbage collection
        return string

    def _from_xml_doc(self, doc, identify=True):
        """Load a playlist from an :class:`xml.dom.minidom.Document`
        instance.
        """
        root = doc.documentElement
        for attribute,value in root.attributes.items():
            attribute = self._restore_key(attribute)
            if attribute == 'version':
                assert value == self.version, \
                    'Cannot read v%s playlist with a v%s reader' \
                    % (value, self.version)
            elif attribute == 'index':
                self._index = int(value)
            else:
                self.info[attribute] = value
        for curve_element in doc.getElementsByTagName('curve'):
            path = curve_element.getAttribute('path')
            info = dict([(self._restore_key(key), value)
                         for key,value in curve_element.attributes.items()])
            info.pop('path')
            self.append_curve_by_path(path, info, identify=identify)
        self.jump(self._index) # ensure valid index

    def from_string(self, string, identify=True):
        u"""Load a playlist from a string.

        Examples
        --------

        >>> string = '''<?xml version="1.0" encoding="utf-8"?>
        ... <playlist index="1" note="An example playlist" version="0.1">
        ...     <curve note="The first curve" path="../curve/one"/>
        ...     <curve attr\xb7with\xb7spaces="The second curve&#xA;with endlines" path="../curve/two"/>
        ... </playlist>
        ... '''
        >>> p = FilePlaylist(drivers=[],
        ...                  path=os.path.join('path', 'to', 'my', 'playlist'))
        >>> p.from_string(string, identify=False)
        >>> p._index
        1
        >>> p.info
        {u'note': u'An example playlist'}
        >>> for curve in p:
        ...     print curve.path
        path/to/curve/one
        path/to/curve/two
        >>> p[-1].info['attr with spaces']
        u'The second curve\\nwith endlines'
        """
        doc = xml.dom.minidom.parseString(string)
        self._from_xml_doc(doc, identify=identify)

    def load(self, path=None, identify=True, hooke=None):
        """Load a playlist from a file.
        """
        self.set_path(path)
        doc = xml.dom.minidom.parse(self.path)
        self._from_xml_doc(doc, identify=identify)
        self._digest = self.digest()
        for curve in self:
            curve.set_hooke(hooke)

    def save(self, path=None, makedirs=True):
        """Saves the playlist in a XML file.
        """
        self.set_path(path)
        dirname = os.path.dirname(self.path) or '.'
        if makedirs == True and not os.path.isdir(dirname):
            os.makedirs(dirname)
        with open(self.path, 'w') as f:
            f.write(self.flatten())
            self._digest = self.digest()
