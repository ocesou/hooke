# Copyright (C) 2010 Massimo Sandal <devicerandom@gmail.com>
#                    W. Trevor King <wking@drexel.edu>
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

"""Property editor panel for Hooke.

wxPropertyGrid is `included in wxPython >= 2.9.1 <included>`_.  Until
then, we'll avoid it because of the *nix build problems.

This module hacks together a workaround to be used until 2.9.1 is
widely installed (or at least released ;).

.. _included:
  http://wxpropgrid.sourceforge.net/cgi-bin/index?page=download
"""

import wx.grid

from . import Panel
from ....plugin import argument_to_setting
from ....util.convert import ANALOGS


def props_from_argument(argument, curves=None, playlists=None):
    """Convert a :class:`~hooke.command.Argument` to a list of
    :class:`Property`\s.
    """
    type = argument.type
    if type in ['driver']:  # intentionally not handled (yet)
        return None
    if argument.count == -1:
        raise NotImplementedError(argument)  # TODO: maybe just set count to 1?
    kwargs = {
        #'label':argument.name,
        'default':argument.default,
        'help':argument.help(),
        }
    type = ANALOGS.get(type, type)  # type consolidation
    # type handling
    if type in ['string', 'bool', 'int', 'float', 'path']:
        _class = globals()['%sProperty' % type.capitalize()]
    elif type in ['curve', 'playlist']:
        if type == 'curve':
            choices = curves  # extracted from the current playlist
        else:
            choices = playlists
        properties = []
        _class = ChoiceProperty
        kwargs['choices'] = choices
    else:
        raise NotImplementedError(argument.type)
    labels = ['%s %d' % (argument.name, i) for i in range(argument.count)]
    return [(label, _class(label=label, **kwargs)) for label in labels]
   

def props_from_setting(setting):
    """Convert a :class:`~hooke.config.Setting` to a list of
    :class:`Property`\s.
    """    
    # TODO: move props_from_argument code here and use
    # argument_to_setting there.
    raise NotImplementedError()


class Property (object):
    def __init__(self, type, label, default, help=None):
        self.type = type
        self.label = label
        self.default = default
        self.help = help

    def get_editor(self):
        """Return a suitable grid editor.
        """
        raise NotImplementedError()

    def get_renderer(self):
        """Return a suitable grid renderer.

        Returns `None` if no special renderer is required.
        """
        return None

    def string_for_value(self, value):
        """Return a string representation of `value` for loading the table.
        """
        return str(value)

    def value_for_string(self, string):
        """Return the value represented by `string`.
        """
        return string


class StringProperty (Property):
    def __init__(self, **kwargs):
        assert 'type' not in kwargs, kwargs
        if 'default' not in kwargs:
            kwargs['default'] = 0
        super(StringProperty, self).__init__(type='string', **kwargs)

    def get_editor(self):
        return wx.grid.GridCellTextEditor()

    def get_renderer(self):
        return wx.grid.GridCellStringRenderer()


class BoolProperty (Property):
    """A boolean property.

    Notes
    -----
    Unfortunately, changing a boolean property takes two clicks:

    1) create the editor
    2) change the value

    There are `ways around this`_, but it's not pretty.

    .. _ways around this:
      http://wiki.wxpython.org/Change%20wxGrid%20CheckBox%20with%20one%20click
    """
    def __init__(self, **kwargs):
        assert 'type' not in kwargs, kwargs
        if 'default' not in kwargs:
            kwargs['default'] = True
        super(BoolProperty, self).__init__(type='bool', **kwargs)

    def get_editor(self):
        return wx.grid.GridCellBoolEditor()

    def get_renderer(self):
        return wx.grid.GridCellBoolRenderer()

    def string_for_value(self, value):
        if value == True:
            return '1'
        return ''

    def value_for_string(self, string):
        return string == '1'


class IntProperty (Property):
    def __init__(self, **kwargs):
        assert 'type' not in kwargs, kwargs
        if 'default' not in kwargs:
            kwargs['default'] = 0
        super(IntProperty, self).__init__(type='int', **kwargs)

    def get_editor(self):
        return wx.grid.GridCellNumberEditor()

    def get_renderer(self):
        return wx.grid.GridCellNumberRenderer()

    def value_for_string(self, string):
        return int(string)


