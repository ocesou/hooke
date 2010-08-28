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

"""Menu bar for Hooke.
"""

import wx

from ...util.callback import callback, in_callback


class Menu (wx.Menu):
    """A `Bind`able version of :class:`wx.Menu`.

    From the `wxPython Style Guide`_, you can't do
    wx.Menu().Bind(...), so we hack around it by bubbling the Bind up
    to the closest parent :class:`wx.Frame`.

    .. _wxPython Style Guide:
      http://wiki.wxpython.org/wxPython%20Style%20Guide#line-101
    """
    def __init__(self, parent=None, **kwargs):
        self._parent = parent
        self._bindings = []
        super(Menu, self).__init__(**kwargs)

    def Bind(self, **kwargs):
        assert 'id' in kwargs, kwargs
        obj = self
        while not isinstance(obj, wx.Frame):
            obj = obj._parent
        obj.Bind(**kwargs)
        self._bindings.append(kwargs)

    def Unbind(self, **kwargs):
        assert 'id' in kwargs, kwargs
        try:
            self._bindings.remove(kwargs)
        except ValueError:
            pass
        kwargs.pop('handler', None)
        obj = self
        while not isinstance(obj, wx.Frame):
            obj = obj._parent
        obj.Unbind(**kwargs)

    def _unbind_all_items(self):
        for kwargs in self._bindings:
            self.Unbind(**kwargs)
        self._bindings = []


class MenuBar (wx.MenuBar):
    """A `Bind`able version of :class:`wx.MenuBar`.

    See :class:`Menu` for the motivation.
    """
    def __init__(self, parent=None, **kwargs):
        self._parent = parent
        super(MenuBar, self).__init__(**kwargs)

    def Append(self, menu, title):
        menu._parent = self
        super(MenuBar, self).Append(menu, title)


class FileMenu (Menu):
    def __init__(self, callbacks=None, **kwargs):
        super(FileMenu, self).__init__(**kwargs)
        if callbacks == None:
            callbacks = {}
        self._callbacks = callbacks
        self._c = {'exit': self.Append(wx.ID_EXIT)}
        self.Bind(event=wx.EVT_MENU, handler=self.close, id=wx.ID_EXIT)

    @callback
    def close(self, event):
        pass


class ViewMenu (Menu):
    def __init__(self, panels, callbacks=None, **kwargs):
        super(ViewMenu, self).__init__(**kwargs)
        if callbacks == None:
            callbacks = {}
        self._callbacks = callbacks
        self._c = {}
        for i,panelname in enumerate(sorted([p.managed_name for p in panels])):
            text = '%s\tF%d' % (panelname, i+4)
            self._c[panelname] = self.AppendCheckItem(id=wx.ID_ANY, text=text)
        for item in self._c.values():
            item.Check()
            self.Bind(event=wx.EVT_MENU, handler=self.view_panel, id=item.GetId())

    def view_panel(self, event):
        _id = event.GetId()
        item = self.FindItemById(_id)
        label = item.GetLabel()
        selected = item.IsChecked()
        in_callback(self, panel_name=label, visible=selected)


class PerspectiveMenu (Menu):
    def __init__(self, callbacks=None, **kwargs):
        super(PerspectiveMenu, self).__init__(**kwargs)
        if callbacks == None:
            callbacks = {}
        self._callbacks = callbacks
        self._c = {}

    def update(self, perspectives, selected):
        """Rebuild the perspectives menu.
        """
        self._unbind_all_items()
        for item in self.GetMenuItems():
            self.DeleteItem(item)
        self._c = {
            'save': self.Append(id=wx.ID_ANY, text='Save Perspective'),
            'delete': self.Append(id=wx.ID_ANY, text='Delete Perspective'),
            }
        self.Bind(event=wx.EVT_MENU, handler=self.save_perspective,
                  id=self._c['save'].GetId())
        self.Bind(event=wx.EVT_MENU, handler=self.delete_perspective,
                  id=self._c['delete'].GetId())
        self.AppendSeparator()
        for label in perspectives:
            self._c[label] = self.AppendRadioItem(id=wx.ID_ANY, text=label)
            self.Bind(event=wx.EVT_MENU, handler=self.select_perspective,
                      id=self._c[label].GetId())
            if label == selected:
                self._c[label].Check(True)

    @callback
    def save_perspective(self, event):
        pass

    @callback
    def delete_perspective(self, event):
        pass

    def select_perspective(self, event):
        _id = event.GetId()
        item = self.FindItemById(_id)
        label = item.GetLabel()
        selected = item.IsChecked()
        assert selected == True, label
        in_callback(self, name=label)


class HelpMenu (Menu):
    def __init__(self, callbacks=None, **kwargs):
        super(HelpMenu, self).__init__(**kwargs)
        if callbacks == None:
            callbacks = {}
        self._callbacks = callbacks
        self._c = {'about': self.Append(id=wx.ID_ABOUT)}
        self.Bind(event=wx.EVT_MENU, handler=self.about, id=wx.ID_ABOUT)

    @callback
    def about(self, event):
        pass


class HookeMenuBar (MenuBar):
    def __init__(self, panels, callbacks=None, **kwargs):
        super(HookeMenuBar, self).__init__(**kwargs)
        if callbacks == None:
            callbacks = {}
        self._callbacks = callbacks
        self._c = {}

        # Attach *Menu() instances
        for key in ['file', 'view', 'perspective', 'help']:
            cap_key = key.capitalize()
            hot_key = '&' + cap_key
            _class = globals()['%sMenu' % cap_key]
            kwargs = {}
            if key == 'view':
                kwargs['panels'] = panels
            self._c[key] = _class(parent=self, callbacks=callbacks, **kwargs)
            self.Append(self._c[key], hot_key)
