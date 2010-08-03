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
>>> playlist = os.path.join('test', 'data', 'fclamp_hemingway', 'playlist')
>>> h = r.run_lines(h, ['load_playlist ' + playlist]) # doctest: +ELLIPSIS
<FilePlaylist playlist.hkp>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['curve_info']) # doctest: +ELLIPSIS, +REPORT_UDIFF
name: 20080428_a53t-0-0-10.dat
path: test/data/fclamp_hemingway/20080428_a53t-0-0-10.dat
experiment: <class 'hooke.experiment.ForceClamp'>
driver: <hooke.driver.hemingway.HemingwayDriver object at 0x...>
filetype: hemingway
note: 
blocks: 1
block sizes: [(14798, 5)]
Success
<BLANKLINE>
"""
