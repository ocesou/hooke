#!/usr/bin/env python

'''
plot.py

Plot panel for Hooke.

Copyright 2009 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas

from matplotlib.backends.backend_wx import NavigationToolbar2Wx

from matplotlib.figure import Figure

import wx

#there are many comments in here from the demo app
#they should come in handy to expand the functionality in the future

class HookeCustomToolbar(NavigationToolbar2Wx):

    def __init__(self, plotCanvas):
        NavigationToolbar2Wx.__init__(self, plotCanvas)
        # add new toolbar buttons
        #glyph_file = 'resources' + os.sep + 'pipette.png'
        #glyph = wx.Image(glyph_file, wx.BITMAP_TYPE_ANY).ConvertToBitmap()

        #self.AddCheckTool(ON_CUSTOM_PICK, glyph, shortHelp='Select a data point', longHelp='Select a data point')
        #wx.EVT_TOOL(self, ON_CUSTOM_PICK, self.OnSelectPoint)

        # remove the unwanted button
#        POSITION_OF_CONFIGURE_SUBPLOTS_BTN = 6
#        self.DeleteToolByPos(POSITION_OF_CONFIGURE_SUBPLOTS_BTN)

    #def OnSelectPoint(self, event):
        #self.Parent.Parent.Parent.pick_active = True


#class LineBuilder:
    #def __init__(self, line):
        #self.line = line
        #self.xs = list(line.get_xdata())
        #self.ys = list(line.get_ydata())
        #self.cid = line.figure.canvas.mpl_connect('button_press_event', self)

    #def __call__(self, event):
        #print 'click', event
        #if event.inaxes != self.line.axes:
            #return
        #self.xs.append(event.xdata)
        #self.ys.append(event.ydata)
        #self.line.set_data(self.xs, self.ys)
        #self.line.figure.canvas.draw()


class PlotPanel(wx.Panel):

    def __init__(self, parent, ID):
        wx.Panel.__init__(self, parent, ID, style=wx.WANTS_CHARS|wx.NO_BORDER, size=(160, 200))

        self.figure = Figure()
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.SetColor(wx.NamedColor('WHITE'))

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.sizer)
        self.Fit()

        self.display_coordinates = False

        self.figure.canvas.mpl_connect('button_press_event', self.OnClick)
        self.figure.canvas.mpl_connect('axes_enter_event', self.OnEnterAxes)
        self.figure.canvas.mpl_connect('axes_leave_event', self.OnLeaveAxes)
        self.figure.canvas.mpl_connect('motion_notify_event', self.OnMouseMove)
        self.add_toolbar()  # comment this out for no toolbar

    def add_toolbar(self):
        self.toolbar = HookeCustomToolbar(self.canvas)
        self.toolbar.Realize()
        if wx.Platform == '__WXMAC__':
            # Mac platform (OSX 10.3, MacPython) does not seem to cope with
            # having a toolbar in a sizer. This work-around gets the buttons
            # back, but at the expense of having the toolbar at the top
            self.SetToolBar(self.toolbar)
        else:
            # On Windows platform, default window size is incorrect, so set
            # toolbar width to figure width.
            tw, th = self.toolbar.GetSizeTuple()
            fw, fh = self.canvas.GetSizeTuple()
            # By adding toolbar in sizer, we are able to put it at the bottom
            # of the frame - so appearance is closer to GTK version.
            # As noted above, doesn't work for Mac.
            self.toolbar.SetSize(wx.Size(fw, th))
            self.sizer.Add(self.toolbar, 0, wx.LEFT | wx.EXPAND)
        # update the axes menu on the toolbar
        self.toolbar.update()

    def get_figure(self):
        return self.figure

    def SetColor(self, rgbtuple):
        '''
        Set figure and canvas colours to be the same
        '''
        if not rgbtuple:
            rgbtuple = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE).Get()
        col = [c / 255.0 for c in rgbtuple]
        self.figure.set_facecolor(col)
        self.figure.set_edgecolor(col)
        self.canvas.SetBackgroundColour(wx.Colour(*rgbtuple))

    def SetStatusText(self, text, field=1):
        self.Parent.Parent.statusbar.SetStatusText(text, field)

    def OnClick(self, event):
        #self.SetStatusText(str(event.xdata))
        #print 'button=%d, x=%d, y=%d, xdata=%f, ydata=%f'%(event.button, event.x, event.y, event.xdata, event.ydata)
        pass

    def OnEnterAxes(self, event):
        self.display_coordinates = True

    def OnLeaveAxes(self, event):
        self.display_coordinates = False
        self.SetStatusText('')

    def OnMouseMove(self, event):
        if event.guiEvent.m_shiftDown:
            self.toolbar.set_cursor(2)
            #print 'hand: ' + str(wx.CURSOR_HAND)
            #print 'cross: ' + str(wx.CURSOR_CROSS)
            #print 'ibeam: ' + str(wx.CURSOR_IBEAM)
            #print 'wait: ' + str(wx.CURSOR_WAIT)
            #print 'hourglass: ' + str(wx.HOURGLASS_CURSOR)
        else:
            self.toolbar.set_cursor(1)

            #axes = self.figure.axes[0]
            #line, = axes.plot([event.x - 20 , event.x + 20], [event.y - 20, event.y + 20])

            #line.figure.canvas.draw()
        if self.display_coordinates:
            coordinateString = ''.join([str(event.xdata), ' ', str(event.ydata)])
            #TODO: pretty format
            self.SetStatusText(coordinateString)

    def OnPaint(self, event):
        self.canvas.draw()
