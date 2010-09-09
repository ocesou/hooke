# -*- coding: utf-8 -*-
#
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

u"""
>>> from hooke.hooke import Hooke, HookeRunner
>>> h = Hooke()
>>> r = HookeRunner()
>>> h = r.run_lines(h, ['help flat_filter_playlist']) # doctest: +REPORT_UDIFF +ELLIPSIS
Usage: flat_filter_playlist...
      F. Musiani, M. Brucale, L. Bubacco, B. Samorì.
      "Conformational equilibria in monomeric α-Synuclein at the
...
"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import hooke.util.encoding
hooke.util.encoding.get_encoding = lambda : 'utf-8'

# Override defaultencoding and get_encoding to work around
# doctest/unicode limitations:
#   Doctest: test.unicode_output
#   ... /usr/lib/python2.6/doctest.py:1475: UnicodeWarning: Unicode
#   equal comparison failed to convert both arguments to Unicode -
#   interpreting them as being unequal
#
# see
#   http://stackoverflow.com/questions/1733414/how-do-i-include-unicode-strings-in-python-doctests
# for details.
#
# Unfortunately, the override also makes the codecs.getwriter() code
# that this test is supposed to check a no-op.  Ah well, guess this
# will have to wait for Python 3.
