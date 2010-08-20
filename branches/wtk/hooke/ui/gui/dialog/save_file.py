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

"""Define :func:`select_save_file`
"""

import os.path

import wx


def select_save_file(directory, name, extension=None, *args, **kwargs):
    """Get a filename from the user for saving data.

    1) Prompt the user for a name using `name` as the default.

       * If the user cancels, return `None`
       * If the selected name does not exist, return it.

    2) If the selected name already exists, ask for clobber
       confirmation.

       * If clobbering is ok, return the selected name.
       * Otherwise, return to (1).
    """
    def path(name):
        return os.path.join(directory, name+extension)
    def name_exists(name):
        os.path.exists(path(name))
        
    while True:
        dialog = wx.TextEntryDialog(*args, **kwargs)
        dialog.SetValue(name)
        if dialog.ShowModal() != wx.ID_OK:
            return  # abort
        name = dialog.GetValue()
        if not name_exists(name):
            return name
        dialogConfirm = wx.MessageDialog(
            parent=self,
            message='\n\n'.join(
                ['A file with this name already exists.',
                 'Do you want to replace it?']),
                caption='Confirm',
                style=wx.YES_NO|wx.ICON_QUESTION|wx.CENTER)
        if dialogConfirm.ShowModal() == wx.ID_YES:
            return name
