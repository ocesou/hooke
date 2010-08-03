# Copyright (C) 2010 Rolf Schmidt <rschmidt@alcor.concordia.ca>
#                    W. Trevor King <wking@drexel.edu>
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

"""Note panel for Hooke.
"""

import wx

from ....util.callback import callback, in_callback
from . import Panel


class NotePanel (Panel, wx.Panel):
    def __init__(self, callbacks=None, **kwargs):
        super(NotePanel, self).__init__(
            name='note', callbacks=callbacks, **kwargs)

        self._c = {
            'editor': wx.TextCtrl(
                parent=self,
                style=wx.TE_MULTILINE),
            'update': wx.Button(
                parent=self,
                label='Update note'),
            }
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self._c['editor'], 1, wx.EXPAND)
        sizer.Add(self._c['update'], 0, wx.EXPAND)
        self.SetSizer(sizer)
        self.SetAutoLayout(True)

        self.Bind(wx.EVT_BUTTON, self._on_update)

    def set_text(self, text):
        self._c['editor'].SetValue(text)

    def _on_update(self, event):
        text = self._c['editor'].GetValue()
        in_callback(self, text)
