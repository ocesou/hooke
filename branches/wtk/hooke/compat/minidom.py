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

"""Dynamically patch :mod:`xml.dom.minidom`'s attribute value escaping.

:meth:`xml.dom.minidom.Element.setAttribute` doesn't preform some
character escaping (see the `Python bug`_ and `XML specs`_).
Importing this module applies the suggested patch dynamically.

.. _Python bug: http://bugs.python.org/issue5752
.. _XML specs:
  http://www.w3.org/TR/2000/WD-xml-c14n-20000119.html#charescaping
"""

import logging
import xml.dom.minidom


def _write_data(writer, data, isAttrib=False):
    "Writes datachars to writer."
    if isAttrib:
        data = data.replace("\r", "&#xD;").replace("\n", "&#xA;")
        data = data.replace("\t", "&#x9;").replace('"', "&quot;")
    writer.write(data)
xml.dom.minidom._write_data = _write_data

def writexml(self, writer, indent="", addindent="", newl=""):
    # indent = current indentation
    # addindent = indentation to add to higher levels
    # newl = newline string
    writer.write(indent+"<" + self.tagName)

    attrs = self._get_attributes()
    a_names = attrs.keys()
    a_names.sort()

    for a_name in a_names:
        writer.write(" %s=\"" % a_name)
        _write_data(writer, attrs[a_name].value, isAttrib=True)
        writer.write("\"")
    if self.childNodes:
        writer.write(">%s"%(newl))
        for node in self.childNodes:
            node.writexml(writer,indent+addindent,addindent,newl)
        writer.write("%s</%s>%s" % (indent,self.tagName,newl))
    else:
        writer.write("/>%s"%(newl))
# For an introduction to overriding instance methods, see
#   http://irrepupavel.com/documents/python/instancemethod/
instancemethod = type(xml.dom.minidom.Element.writexml)
xml.dom.minidom.Element.writexml = instancemethod(
    writexml, None, xml.dom.minidom.Element)

logging.warn(
    'monkey patched xml.dom.minidom.Element and ._write_data for issue5752')
