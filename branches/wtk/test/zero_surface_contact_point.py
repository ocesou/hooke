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
>>> h = r.run_lines(h, ['zero_surface_contact_point --block retract']
...     ) # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE, +REPORT_UDIFF
{...'fitted parameters': [8.413...e-08, 2.812...e-10, 158.581...],...}
Success
<BLANKLINE>
>>> curve = h.playlists.current().current()
>>> retract = curve.data[1]
>>> retract.info['columns']
['z piezo (m)', 'deflection (m)', 'surface distance (m)', 'surface deflection (m)']
>>> retract[:5,-2:]  # doctest: +ELLIPSIS
Data([[ -3.387...e-08,  -4.1686...e-08],
       [ -3.387...e-08,  -4.161...e-08],
       [ -3.356...e-08,  -4.157...e-08],
       [ -3.417...e-08,  -4.161...e-08],
       [ -3.387...e-08,  -4.161...e-08]])
>>> retract[-5:,-2:]  # doctest: +ELLIPSIS
Data([[  4.501...e-07,  -1.178...e-09],
       [  4.501...e-07,  -1.156...e-09],
       [  4.501...e-07,  -1.269...e-09],
       [  4.510...e-07,  -1.518...e-09],
       [  4.513...e-07,  -8.613...e-10]])
"""
