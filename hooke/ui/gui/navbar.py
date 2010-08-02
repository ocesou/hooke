# Copyright

"""Navigation bar for Hooke.
"""

import wx

from ...util.callback import callback, in_callback


class NavBar (wx.ToolBar):
    def __init__(self, callbacks, *args, **kwargs):
        super(NavBar, self).__init__(*args, **kwargs)
        self.SetToolBitmapSize(wx.Size(16,16))
        self._c = {
            'previous': self.AddLabelTool(
                id=wx.ID_PREVIEW_PREVIOUS,
                label='Previous',
                bitmap=wx.ArtProvider_GetBitmap(
                    wx.ART_GO_BACK, wx.ART_OTHER, wx.Size(16, 16)),
                shortHelp='Previous curve'),
            'next': self.AddLabelTool(
                id=wx.ID_PREVIEW_NEXT,
                label='Next',
                bitmap=wx.ArtProvider_GetBitmap(
                    wx.ART_GO_FORWARD, wx.ART_OTHER, wx.Size(16, 16)),
                shortHelp='Next curve'),
            }
        self.Realize()
        self._callbacks = callbacks
        self.Bind(wx.EVT_TOOL, self._on_next, self._c['next'])
        self.Bind(wx.EVT_TOOL, self._on_previous, self._c['previous'])

    def _on_next(self, event):
        self.next()

    def _on_previous(self, event):
        self.previous()

    @callback
    def next(self):
        pass

    @callback
    def previous(self):
        pass


    
