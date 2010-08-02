# Copyright

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
