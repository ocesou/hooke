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

import wx


def measure_N_points(hooke_frame, N, message='', block=0):
    '''
    General helper function for N-points measurements
    By default, measurements are done on the retraction
    '''
    if message:
        dialog = wx.MessageDialog(None, message, 'Info', wx.OK)
        dialog.ShowModal()

    figure = self.GetActiveFigure()

    xvector = self.displayed_plot.curves[block].x
    yvector = self.displayed_plot.curves[block].y

    clicked_points = figure.ginput(N, timeout=-1, show_clicks=True)

    points = []
    for clicked_point in clicked_points:
        point = lib.clickedpoint.ClickedPoint()
        point.absolute_coords = clicked_point[0], clicked_point[1]
        point.dest = 0
        #TODO: make this optional?
        #so far, the clicked point is taken, not the corresponding data point
        point.find_graph_coords(xvector, yvector)
        point.is_line_edge = True
        point.is_marker = True
        points.append(point)
    return points
