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
>>> h = r.run_lines(h, ['delta --block retract 300 500']) # doctest: +ELLIPSIS, +REPORT_UDIFF
[('z piezo (m)', -4.699...e-08), ('deflection (m)', -1.836...e-09)]
Success
<BLANKLINE>
"""
