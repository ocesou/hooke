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
>>> playlist = os.path.join('test', 'data', 'vclamp_mfp3d', 'playlist')
>>> h = r.run_lines(h, ['load_playlist ' + playlist])
<FilePlaylist MFP3D>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['curve_info']) # doctest: +ELLIPSIS, +REPORT_UDIFF
name: Line0004Point0000.ibw
path: .../test/data/vclamp_mfp3d/Line0004Point0000.ibw
experiment: <hooke.experiment.VelocityClamp object at 0x...>
driver: <hooke.driver.mfp3d.MFP3DDriver object at 0x...>
filetype: mfp3d
note: None
command stack: []
blocks: 3
block sizes: [(491, 2), (497, 2), (105, 2)]
Success
<BLANKLINE>

Also checkout a newer Image* file.

>>> h = r.run_lines(h, ['previous_curve'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['curve_info']) # doctest: +ELLIPSIS, +REPORT_UDIFF
name: Image0396.ibw
path: .../test/data/vclamp_mfp3d/Image0396.ibw
experiment: <hooke.experiment.VelocityClamp object at 0x...>
driver: <hooke.driver.mfp3d.MFP3DDriver object at 0x...>
filetype: mfp3d
note: None
command stack: []
blocks: 3
block sizes: [(506, 3), (6, 3), (496, 3)]
Success
<BLANKLINE>
"""
