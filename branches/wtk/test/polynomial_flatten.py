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
...     ['polynomial_flatten --distance_column "z piezo (m)" --deflection_column "deflection (m)"']
...     ) # doctest: +ELLIPSIS, +REPORT_UDIFF
Success
<BLANKLINE>
>>> curve = h.playlists.current().current()
>>> approach = curve.data[0]
>>> approach.info['columns']
['z piezo (m)', 'deflection (m)', 'flattened deflection (m)']
>>> approach[:5,-1]  # doctest: +ELLIPSIS
Data([ -3.603...e-08,  -3.566...e-08,  -3.539...e-08,
        -3.508...e-08,  -3.476...e-08])
>>> approach[-5:,-1]  # doctest: +ELLIPSIS
Data([  3.624...e-10,   5.884...e-10,   2.257...e-10,
        -9.157...e-11,  -9.027...e-13])

In practice you should zero your data before using
`polynomial flatten`, because it flattens all data with positive
 deflection, and you don't want it to flatten the contact region.
"""
