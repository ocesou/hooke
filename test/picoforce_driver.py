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
>>> playlist = os.path.join('test', 'data', 'vclamp_picoforce', 'playlist')
>>> h = r.run_lines(h, ['load_playlist ' + playlist])
<FilePlaylist playlist.hkp>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['curve_info']) # doctest: +ELLIPSIS, +REPORT_UDIFF
name: 20071120a_i27_t33.100
path: test/data/vclamp_picoforce/20071120a_i27_t33.100
experiment: <class 'hooke.experiment.VelocityClamp'>
driver: <hooke.driver.picoforce.PicoForceDriver object at 0x...>
filetype: picoforce
note: 
blocks: 2
block sizes: [(2048, 2), (2048, 2)]
Success
<BLANKLINE>

Also checkout the newer versions we have available.

>>> h = r.run_lines(h, ['previous_curve'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['curve_info']) # doctest: +ELLIPSIS, +REPORT_UDIFF
name: 0x07200000
path: test/data/vclamp_picoforce/0x07200000
experiment: <class 'hooke.experiment.VelocityClamp'>
driver: <hooke.driver.picoforce.PicoForceDriver object at 0x...>
filetype: picoforce
note: 
blocks: 2
block sizes: [(512, 2), (512, 2)]
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['previous_curve'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['curve_info']) # doctest: +ELLIPSIS, +REPORT_UDIFF
name: 0x06130001
path: test/data/vclamp_picoforce/0x06130001
experiment: <class 'hooke.experiment.VelocityClamp'>
driver: <hooke.driver.picoforce.PicoForceDriver object at 0x...>
filetype: picoforce
note: 
blocks: 2
block sizes: [(2048, 2), (2048, 2)]
Success
<BLANKLINE>
"""
