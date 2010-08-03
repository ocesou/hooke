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
"""

import sys
import os.path

import wx
import wx.propgrid as wxpg

# There are many comments and code fragments in here from the demo app.
# They should come in handy to expand the functionality in the future.

class Display (object):
    property_descriptor = []
    def __init__(self):
        pass

class ValueObject (object):
    def __init__(self):
        pass


class IntProperty2 (wxpg.PyProperty):
    """This is a simple re-implementation of wxIntProperty.
    """
    def __init__(self, label, name = wxpg.LABEL_AS_NAME, value=0):
        wxpg.PyProperty.__init__(self, label, name)
        self.SetValue(value)

    def GetClassName(self):
        return "IntProperty2"

    def GetEditor(self):
        return "TextCtrl"

    def GetValueAsString(self, flags):
        return str(self.GetValue())

    def PyStringToValue(self, s, flags):
        try:
            v = int(s)
            if self.GetValue() != v:
                return v
        except TypeError:
            if flags & wxpg.PG_REPORT_ERROR:
                wx.MessageBox("Cannot convert '%s' into a number."%s, "Error")
        return False

    def PyIntToValue(self, v, flags):
        if (self.GetValue() != v):
            return v


class PyFilesProperty(wxpg.PyArrayStringProperty):
    def __init__(self, label, name = wxpg.LABEL_AS_NAME, value=[]):
        wxpg.PyArrayStringProperty.__init__(self, label, name, value)
        self.SetValue(value)

    def OnSetValue(self, v):
        self.value = v
        self.display = ', '.join(self.value)

    def GetValueAsString(self, argFlags):
        return self.display

    def PyStringToValue(self, s, flags):
        return [a.strip() for a in s.split(',')]

    def OnEvent(self, propgrid, ctrl, event):
        if event.GetEventType() == wx.wxEVT_COMMAND_BUTTON_CLICKED:
            # Show dialog to select a string, call DoSetValue and
            # return True, if value changed.
            return True

        return False


class PyObjectPropertyValue:
    """\
    Value type of our sample PyObjectProperty. We keep a simple dash-delimited
    list of string given as argument to constructor.
    """
    def __init__(self, s=None):
        try:
            self.ls = [a.strip() for a in s.split('-')]
        except:
            self.ls = []

    def __repr__(self):
        return ' - '.join(self.ls)


class PyObjectProperty(wxpg.PyProperty):
    """\
    Another simple example. This time our value is a PyObject (NOTE: we can't
    return an arbitrary python object in DoGetValue. It cannot be a simple
    type such as int, bool, double, or string, nor an array or wxObject based.
    Dictionary, None, or any user-specified Python object is allowed).
    """
    def __init__(self, label, name = wxpg.LABEL_AS_NAME, value=None):
        wxpg.PyProperty.__init__(self, label, name)
        self.SetValue(value)

    def GetClassName(self):
        return self.__class__.__name__

    def GetEditor(self):
        return "TextCtrl"

    def GetValueAsString(self, flags):
        return repr(self.GetValue())

    def PyStringToValue(self, s, flags):
        return PyObjectPropertyValue(s)


class ShapeProperty(wxpg.PyEnumProperty):
    """\
    Demonstrates use of OnCustomPaint method.
    """
    def __init__(self, label, name = wxpg.LABEL_AS_NAME, value=-1):
        wxpg.PyEnumProperty.__init__(self, label, name, ['Line','Circle','Rectangle'], [0,1,2], value)

    def OnMeasureImage(self, index):
        return wxpg.DEFAULT_IMAGE_SIZE

    def OnCustomPaint(self, dc, rect, paint_data):
        """\
        paint_data.m_choiceItem is -1 if we are painting the control,
        in which case we need to get the drawn item using DoGetValue.
        """
        item = paint_data.m_choiceItem
        if item == -1:
            item = self.DoGetValue()

        dc.SetPen(wx.Pen(wx.BLACK))
        dc.SetBrush(wx.Brush(wx.BLACK))

        if item == 0:
            dc.DrawLine(rect.x,rect.y,rect.x+rect.width,rect.y+rect.height)
        elif item == 1:
            half_width = rect.width / 2
            dc.DrawCircle(rect.x+half_width,rect.y+half_width,half_width-3)
        elif item == 2:
            dc.DrawRectangle(rect.x, rect.y, rect.width, rect.height)


class LargeImagePickerCtrl(wx.Window):
    """\
    Control created and used by LargeImageEditor.
    """
    def __init__(self):
        pre = wx.PreWindow()
        self.PostCreate(pre)

    def Create(self, parent, id_, pos, size, style = 0):
        wx.Window.Create(self, parent, id_, pos, size, style | wx.BORDER_SIMPLE)
        img_spc = size[1]
        self.tc = wx.TextCtrl(self, -1, "", (img_spc,0), (2048,size[1]), wx.BORDER_NONE)
        self.SetBackgroundColour(wx.WHITE)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.property = None
        self.bmp = None
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self)

        whiteBrush = wx.Brush(wx.WHITE)
        dc.SetBackground(whiteBrush)
        dc.Clear()

        bmp = self.bmp
        if bmp:
            dc.DrawBitmap(bmp, 2, 2)
        else:
            dc.SetPen(wx.Pen(wx.BLACK))
            dc.SetBrush(whiteBrush)
            dc.DrawRectangle(2, 2, 64, 64)

    def RefreshThumbnail(self):
        """\
        We use here very simple image scaling code.
        """
        if not self.property:
            self.bmp = None
            return

        path = self.property.DoGetValue()

        if not os.path.isfile(path):
            self.bmp = None
            return

        image = wx.Image(path)
        image.Rescale(64, 64)
        self.bmp = wx.BitmapFromImage(image)

    def SetProperty(self, property):
        self.property = property
        self.tc.SetValue(property.GetDisplayedString())
        self.RefreshThumbnail()

    def SetValue(self, s):
        self.RefreshThumbnail()
        self.tc.SetValue(s)

    def GetLastPosition(self):
        return self.tc.GetLastPosition()


class LargeImageEditor(wxpg.PyEditor):
    """\
    Double-height text-editor with image in front.
    """
    def __init__(self):
        wxpg.PyEditor.__init__(self)

    def CreateControls(self, propgrid, property, pos, sz):
        try:
            h = 64 + 6
            x = propgrid.GetSplitterPosition()
            x2 = propgrid.GetClientSize().x
            bw = propgrid.GetRowHeight()
            lipc = LargeImagePickerCtrl()
            if sys.platform == 'win32':
                lipc.Hide()
            lipc.Create(propgrid, wxpg.PG_SUBID1, (x,pos[1]), (x2-x-bw,h))
            lipc.SetProperty(property)
            # Hmmm.. how to have two-stage creation without subclassing?
            #btn = wx.PreButton()
            #pre = wx.PreWindow()
            #self.PostCreate(pre)
            #if sys.platform == 'win32':
            #    btn.Hide()
            #btn.Create(propgrid, wxpg.PG_SUBID2, '...', (x2-bw,pos[1]), (bw,h), wx.WANTS_CHARS)
            btn = wx.Button(propgrid, wxpg.PG_SUBID2, '...', (x2-bw,pos[1]), (bw,h), wx.WANTS_CHARS)
            return (lipc, btn)
        except:
            import traceback
            print traceback.print_exc()

    def UpdateControl(self, property, ctrl):
        ctrl.SetValue(property.GetDisplayedString())

    def DrawValue(self, dc, property, rect):
        if not (property.GetFlags() & wxpg.PG_PROP_AUTO_UNSPECIFIED):
            dc.DrawText( property.GetDisplayedString(), rect.x+5, rect.y );

    def OnEvent(self, propgrid, ctrl, event):
        if not ctrl:
            return False

        evtType = event.GetEventType()

        if evtType == wx.wxEVT_COMMAND_TEXT_ENTER:
            if propgrid.IsEditorsValueModified():
                return True

        elif evtType == wx.wxEVT_COMMAND_TEXT_UPDATED:
            if not property.HasFlag(wxpg.PG_PROP_AUTO_UNSPECIFIED) or not ctrl or \
               ctrl.GetLastPosition() > 0:

                # We must check this since an 'empty' text event
                # may be triggered when creating the property.
                PG_FL_IN_SELECT_PROPERTY = 0x00100000
                if not (propgrid.GetInternalFlags() & PG_FL_IN_SELECT_PROPERTY):
                    event.Skip();
                    event.SetId(propgrid.GetId());

                propgrid.EditorsValueWasModified();

        return False


    def CopyValueFromControl(self, property, ctrl):
        tc = ctrl.tc
        res = property.SetValueFromString(tc.GetValue(),0)
        # Changing unspecified always causes event (returning
        # true here should be enough to trigger it).
        if not res and property.IsFlagSet(wxpg.PG_PROP_AUTO_UNSPECIFIED):
            res = True

        return res

    def SetValueToUnspecified(self, ctrl):
        ctrl.tc.Remove(0,len(ctrl.tc.GetValue()));

    def SetControlStringValue(self, ctrl, txt):
        ctrl.SetValue(txt)

    def OnFocus(self, property, ctrl):
        ctrl.tc.SetSelection(-1,-1)
        ctrl.tc.SetFocus()


class PropertyEditor(wx.Panel):

    def __init__(self, parent):
        # Use the WANTS_CHARS style so the panel doesn't eat the Return key.
        wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS, size=(160, 200))

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.pg = wxpg.PropertyGrid(self, style=wxpg.PG_SPLITTER_AUTO_CENTER|wxpg.PG_AUTO_SORT)

        # Show help as tooltips
        self.pg.SetExtraStyle(wxpg.PG_EX_HELP_AS_TOOLTIPS)

        #pg.Bind(wxpg.EVT_PG_CHANGED, self.OnPropGridChange)
        #pg.Bind(wxpg.EVT_PG_SELECTED, self.OnPropGridSelect)
        #self.pg.Bind(wxpg.EVT_PG_RIGHT_CLICK, self.OnPropGridRightClick)

        # Needed by custom image editor
        wx.InitAllImageHandlers()

        #
        # Let's create a simple custom editor
        #
        # NOTE: Editor must be registered *before* adding a property that uses it.
        self.pg.RegisterEditor(LargeImageEditor)

        '''
        #
        # Add properties
        #

        pg.Append( wxpg.PropertyCategory("1 - Basic Properties") )
        pg.Append( wxpg.StringProperty("String",value="Some Text") )
        pg.Append( wxpg.IntProperty("Int",value=100) )
        pg.Append( wxpg.FloatProperty("Float",value=100.0) )
        pg.Append( wxpg.BoolProperty("Bool",value=True) )
        pg.Append( wxpg.BoolProperty("Bool_with_Checkbox",value=True) )
        pg.SetPropertyAttribute("Bool_with_Checkbox", "UseCheckbox", True)

        pg.Append( wxpg.PropertyCategory("2 - More Properties") )
        pg.Append( wxpg.LongStringProperty("LongString",value="This is a\\nmulti-line string\\nwith\\ttabs\\nmixed\\tin.") )
        pg.Append( wxpg.DirProperty("Dir",value="C:\\Windows") )
        pg.Append( wxpg.FileProperty("File",value="C:\\Windows\\system.ini") )
        pg.Append( wxpg.ArrayStringProperty("ArrayString",value=['A','B','C']) )

        pg.Append( wxpg.EnumProperty("Enum","Enum",
                                     ['wxPython Rules','wxPython Rocks','wxPython Is The Best'],
                                     [10,11,12],0) )
        pg.Append( wxpg.EditEnumProperty("EditEnum","EditEnumProperty",['A','B','C'],[0,1,2],"Text Not in List") )

        pg.Append( wxpg.PropertyCategory("3 - Advanced Properties") )
        pg.Append( wxpg.DateProperty("Date",value=wx.DateTime_Now()) )
        pg.Append( wxpg.FontProperty("Font",value=self.GetFont()) )
        pg.Append( wxpg.ColourProperty("Colour",value=self.GetBackgroundColour()) )
        pg.Append( wxpg.SystemColourProperty("SystemColour") )
        pg.Append( wxpg.ImageFileProperty("ImageFile") )
        pg.Append( wxpg.MultiChoiceProperty("MultiChoice",choices=['wxWidgets','QT','GTK+']) )

        pg.Append( wxpg.PropertyCategory("4 - Additional Properties") )
        pg.Append( wxpg.PointProperty("Point",value=self.GetPosition()) )
        pg.Append( wxpg.SizeProperty("Size",value=self.GetSize()) )
        pg.Append( wxpg.FontDataProperty("FontData") )
        pg.Append( wxpg.IntProperty("IntWithSpin",value=256) )
        pg.SetPropertyEditor("IntWithSpin","SpinCtrl")
        pg.Append( wxpg.DirsProperty("Dirs",value=['C:/Lib','C:/Bin']) )
        pg.SetPropertyHelpString( "String", "String Property help string!" )
        pg.SetPropertyHelpString( "Dirs", "Dirs Property help string!" )

        pg.SetPropertyAttribute( "File", wxpg.PG_FILE_SHOW_FULL_PATH, 0 )
        pg.SetPropertyAttribute( "File", wxpg.PG_FILE_INITIAL_PATH, "C:\\Program Files\\Internet Explorer" )
        pg.SetPropertyAttribute( "Date", wxpg.PG_DATE_PICKER_STYLE, wx.DP_DROPDOWN|wx.DP_SHOWCENTURY )

        pg.Append( wxpg.PropertyCategory("5 - Custom Properties") )
        pg.Append( IntProperty2("IntProperty2", value=1024) )

        pg.Append( ShapeProperty("ShapeProperty", value=0) )
        pg.Append( PyObjectProperty("PyObjectProperty") )

        pg.Append( wxpg.ImageFileProperty("ImageFileWithLargeEditor") )
        pg.SetPropertyEditor("ImageFileWithLargeEditor", "LargeImageEditor")


        pg.SetPropertyClientData( "Point", 1234 )
        if pg.GetPropertyClientData( "Point" ) != 1234:
            raise ValueError("Set/GetPropertyClientData() failed")

        # Test setting unicode string
        pg.GetPropertyByName("String").SetValue(u"Some Unicode Text")

        #
        # Test some code that *should* fail (but not crash)
        #try:
            #a_ = pg.GetPropertyValue( "NotARealProperty" )
            #pg.EnableProperty( "NotAtAllRealProperty", False )
            #pg.SetPropertyHelpString( "AgaintNotARealProperty", "Dummy Help String" )
        #except:
            #pass
            #raise

        '''
        sizer.Add(self.pg, 1, wx.EXPAND)
        self.SetSizer(sizer)
        sizer.SetSizeHints(self)

        self.SelectedTreeItem = None

    def GetPropertyValues(self):
        return self.pg.GetPropertyValues()

    def Initialize(self, properties):
        pg = self.pg
        pg.Clear()

        if properties:
            for element in properties:
                if element[1]['type'] == 'arraystring':
                    elements = element[1]['elements']
                    if 'value' in element[1]:
                        property_value = element[1]['value']
                    else:
                        property_value = element[1]['default']
                    #retrieve individual strings
                    property_value = split(property_value, ' ')
                    #remove " delimiters
                    values = [value.strip('"') for value in property_value]
                    pg.Append(wxpg.ArrayStringProperty(element[0], value=values))

                if element[1]['type'] == 'boolean':
                    if 'value' in element[1]:
                        property_value = element[1].as_bool('value')
                    else:
                        property_value = element[1].as_bool('default')
                    property_control = wxpg.BoolProperty(element[0], value=property_value)
                    pg.Append(property_control)
                    pg.SetPropertyAttribute(element[0], 'UseCheckbox', True)

                #if element[0] == 'category':
                    #pg.Append(wxpg.PropertyCategory(element[1]))

                if element[1]['type'] == 'color':
                    if 'value' in element[1]:
                        property_value = element[1]['value']
                    else:
                        property_value = element[1]['default']
                    property_value = eval(property_value)
                    pg.Append(wxpg.ColourProperty(element[0], value=property_value))

                if element[1]['type'] == 'enum':
                    elements = element[1]['elements']
                    if 'value' in element[1]:
                        property_value = element[1]['value']
                    else:
                        property_value = element[1]['default']
                    pg.Append(wxpg.EnumProperty(element[0], element[0], elements, [], elements.index(property_value)))

                if element[1]['type'] == 'filename':
                    if 'value' in element[1]:
                        property_value = element[1]['value']
                    else:
                        property_value = element[1]['default']
                    pg.Append(wxpg.FileProperty(element[0], value=property_value))

                if element[1]['type'] == 'float':
                    if 'value' in element[1]:
                        property_value = element[1].as_float('value')
                    else:
                        property_value = element[1].as_float('default')
                    property_control = wxpg.FloatProperty(element[0], value=property_value)
                    pg.Append(property_control)

                if element[1]['type'] == 'folder':
                    if 'value' in element[1]:
                        property_value = element[1]['value']
                    else:
                        property_value = element[1]['default']
                    pg.Append(wxpg.DirProperty(element[0], value=property_value))

                if element[1]['type'] == 'integer':
                    if 'value' in element[1]:
                        property_value = element[1].as_int('value')
                    else:
                        property_value = element[1].as_int('default')
                    property_control = wxpg.IntProperty(element[0], value=property_value)
                    if 'maximum' in element[1]:
                        property_control.SetAttribute('Max', element[1].as_int('maximum'))
                    if 'minimum' in element[1]:
                        property_control.SetAttribute('Min', element[1].as_int('minimum'))
                    property_control.SetAttribute('Wrap', True)
                    pg.Append(property_control)
                    pg.SetPropertyEditor(element[0], 'SpinCtrl')

                if element[1]['type'] == 'string':
                    if 'value' in element[1]:
                        property_value = element[1]['value']
                    else:
                        property_value = element[1]['default']
                    pg.Append(wxpg.StringProperty(element[0], value=property_value))

        pg.Refresh()

    def OnReserved(self, event):
        pass
