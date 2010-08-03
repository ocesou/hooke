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

"""Notebook panel for Hooke.
"""

import wx.aui as aui

from . import Panel
from .welcome import WelcomeWindow


class NotebookPanel (Panel, aui.AuiNotebook):
    def __init__(self, callbacks=None, **kwargs):
        super(Notebook, self).__init__(
            name='notebook', callbacks=callbacks, **kwargs)
        self.SetArtProvider(aui.AuiDefaultTabArt())
        #uncomment if we find a nice icon
        #page_bmp = wx.ArtProvider.GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, wx.Size(16, 16))
        self.AddPage(
            WelcomeWindow(
                parent=self,
                size=wx.Size(400, 300)),
            'Welcome')
