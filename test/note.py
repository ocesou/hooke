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

>>> h = r.run_lines(h, ['new_playlist --output_playlist mylist'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['glob_curves_to_playlist test/data/vclamp_picoforce/*']
...     )  # doctest: +ELLIPSIS
<Curve 0x06130001>
<Curve 0x07200000>
<Curve 20071120a_i27_t33.100>
<Curve 20071120a_i27_t33.101>
...
<Curve 20071120a_i27_t33.199>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['jump_to_curve 14'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['''set_note "Hi there.\\nI'm a note"'''])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['jump_to_curve 27'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['''set_note "I'm another note."'''])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['note_filter_playlist --output_playlist filtered'])
<FilePlaylist filtered>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_playlist'])
<FilePlaylist mylist>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['jump_to_playlist -- -1'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_playlist'])
<FilePlaylist filtered>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_curve'])
<Curve 20071120a_i27_t33.112>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['curve_index'])
0
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['jump_to_curve -- -1'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_curve'])
<Curve 20071120a_i27_t33.125>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['curve_index'])
1
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_note'])
I'm another note.
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['set_note ""'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_note'])
None
Success
<BLANKLINE>
"""
