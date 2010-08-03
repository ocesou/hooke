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
>>> h = r.run_lines(h, ['load_playlist test/data/vclamp_picoforce/playlist']) # doctest: +ELLIPSIS
<FilePlaylist playlist.hkp>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['flat_filter_playlist']) # doctest: +ELLIPSIS
<FilePlaylist playlist-0>
Success
<BLANKLINE>
>>> h.playlists.jump(-1)
>>> h.playlists.current().name
'playlist-0'
>>> h.playlists.current().path
'test/data/vclamp_picoforce/playlist-0.hkp'
>>> len(h.playlists.current())
0

Note: I just checked and there really are no interesting features in
the vclamp_picoforce data.  Sad.
"""
