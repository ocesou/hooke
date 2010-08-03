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

"""Scrolling text buffer panel for Hooke.
"""

import wx

from . import Panel


class OutputPanel (Panel, wx.TextCtrl):
    """Scrolling text buffer panel.
    """
    def __init__(self, name=None, callbacks=None, buffer_lines=1000, **kwargs):
        self._buffer_lines = buffer_lines
        if (kwargs.get('style') & wx.TE_READONLY == 0):
            raise NotImplementedError('%s assumes a readonly TextCtrl'
                                      % self.__class__.__name__)
        super(OutputPanel, self).__init__(
            name='output', callbacks=callbacks, **kwargs)

    def write(self, text):
        self.AppendText(text)
        self._limit_to_buffer()

    def _limit_to_buffer(self):
        """Limit number of lines retained in the buffer to `._buffer_lines`.
        """
        num_lines = self.GetNumberOfLines()
        line_index = num_lines - self._buffer_lines
        if line_index > 0:
            first_pos = 0  # character index for the first character to keep
            for i in range(line_index):
                first_pos += self.GetLineLength(i) + 1  # +1 for '\n'
            self.Remove(0, first_pos)