class FloatProperty (Property):
    def __init__(self, **kwargs):
        assert 'type' not in kwargs, kwargs
        if 'default' not in kwargs:
            kwargs['default'] = 0.0
        super(FloatProperty, self).__init__(type='float', **kwargs)

    def get_editor(self):
        return wx.grid.GridCellFloatEditor()

    def get_renderer(self):
        return wx.grid.GridCellFloatRenderer()

    def value_for_string(self, string):
        return float(string)


class ChoiceProperty (Property):
    def __init__(self, choices, **kwargs):
        assert 'type' not in kwargs, kwargs
        if 'default' in kwargs:
            if kwargs['default'] not in choices:
                choices.insert(0, kwargs['default'])
        else:
            kwargs['default'] = choices[0]
        super(ChoiceProperty, self).__init__(type='choice', **kwargs)
        self._choices = choices

    def get_editor(self):
        choices = [self.string_for_value(c) for c in self._choices]
        return wx.grid.GridCellChoiceEditor(choices=choices)

    def get_renderer(self):
        return None
        #return wx.grid.GridCellChoiceRenderer()

    def string_for_value(self, value):
        if hasattr(value, 'name'):
            return value.name
        return str(value)

    def value_for_string(self, string):
        for choice in self._choices:
            if self.string_for_value(choice) == string:
               return choice
        raise ValueError(string)


class PathProperty (StringProperty):
    """Simple file or path property.

    Currently there isn't a fancy file-picker popup.  Perhaps in the
    future.
    """
    def __init__(self, **kwargs):
        super(PathProperty, self).__init__(**kwargs)
        self.type = 'path'


class PropertyPanel(Panel, wx.grid.Grid):
    """UI to view/set config values and command argsuments.
    """
    def __init__(self, callbacks=None, **kwargs):
        super(PropertyPanel, self).__init__(
            name='property editor', callbacks=callbacks, **kwargs)
        self._properties = []

        self.CreateGrid(numRows=0, numCols=1)
        self.SetColLabelValue(0, 'value')

        self._last_tooltip = None
        self.GetGridWindow().Bind(wx.EVT_MOTION, self._on_motion)

    def _on_motion(self, event):
        """Enable tooltips.
        """
        x,y = self.CalcUnscrolledPosition(event.GetPosition())
        row,col = self.XYToCell(x, y)
        if col == -1 or row == -1:
            msg = ''
        else:
            msg = self._properties[row].help or ''
        if msg != self._last_tooltip:
            self._last_tooltip = msg
            event.GetEventObject().SetToolTipString(msg)

    def append_property(self, property):
        if len([p for p in self._properties if p.label == property.label]) > 0:
            raise ValueError(property)  # property.label collision
        self._properties.append(property)
        row = len(self._properties) - 1
        self.AppendRows(numRows=1)
        self.SetRowLabelValue(row, property.label)
        self.SetCellEditor(row=row, col=0, editor=property.get_editor())
        r = property.get_renderer()
        if r != None:
            self.SetCellRenderer(row=row, col=0, renderer=r)
        self.set_property(property.label, property.default)

    def remove_property(self, label):
        row,property = self._property_by_label(label)
        self._properties.pop(row)
        self.DeleteRows(pos=row)

    def clear(self):
        while(len(self._properties) > 0):
            self.remove_property(self._properties[-1].label)

    def set_property(self, label, value):
        row,property = self._property_by_label(label)
        self.SetCellValue(row=row, col=0, s=property.string_for_value(value))

    def get_property(self, label):
        row,property = self._property_by_label(label)
        string = self.GetCellValue(row=row, col=0)
        return property.value_for_string(string)

    def get_values(self):
        return dict([(p.label, self.get_property(p.label))
                     for p in self._properties])

    def _property_by_label(self, label):
        props = [(i,p) for i,p in enumerate(self._properties)
                 if p.label == label]
        assert len(props) == 1, props
        row,property = props[0]
        return (row, property)
