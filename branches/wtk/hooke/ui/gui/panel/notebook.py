# Copyright

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
