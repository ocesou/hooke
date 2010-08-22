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
Point data_logger to our test data.

>>> import os
>>> import os.path
>>> import data_logger
>>> data_logger.DEFAULT_PATH = os.path.join(
...     os.getcwd(), 'test', 'data', 'vclamp_wtk')

Adjust Hooke in case we don't have calibcant installed.

>>> from hooke.hooke import Hooke, HookeRunner
>>> h = Hooke()
>>> h.config.set('wtk driver', 'cantilever calibration directory',
...              '$DEFAULT$/calibrate_cantilever')
>>> h.load_drivers()

Proceed with the test itself.

>>> r = HookeRunner()
>>> playlist = os.path.join('test', 'data', 'vclamp_wtk', 'playlist')
>>> h = r.run_lines(h, ['load_playlist ' + playlist])
<FilePlaylist WTK>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['curve_info']) # doctest: +ELLIPSIS, +REPORT_UDIFF
name: 20100504144209_unfold
path: .../test/data/vclamp_wtk/unfold/20100504/20100504144209_unfold
experiment: <hooke.experiment.VelocityClamp object at 0x...>
driver: <hooke.driver.wtk.WTKDriver object at 0x...>
filetype: wtk
note: None
command stack: []
blocks: 2
block sizes: [(810, 2), (8001, 2)]
Success
<BLANKLINE>
"""
