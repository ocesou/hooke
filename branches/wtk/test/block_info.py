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
>>> from uuid import uuid4
>>> from hooke.hooke import Hooke, HookeRunner
>>> h = Hooke()
>>> r = HookeRunner()
>>> h = r.run_lines(h, ['load_playlist test/data/test']) # doctest: +ELLIPSIS
<FilePlaylist test.hkp>
Success
<BLANKLINE>

>>> file_name = '%s.block' % uuid4()
>>> block_info_already_exists = os.path.exists(file_name)
>>> block_info_already_exists
False
>>> h = r.run_lines(h, ['block_info --output %s name columns "raw info.Scanner list.Serial n*"'
...                     % file_name]) # doctest: +ELLIPSIS, +REPORT_UDIFF
{'columns': ['z piezo (m)', 'deflection (m)'],
 'index': 0,
 'name': 'approach',
 'raw info': {'Scanner list': {'Serial number': '196PF'}}}
Success
<BLANKLINE>
>>> with open(file_name, 'r') as f:
...     text = f.read()
>>> if block_info_already_exists == False:
...    os.remove(file_name)
>>> print text  # doctest: +ELLIPSIS, +REPORT_UDIFF
picoforce.000:
  approach:
    columns: [z piezo (m), deflection (m)]
    index: 0
    name: approach
    raw info:
      Scanner list: {Serial number: 196PF}
  path: .../test/data/picoforce.000
<BLANKLINE>
"""
