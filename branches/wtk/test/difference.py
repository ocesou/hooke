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
>>> from hooke.hooke import Hooke, HookeRunner
>>> h = Hooke()
>>> r = HookeRunner()
>>> h = r.run_lines(h, ['load_playlist test/data/test']) # doctest: +ELLIPSIS
<FilePlaylist test.hkp>
Success
<BLANKLINE>
>>> h = r.run_lines(h,
...     ['difference --block_A retract --block_B approach --column_A "deflection (m)"']
...     ) # doctest: +ELLIPSIS, +REPORT_UDIFF
Success
<BLANKLINE>
>>> curve = h.playlists.current().current()
>>> retract = curve.data[1]
>>> retract.info['columns']
['z piezo (m)', 'deflection (m)', 'difference of retract deflection and approach deflection (m)']
>>> retract[:5,-1]  # doctest: +ELLIPSIS
Data([ -3.898...e-09,  -4.193...e-09,  -4.420...e-09,
        -4.782...e-09,  -5.100...e-09])
>>> retract[-5:,-1]  # doctest: +ELLIPSIS
Data([  4.080...e-10,   2.040...e-10,   4.533...e-10,
         5.213...e-10,   1.088...e-09])

Note the differences are not near zero because the z piezo position
runs in opposite directions for the two blocks.
"""
