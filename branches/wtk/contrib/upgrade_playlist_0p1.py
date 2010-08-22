#!/usr/bin/python
# Copyright

"""Upgrade version 0.1 playlists (XML) to the current Hooke playlist
file format.
"""

import sys
import xml.dom.minidom

import yaml

from hooke.playlist import FilePlaylist


class Converter (FilePlaylist):
    def _restore_key(self, key):
        """Restore keys encoded with :meth:`_clean_key`.
        """
        return key.replace(u'\u00B7', ' ')

    def _from_xml_doc(self, doc, identify=True):
        """Load a playlist from an :class:`xml.dom.minidom.Document`
        instance.
        """
        root = doc.documentElement
        for attribute,value in root.attributes.items():
            attribute = self._restore_key(attribute)
            if attribute == 'version':
                assert value == '0.1', \
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
        #self._digest = self.digest()
        for curve in self:
            curve.set_hooke(hooke)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print >> sys.stderr, 'usage: upgrade_playlist_0p1.py X.hkp [Y.hkp ...]'
        sys.exit(1)

    for path in sys.argv[1:]:
        p = Converter(drivers=None, path=path)
        p.load(identify=False)
        p.save()
