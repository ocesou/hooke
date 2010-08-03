# Copyright (C) 2008-2010 Alberto Gomez-Casado
#                         Fabrizio Benedetti
#                         Massimo Sandal <devicerandom@gmail.com>
#                         W. Trevor King <wking@drexel.edu>
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

from numpy import arange

import wx


class ClickedPoint(object):
    """Defines a clicked point from a curve plot.
    """
    def __init__(self):

        self.is_marker=None #boolean ; decides if it is a marker
        self.is_line_edge=None #boolean ; decides if it is the edge of a line (unused)
        self.absolute_coords=(None,None) #(float,float) ; the absolute coordinates of the clicked point on the graph
        self.graph_coords=(None,None) #(float,float) ; the coordinates of the plot that are nearest in X to the clicked point
        self.index=None #integer ; the index of the clicked point with respect to the vector selected
        self.dest=None #0 or 1 ; 0=top plot 1=bottom plot

    def find_graph_coords(self,xvector,yvector):
        """Find the point in the dataset that is closest to `self`.

        Given a clicked point on the plot, finds the nearest point in
        the dataset (in X) that corresponds to the clicked point.
        """
        dists=[]
        for index in arange(1,len(xvector),1):
            dists.append(((self.absolute_coords[0]-xvector[index])**2)+((self.absolute_coords[1]-yvector[index])**2))

        self.index=dists.index(min(dists))
        self.graph_coords=(xvector[self.index],yvector[self.index])


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
