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

class ClickedPoint(object):
    '''
    this class defines what a clicked point on the curve plot is
    '''
    def __init__(self):

        self.is_marker=None #boolean ; decides if it is a marker
        self.is_line_edge=None #boolean ; decides if it is the edge of a line (unused)
        self.absolute_coords=(None,None) #(float,float) ; the absolute coordinates of the clicked point on the graph
        self.graph_coords=(None,None) #(float,float) ; the coordinates of the plot that are nearest in X to the clicked point
        self.index=None #integer ; the index of the clicked point with respect to the vector selected
        self.dest=None #0 or 1 ; 0=top plot 1=bottom plot


    def find_graph_coords_old(self, xvector, yvector):
        '''
        Given a clicked point on the plot, finds the nearest point in the dataset (in X) that
        corresponds to the clicked point.
        OLD & DEPRECATED - to be removed
        '''

        #FIXME: a general algorithm using min() is needed!
        best_index=0
        best_dist=10**9 #should be more than enough given the scale

        for index in scipy.arange(1,len(xvector),1):
            dist=((self.absolute_coords[0]-xvector[index])**2)+(100*((self.absolute_coords[1]-yvector[index])))**2
                #TODO, generalize? y coordinate is multiplied by 100 due to scale differences in the plot
            if dist<best_dist:
                best_index=index
                best_dist=dist

        self.index=best_index
        self.graph_coords=(xvector[best_index],yvector[best_index])
        return

    def find_graph_coords(self,xvector,yvector):
        '''
        Given a clicked point on the plot, finds the nearest point in the dataset (in X) that
        corresponds to the clicked point.
        '''
        dists=[]
        for index in scipy.arange(1,len(xvector),1):
            dists.append(((self.absolute_coords[0]-xvector[index])**2)+((self.absolute_coords[1]-yvector[index])**2))

        self.index=dists.index(min(dists))
        self.graph_coords=(xvector[self.index],yvector[self.index])
