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
...     ['remove_cantilever_from_extension --distance_column "z piezo (m)" --deflection_column "deflection (m)"']
...     )
Success
<BLANKLINE>
>>> curve = h.playlists.current().current()
>>> approach = curve.data[0]
>>> approach.info['columns']
['z piezo (m)', 'deflection (m)', 'cantilever adjusted extension (m)']
>>> approach[:5,-1]  # doctest: +ELLIPSIS
Data([ -1.806...e-06,  -1.812...e-06,  -1.817...e-06,
        -1.823...e-06,  -1.828...e-06])
>>> approach[-5:,-1]  # doctest: +ELLIPSIS
Data([ -1.981...e-06,  -1.986...e-06,  -1.980...e-06,
        -1.974...e-06,  -1.975...e-06])

The large shift is due to the unzeroed input deflection.
"""
