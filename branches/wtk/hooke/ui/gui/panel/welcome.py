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
