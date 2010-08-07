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

"""Status bar for Hooke.
"""

import wx

from ... import version


class StatusBar (wx.StatusBar):
    def __init__(self, *args, **kwargs):
        super(StatusBar, self).__init__(*args, **kwargs)
        self.SetFieldsCount(2)
        self.SetStatusWidths([-2, -3])
        self.SetStatusText('Ready', 0)
        self.SetStatusText(u'Welcome to Hooke (version %s)' % version(), 1)

    def set_playlist(self, playlist):
        self.SetStatusText(self._playlist_status(playlist), 0)

    def set_curve(self, curve):
        pass

    def set_plot_text(self, text):
        self.SetStatusText(text, 1)

    def _playlist_status(self, playlist):
        fields = [
            playlist.name,
            '(%d/%d)' % (playlist.index(), len(playlist)),
            ]
        curve = playlist.current()
        if curve != None:
            fields.append(curve.name)
        return ' '.join(fields)
