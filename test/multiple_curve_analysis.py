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

Setup a playlist to act on.

>>> h = r.run_lines(h, ['load_playlist test/data/vclamp_picoforce/playlist'])
<FilePlaylist playlist.hkp>
Success
<BLANKLINE>

Build the command stack.

>>> h = r.run_lines(h, [
...         'start_command_capture',
...         'zero_surface_contact_point --block retract',
...         'flat_filter_peaks --block retract --min_points 1',
...         'zero_surface_contact_point --block retract --ignore_after_last_peak_info_name "flat filter peaks"',
...         'convert_distance_to_force --block retract --deflection_column "surface deflection (m)"',
...         'remove_cantilever_from_extension --block retract',
...         'flat_peaks_to_polymer_peaks --block retract',
...         'polymer_fit_peaks --block retract',
...         'stop_command_capture',
...         ])  # doctest: +REPORT_UDIFF
Success
<BLANKLINE>
Success
<BLANKLINE>
Success
<BLANKLINE>
Success
<BLANKLINE>
Success
<BLANKLINE>
Success
<BLANKLINE>
Success
<BLANKLINE>
Success
<BLANKLINE>
Success
<BLANKLINE>

Apply the command stack.

>>> h = r.run_lines(h, ['apply_command_stack_to_playlist'])
Success
<BLANKLINE>

Verify successful application.

>>> curve = h.playlists.current().current()
>>> curve
<Curve 20071120a_i27_t33.100>
>>> for c in curve.command_stack:
...     print c  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE, +REPORT_UDIFF
<CommandMessage zero surface contact point {block: retract}>
<CommandMessage flat filter peaks {block: retract, min points: 1}>
<CommandMessage zero surface contact point {block: retract, ignore after last peak info name: flat filter peaks}>
<CommandMessage convert distance to force {block: retract, deflection column: surface deflection (m)}>
<CommandMessage remove cantilever from extension {block: retract}>
<CommandMessage flat peaks to polymer peaks {block: retract}>
<CommandMessage polymer fit peaks {block: retract}>
>>> for c in curve.data[-1].info['columns']:
...     print c  # doctest: +REPORT_UDIFF
z piezo (m)
deflection (m)
surface distance (m)
surface deflection (m)
flat filter peaks (m)
deflection (N)
cantilever adjusted extension (m)
polymer peak 0 (N)
>>> h.playlists.current().next()
>>> curve = h.playlists.current().current()
>>> curve
<Curve 20071120a_i27_t33.101>
>>> for c in curve.command_stack:
...     print c  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE, +REPORT_UDIFF
<CommandMessage zero surface contact point {block: retract}>
<CommandMessage flat filter peaks {block: retract, min points: 1}>
<CommandMessage zero surface contact point {block: retract, ignore after last peak info name: flat filter peaks}>
<CommandMessage convert distance to force {block: retract, deflection column: surface deflection (m)}>
<CommandMessage remove cantilever from extension {block: retract}>
<CommandMessage flat peaks to polymer peaks {block: retract}>
<CommandMessage polymer fit peaks {block: retract}>
>>> for c in curve.data[-1].info['columns']:
...     print c  # doctest: +REPORT_UDIFF
z piezo (m)
deflection (m)
surface distance (m)
surface deflection (m)
flat filter peaks (m)
deflection (N)
cantilever adjusted extension (m)
polymer peak 0 (N)
"""
