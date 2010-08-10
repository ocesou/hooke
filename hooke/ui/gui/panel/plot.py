# Copyright (C) 2010 Massimo Sandal <devicerandom@gmail.com>
#                    Rolf Schmidt <rschmidt@alcor.concordia.ca>
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

"""Plot panel for Hooke.

Notes
-----
Originally based on `this example`_.

.. _this example:
  http://matplotlib.sourceforge.net/examples/user_interfaces/embedding_in_wx2.html
"""

import logging

import matplotlib
matplotlib.use('WXAgg')  # use wxpython with antigrain (agg) rendering
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx as NavToolbar
from matplotlib.figure import Figure
from matplotlib.ticker import Formatter, ScalarFormatter
import numpy
import wx

from ....util.callback import callback, in_callback
from ....util.si import ppSI, split_data_label
from ..dialog.selection import Selection
from . import Panel


class HookeFormatter (Formatter):
    """:class:`matplotlib.ticker.Formatter` using SI prefixes.
    """
    def __init__(self, unit='', decimals=2):
        self.decimals = decimals
        self.unit = unit

    def __call__(self, x, pos=None):
        """Return the format for tick val `x` at position `pos`.
        """
        if x == 0:
            return '0'
        return ppSI(value=x, unit=self.unit, decimals=self.decimals)


class HookeScalarFormatter (ScalarFormatter):
    """:class:`matplotlib.ticker.ScalarFormatter` using only multiples
    of three in the mantissa.

    A fixed number of decimals can be displayed with the optional
    parameter `decimals` . If `decimals` is `None` (default), the number
    of decimals is defined from the current ticks.
    """
    def __init__(self, decimals=None, **kwargs):
        # Can't use super() because ScalarFormatter is an old-style class :(.
        ScalarFormatter.__init__(self, **kwargs)
        self._decimals = decimals

    def _set_orderOfMagnitude(self, *args, **kwargs):
        """Sets the order of magnitude."""        
        # Can't use super() because ScalarFormatter is an old-style class :(.
        ScalarFormatter._set_orderOfMagnitude(self, *args, **kwargs)
        self.orderOfMagnitude -= self.orderOfMagnitude % 3

    def _set_format(self, *args, **kwargs):
        """Sets the format string to format all ticklabels."""
        # Can't use super() because ScalarFormatter is an old-style class :(.
        ScalarFormatter._set_format(self, *args, **kwargs)
        if self._decimals is None or self._decimals < 0:
            locs = (np.asarray(self.locs)-self.offset) / 10**self.orderOfMagnitude+1e-15
            sigfigs = [len(str('%1.8f'% loc).split('.')[1].rstrip('0')) \
                   for loc in locs]
            sigfigs.sort()
            decimals = sigfigs[-1]
        else:
            decimals = self._decimals
        self.format = '%1.' + str(decimals) + 'f'
        if self._usetex:
            self.format = '$%s$' % self.format
        elif self._useMathText:
            self.format = '$\mathdefault{%s}$' % self.format


