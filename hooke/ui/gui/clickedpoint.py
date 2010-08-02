#!/usr/bin/env python

'''
clickedpoint.py

ClickedPoint class for Hooke.

Copyright 2010 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

from scipy import arange

class ClickedPoint(object):
    '''
    This class defines what a clicked point on the curve plot is.
    '''
    def __init__(self):

        self.is_marker = None #boolean ; decides if it is a marker
        self.is_line_edge = None #boolean ; decides if it is the edge of a line (unused)
        self.absolute_coords = (None, None) #(float,float) ; the absolute coordinates of the clicked point on the graph
        self.graph_coords = (None, None) #(float,float) ; the coordinates of the plot that are nearest in X to the clicked point
        self.index = None #integer ; the index of the clicked point with respect to the vector selected
        self.dest = None #0 or 1 ; 0=top plot 1=bottom plot

    def find_graph_coords(self, xvector, yvector):
        '''
        Given a clicked point on the plot, finds the nearest point in the dataset (in X) that
        corresponds to the clicked point.
        '''
        dists = []
        for index in arange(1, len(xvector), 1):
            dists.append(((self.absolute_coords[0] - xvector[index]) ** 2)+((self.absolute_coords[1] - yvector[index]) ** 2))

        self.index=dists.index(min(dists))
        self.graph_coords=(xvector[self.index], yvector[self.index])
