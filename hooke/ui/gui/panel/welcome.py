# Copyright

"""Welcome panel for Hooke.
"""

import wx

from . import Panel


class WelcomeWindow (wx.html.HtmlWindow):
    def __init__(self, *args, **kwargs):
        super(WelcomeWindow, self).__init__(self, *args, **kwargs)
        lines = [
            '<h1>Welcome to Hooke</h1>',
            '<h3>Features</h3>',
            '<ul>',
            '<li>View, annotate, measure force files</li>',
            '<li>Worm-like chain fit of force peaks</li>',
            '<li>Automatic convolution-based filtering of empty files</li>',
            '<li>Automatic fit and measurement of multiple force peaks</li>',
            '<li>Handles force-clamp force experiments (experimental)</li>',
            '<li>It is extensible through plugins and drivers</li>',
            '</ul>',
            '<p>See the <a href="%s">DocumentationIndex</a>'
            % 'http://code.google.com/p/hooke/wiki/DocumentationIndex',
            'for more information</p>',
            ]
        ctrl.SetPage('\n'.join(lines))

class WelcomePanel (Panel, wx.Panel):
    def __init__(self, callbacks=None, **kwargs):
        super(WelcomePanel, self).__init__(
            name='welcome', callbacks=callbacks, **kwargs)
        self._c = {
            'window': WelcomeWindow(
                parent=self,
                size=wx.Size(400, 300)),
            }