class PlotPanel (Panel, wx.Panel):
    """UI for graphical curve display.
    """
    def __init__(self, callbacks=None, **kwargs):
        self.display_coordinates = False
        self.style = 'line'
        self._curve = None
        self._config = {}
        self._x_column = None
        self._y_columns = []  # TODO: select right/left scales?
        self._x_unit = ''
        self._y_unit = ''
        super(PlotPanel, self).__init__(
            name='plot', callbacks=callbacks, **kwargs)
        self._c = {}
        self._c['figure'] = Figure()
        self._c['canvas'] = FigureCanvas(
            parent=self, id=wx.ID_ANY, figure=self._c['figure'])

        self._set_color(wx.NamedColor('WHITE'))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self._c['canvas'], 1, wx.LEFT | wx.TOP | wx.GROW)
        self._setup_toolbar(sizer=sizer)  # comment out to remove plot toolbar.
        self.SetSizer(sizer)
        self.Fit()

        self.Bind(wx.EVT_SIZE, self._on_size) 
        self._c['figure'].canvas.mpl_connect(
            'button_press_event', self._on_click)
        self._c['figure'].canvas.mpl_connect(
            'axes_enter_event', self._on_enter_axes)
        self._c['figure'].canvas.mpl_connect(
            'axes_leave_event', self._on_leave_axes)
        self._c['figure'].canvas.mpl_connect(
            'motion_notify_event', self._on_mouse_move)

    def _setup_toolbar(self, sizer):
        self._c['toolbar'] = NavToolbar(self._c['canvas'])
        self._c['x column'] = wx.Choice(
            parent=self._c['toolbar'], choices=[])
        self._c['x column'].SetToolTip(wx.ToolTip('x column'))
        self._c['toolbar'].AddControl(self._c['x column'])
        self._c['x column'].Bind(wx.EVT_CHOICE, self._on_x_column)
        self._c['y column'] = wx.Button(
            parent=self._c['toolbar'], label='y column(s)')
        self._c['y column'].SetToolTip(wx.ToolTip('y column'))
        self._c['toolbar'].AddControl(self._c['y column'])
        self._c['y column'].Bind(wx.EVT_BUTTON, self._on_y_column)

        self._c['toolbar'].Realize()  # call after putting items in the toolbar
        if wx.Platform == '__WXMAC__':
            # Mac platform (OSX 10.3, MacPython) does not seem to cope with
            # having a toolbar in a sizer. This work-around gets the buttons
            # back, but at the expense of having the toolbar at the top
            self.SetToolBar(self._c['toolbar'])
        elif wx.Platform == '__WXMSW__':
            # On Windows platform, default window size is incorrect, so set
            # toolbar width to figure width.
            tw, th = toolbar.GetSizeTuple()
            fw, fh = self._c['canvas'].GetSizeTuple()
            # By adding toolbar in sizer, we are able to put it at the bottom
            # of the frame - so appearance is closer to GTK version.
            # As noted above, doesn't work for Mac.
            self._c['toolbar'].SetSize(wx.Size(fw, th))
            sizer.Add(self._c['toolbar'], 0 , wx.LEFT | wx.EXPAND)
        else:
            sizer.Add(self._c['toolbar'], 0 , wx.LEFT | wx.EXPAND)
        self._c['toolbar'].update()  # update the axes menu on the toolbar

    def _set_color(self, rgbtuple=None):
        """Set both figure and canvas colors to `rgbtuple`.
        """
        if rgbtuple == None:
            rgbtuple = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE).Get()
        col = [c/255.0 for c in rgbtuple]
        self._c['figure'].set_facecolor(col)
        self._c['figure'].set_edgecolor(col)
        self._c['canvas'].SetBackgroundColour(wx.Colour(*rgbtuple))

    def _set_status_text(self, text):
        in_callback(self, text)

    def _on_size(self, event):
        event.Skip()
        wx.CallAfter(self._resize_canvas)

    def _on_click(self, event):
        if self._curve == None:
            return
        d = self._config.get('plot decimals', 2)
        x,y = (event.xdata, event.ydata)
        if None in [x, y]:
            return
        xt = ppSI(value=x, unit=self._x_unit, decimals=d)
        yt = ppSI(value=y, unit=self._y_unit, decimals=d)
        point_indexes = []
        for data in self._curve.data:
            try:
                x_col = data.info['columns'].index(self._x_column)
            except ValueError:
                continue  # data is missing a required column
            index = numpy.absolute(data[:,x_col]-x).argmin()
            point_indexes.append((data.info['name'], index))
        self._set_status_text(
            '(%s, %s) %s'
            % (xt, yt,
               ', '.join(['%s: %d' % (n,i) for n,i in point_indexes])))

    def _on_enter_axes(self, event):
        self.display_coordinates = True

    def _on_leave_axes(self, event):
        self.display_coordinates = False
        #self.SetStatusText('')

    def _on_mouse_move(self, event):
        if 'toolbar' in self._c:
            if event.guiEvent.m_shiftDown:
                self._c['toolbar'].set_cursor(wx.CURSOR_RIGHT_ARROW)
            else:
                self._c['toolbar'].set_cursor(wx.CURSOR_ARROW)
        if self.display_coordinates:
            coordinateString = ''.join(
                ['x: ', str(event.xdata), ' y: ', str(event.ydata)])
            #TODO: pretty format
            #self.SetStatusText(coordinateString)

    def _on_x_column(self, event):
        self._x_column = self._c['x column'].GetStringSelection()
        self.update()

    def _on_y_column(self, event):
        if not hasattr(self, '_columns') or len(self._columns) == 0:
            self._y_columns = []
            return
        s = Selection(
            options=self._columns,
            message='Select visible y column(s).',
            button_id=wx.ID_OK,
            selection_style='multiple',
            parent=self,
            title='Select y column(s)',
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        s.CenterOnScreen()
        s.ShowModal()
        if s.canceled == True:
            return
        self._y_columns = [self._columns[i] for i in s.selected]
        s.Destroy()
        if len(self._y_columns) == 0:
            self._y_columns = self._columns[-1:]
        self.update()

    def _resize_canvas(self):
        w,h = self.GetClientSize()
        if 'toolbar' in self._c:
            tw,th = self._c['toolbar'].GetSizeTuple()
        else:
            th = 0
        dpi = float(self._c['figure'].get_dpi())
        self._c['figure'].set_figwidth(w/dpi)
        self._c['figure'].set_figheight((h-th)/dpi)
        self._c['canvas'].draw()
        self.Refresh()

    def OnPaint(self, event):
        print 'painting'
        super(PlotPanel, self).OnPaint(event)
        self._c['canvas'].draw()

    def set_curve(self, curve, config=None):
        self._curve = curve
        columns = set()
        for data in curve.data:
            columns = columns.union(set(data.info['columns']))
        self._columns = sorted(columns)
        if self._x_column not in self._columns:
            self._x_column = self._columns[0]
        self._y_columns = [y for y in self._y_columns if y in self._columns]
        if len(self._y_columns) == 0:
            self._y_columns = self._columns[-1:]
        if 'x column' in self._c:
            for i in range(self._c['x column'].GetCount()):
                self._c['x column'].Delete(0)
            self._c['x column'].AppendItems(self._columns)
            self._c['x column'].SetStringSelection(self._x_column)
        self.update(config=config)

    def update(self, config=None):
        if config == None:
            config = self._config  # use the last cached value
        else:
            self._config = config  # cache for later refreshes
        self._c['figure'].clear()
        self._c['figure'].suptitle(
            self._hooke_frame._file_name(self._curve.name),
            fontsize=12)
        axes = self._c['figure'].add_subplot(1, 1, 1)

        if config['plot SI format'] == True:
            d = config['plot decimals']
            x_n, self._x_unit = split_data_label(self._x_column)
            y_n, self._y_unit = split_data_label(self._y_columns[0])
            for y_column in self._y_columns[1:]:
                y_n, y_unit = split_data_label(y_column)
                if y_unit != self._y_unit:
                    log = logging.getLogger('hooke')
                    log.warn('y-axes unit mismatch: %s != %s, using %s.'
                             % (self._y_unit, y_unit, self._y_unit))
            fx = HookeFormatter(decimals=d, unit=self._x_unit)
            axes.xaxis.set_major_formatter(fx)
            fy = HookeFormatter(decimals=d, unit=self._y_unit)
            axes.yaxis.set_major_formatter(fy)
            axes.set_xlabel(x_n)
            if len(self._y_columns) == 1:
                axes.set_ylabel(y_n)
        else:
            self._x_unit = ''
            self._y_unit = ''
            axes.set_xlabel(self._x_column)
            if len(self._y_columns) == 1:
                axes.set_ylabel(self._y_columns[0])

        self._c['figure'].hold(True)
        for i,data in enumerate(self._curve.data):
            for y_column in self._y_columns:
                try:
                    x_col = data.info['columns'].index(self._x_column)
                    y_col = data.info['columns'].index(y_column)
                except ValueError:
                    continue  # data is missing a required column
                axes.plot(data[:,x_col], data[:,y_col],
                          '.',
                          label=('%s, %s' % (data.info['name'], y_column)))
        if config['plot legend'] == True:
            axes.legend(loc='best')
        self._c['canvas'].draw()
