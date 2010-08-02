# Copyright

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
