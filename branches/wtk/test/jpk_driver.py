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
>>> import os.path
>>> from hooke.hooke import Hooke, HookeRunner
>>> h = Hooke()
>>> r = HookeRunner()
>>> playlist = os.path.join('test', 'data', 'vclamp_jpk', 'playlist')
>>> h = r.run_lines(h, ['load_playlist ' + playlist]) # doctest: +ELLIPSIS
<FilePlaylist playlist.hkp>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['curve_info']) # doctest: +ELLIPSIS, +REPORT_UDIFF
name: 2009.04.23-15.15.47.jpk
path: test/data/vclamp_jpk/2009.04.23-15.15.47.jpk
experiment: None
driver: <hooke.driver.jpk.JPKDriver object at 0x...>
filetype: None
note: 
blocks: 2
block sizes: [(4096, 6), (4096, 4)]
Success
<BLANKLINE>

Load the second curve, to test calibration file overriding.

>>> h = r.run_lines(h, ['next_curve'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['curve_info']) # doctest: +ELLIPSIS, +REPORT_UDIFF
name: 2009.04.23-15.21.39.jpk
path: test/data/vclamp_jpk/2009.04.23-15.21.39.jpk
experiment: None
driver: <hooke.driver.jpk.JPKDriver object at 0x...>
filetype: None
note: 
blocks: 3
block sizes: [(4096, 6), (2048, 3), (4096, 4)]
Success
<BLANKLINE>
"""
