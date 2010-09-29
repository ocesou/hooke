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

"""Define :class:`SelectionHandler` to handle
:class:`~hooke.interaction.SelectionRequest`\s.
"""

import wx

from ..dialog.selection import Selection
from . import Handler


class SelectionHandler (Handler):
    def __init__(self):
        super(SelectionHandler, self).__init__(name='selection')

    def run(self, hooke_frame, msg):
        self._canceled = True
        while self._canceled:
            s = Selection(
                options=msg.options,
                message=msg.msg,
                button_id=wxID_OK,
                callbacks={
                    'button': self._selection,
                    },
                default=msg.default,
                selection_style='single',
                parent=self,
                label='Selection handler',
                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        return self._selected

    def _selection(self, _class, method, options, selected):
        self._selected = selected
        self._canceled = False
