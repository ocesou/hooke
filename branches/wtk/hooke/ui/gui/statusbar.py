# Copyright

"""Status bar for Hooke.
"""

import wx

from ... import version


class StatusBar (wx.StatusBar):
    def __init__(self, *args, **kwargs):
        super(StatusBar, self).__init__(*args, **kwargs)
        self.SetStatusWidths([-2, -3])
        self.SetStatusText('Ready', 0)
        self.SetStatusText(u'Welcome to Hooke (version %s)' % version(), 1)

    def set_playlist(self, playlist):
        self.SetStatusText(self._playlist_status(playlist), 0)

    def set_curve(self, curve):
        pass

    def _playlist_status(self, playlist):
        fields = [
            playlist.name,
            '(%d/%d)' % (playlist._index, len(playlist)),
            ]
        curve = playlist.current()
        if curve != None:
            fields.append(curve.name)
        return ' '.join(fields)
