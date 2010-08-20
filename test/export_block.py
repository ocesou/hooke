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

"""
>>> import os
>>> import os.path
>>> from uuid import uuid4
>>> from hooke.hooke import Hooke, HookeRunner

>>> h = Hooke()
>>> r = HookeRunner()
>>> h = r.run_lines(h, ['load_playlist test/data/test']) # doctest: +ELLIPSIS
<FilePlaylist test.hkp>
Success
<BLANKLINE>
>>> file_name = '%s.dat' % uuid4()
>>> export_already_exists = os.path.exists(file_name)
>>> export_already_exists
False
>>> h = r.run_lines(h, ['export_block --output %s' % file_name])
Success
<BLANKLINE>
>>> with open(file_name, 'r') as f:
...     lines = f.readlines()
>>> if export_already_exists == False:
...    os.remove(file_name)
>>> print len(lines)
2049
>>> print ''.join(lines[:5]),  # doctest: +ELLIPSIS, +REPORT_UDIFF +NORMALIZE_WHITESPACE
# z piezo (m)  deflection (m)
-1.519...e-07  9.094...e-08
-1.513...e-07  9.130...e-08
-1.513...e-07  9.157...e-08
-1.507...e-07  9.189...e-08
"""
