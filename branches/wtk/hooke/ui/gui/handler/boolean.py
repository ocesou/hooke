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

import wx

"""Define :class:`BooleanHandler` to handle
:class:`~hooke.interaction.BooleanRequest`\s.
"""

from . import Handler


class BooleanHandler (Handler):
    def __init__(self):
        super(BooleanHandler, self).__init__(name='boolean')

    def run(self, hooke_frame, msg):
        if msg.default == True:
            default = wx.YES_DEFAULT
        else:
            default = wx.NO_DEFAULT
        dialog = wx.MessageDialog(
            parent=self,
            message=msg.msg,
            caption='Boolean Handler',
            style=swx.YES_NO|default)
        dialog.ShowModal()
        dialog.Destroy()
        return value
