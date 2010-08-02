# Copyright

import wx

from . import Handler


class BooleanHandler (Handler):
    
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

