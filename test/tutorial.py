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
Test the commands listed in :file:`doc/tutorial.txt`.

>>> import os
>>> import os.path
>>> from hooke.hooke import Hooke, HookeRunner
>>> h = Hooke()
>>> r = HookeRunner()

*Help*

>>> h = r.run_lines(h, ['help'])  # doctest: +ELLIPSIS
<BLANKLINE>
Documented commands (type help <topic>):
========================================
...
>>> h = r.run_lines(h, ['help load_playlist'])
Usage: load_playlist [options]
<BLANKLINE>
Options:
  -h, --help            show this help message and exit
  --disable-stack       Add this command to appropriate command stacks. (True)
  --output_playlist=OUTPUT_PLAYLIST
                        Name of the new playlist (defaults to an auto-
                        generated name). (None)
  --drivers=DRIVERS     Drivers for loading curves. (None)
<BLANKLINE>
Load a playlist.
<BLANKLINE>
----
Usage: load_playlist [options] input

*Creating a playlist*

>>> h = r.run_lines(h, ['cd --path .'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['pwd'])  # doctest: +ELLIPSIS
/.../hooke
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['ls'])  # doctest: +ELLIPSIS +REPORT_UDIFF
.hg
...
AUTHORS
...
README
...
hooke
...
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['new_playlist --output_playlist mylist'])
<FilePlaylist mylist>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['jump_to_playlist -- -1'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_playlist'])
<FilePlaylist mylist>
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
>>> playlist_already_exists = os.path.exists('mylist.hkp')
>>> playlist_already_exists
False
>>> h = r.run_lines(h, ['save_playlist --output mylist'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['name_playlist my_old_list'])
<FilePlaylist my_old_list>
Success
<BLANKLINE>
>>> os.path.isfile('mylist.hkp')
True
>>> h = r.run_lines(h, ['load_playlist mylist.hkp'])
<FilePlaylist mylist>
Success
<BLANKLINE>
>>> if playlist_already_exists == False:
...     os.remove('mylist.hkp')

*Navigating the playlist*

>>> h = r.run_lines(h, ['get_curve'])
<Curve 0x06130001>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['next_curve'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_curve'])
<Curve 0x07200000>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['previous_curve'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_curve'])
<Curve 0x06130001>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['curve_index'])
0
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['previous_curve'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_curve'])
<Curve 20071120a_i27_t33.199>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['curve_index'])
101
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['next_curve'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_curve'])
<Curve 0x06130001>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['curve_index'])
0
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['jump_to_curve 14'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_curve'])
<Curve 20071120a_i27_t33.112>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['curve_index'])
14
Success
<BLANKLINE>

>>> [p for p in h.playlists]
[<FilePlaylist my_old_list>, <FilePlaylist mylist>]
>>> h = r.run_lines(h, ['get_playlist'])
<FilePlaylist my_old_list>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['next_playlist'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_playlist'])
<FilePlaylist mylist>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['previous_playlist'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_playlist'])
<FilePlaylist my_old_list>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['playlist_index'])
0
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['previous_playlist'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_playlist'])
<FilePlaylist mylist>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['playlist_index'])
1
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['next_playlist'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_playlist'])
<FilePlaylist my_old_list>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['playlist_index'])
0
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['jump_to_playlist 1'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_playlist'])
<FilePlaylist mylist>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['playlist_index'])
1
Success
<BLANKLINE>

*Taking notes*

See :file:`note.py`.

*Exporting curves*

See :file:`export_block.py`.

*Measuring distances and forces*

See :file:`delta.py`.

*Worm like chain and freely jointed chain fitting*

*Command stacks*

See :file:`command_stack.py`,
:file:`apply_command_stack_to_playlist.py`, and
:file:`command_stack_save_load.py`.

*Multiple curve analysis*

See :file:`multiple_curve_analysis`.

*Configuring Hooke*

See :file:`config.py`.
"""
