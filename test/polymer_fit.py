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

Prepare a curve for polymer fitting.

>>> h = r.run_lines(h, ['load_playlist test/data/test']) # doctest: +ELLIPSIS
<FilePlaylist test.hkp>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['zero_surface_contact_point --block retract']
...     ) # doctest: +ELLIPSIS, +REPORT_UDIFF
{'info':...'fitted parameters': [8.413...e-08, 2.812...e-10, 158.581...],...}
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['polynomial_flatten --block retract --deflection_column "surface deflection (m)" --degree 1'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['convert_distance_to_force --block retract --deflection_column "flattened deflection (m)"'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['remove_cantilever_from_extension --block retract'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['flat_filter_peaks --block retract --min_points 1']
...     )  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE
[<Peak flat filter peak 0 of surface deflection 510
  [ -1.065...e-09  -2.244...e-09]>,
 <Peak flat filter peak 1 of surface deflection 610
  [ -1.156...e-09  -8.840...e-10  -3.173...e-10  -7.480...e-10]>,
 <Peak flat filter peak 2 of surface deflection 704
  [ -7.933...e-10  -1.654...e-09]>,
 <Peak flat filter peak 3 of surface deflection 812
  [ -1.745...e-09]>,
 <Peak flat filter peak 4 of surface deflection 916 [ -2.085...e-09]>,
 <Peak flat filter peak 5 of surface deflection 1103
  [ -1.768...e-09  -8.885...e-09  -1.722...e-09]>]
Success
<BLANKLINE>

Fit the flat filter peaks with a polymer tension.

>>> h = r.run_lines(h, ['flat_peaks_to_polymer_peaks --block retract'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['polymer_fit_peaks --block retract'])
Success
<BLANKLINE>

Check the results.

>>> curve = h.playlists.current().current()
>>> retract = curve.data[1]
>>> retract.info['columns']  # doctest: +NORMALIZE_WHITESPACE
['z piezo (m)', 'deflection (m)',
 'surface distance (m)', 'surface deflection (m)',
 'flattened deflection (m)', 'deflection (N)',
 'cantilever adjusted extension (m)', 'flat filter peaks (m)',
 'polymer peak 0 (N)', 'polymer peak 1 (N)', 'polymer peak 2 (N)',
 'polymer peak 3 (N)', 'polymer peak 4 (N)', 'polymer peak 5 (N)']
>>> retract[:5,-2:]
Data([[ NaN,  NaN],
       [ NaN,  NaN],
       [ NaN,  NaN],
       [ NaN,  NaN],
       [ NaN,  NaN]])
>>> retract[1097:1103,-2:]  # doctest: +ELLIPSIS
Data([[             NaN,   5.2...e-10],
       [             NaN,   5...e-10],
       [             NaN,   6.1...e-10],
       [             NaN,   6.2...e-10],
       [             NaN,   7...e-10],
       [             NaN,              NaN]])
>>> retract[-5:,-2:]
Data([[ NaN,  NaN],
       [ NaN,  NaN],
       [ NaN,  NaN],
       [ NaN,  NaN],
       [ NaN,  NaN]])
"""
