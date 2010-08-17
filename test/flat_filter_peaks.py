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
...     ['zero_surface_contact_point --block retract']
...     ) # doctest: +ELLIPSIS, +REPORT_UDIFF
{'info':...}
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['flat_filter_peaks --block retract']
...     ) # doctest: +ELLIPSIS
[<Peak flat filter peak 0 of surface deflection 610 [ -1.156...e-09  -8.840...e-10  -3.173...e-10  -7.480...e-10]>]
Success
<BLANKLINE>
>>> curve = h.playlists.current().current()
>>> retract = curve.data[-1]
>>> retract.info['flat filter peaks']  # doctest: +ELLIPSIS
[<Peak flat filter peak 0 of surface deflection 610 [ -1.156...e-09  -8.840...e-10  -3.173...e-10  -7.480...e-10]>]
>>> retract.info['columns']
['z piezo (m)', 'deflection (m)', 'surface distance (m)', 'surface deflection (m)', 'flat filter peaks (m)']
>>> retract[:5,-1]  # doctest: +ELLIPSIS
Data([-0., -0., -0., -0., -0.])
>>> retract[609:615,-1]  # doctest: +ELLIPSIS
Data([  0.000...e+00,   2.380...e-09,   9.747...e-10,
        -2.266...e-10,   9.071...e-11,  -0.000...e+00])
>>> retract[-5:,-1]  # doctest: +ELLIPSIS
Data([-0., -0., -0., -0., -0.])
"""
