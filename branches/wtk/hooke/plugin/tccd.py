# Copyright (C) 2009-2010 Massimo Sandal <devicerandom@gmail.com>
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

"""General utilities for TCCD stuff
"""

class generaltccdCommands(object):

    def plotmanip_threshold(self, plot, current, customvalue=False):
        '''
        Cuts from the plot everything below the threshold.
        Set the threshold with "set tccd_threshold"
        '''

        if current.curve.experiment != 'smfluo':
            return plot

        if not self.config['tccd_threshold'] and (not customvalue):
            return plot

        if customvalue:
            thresh=customvalue
        else:
            thresh=self.config['tccd_threshold']

        for set in plot.vectors:
            newy=[]
            for value in set[1]:
                if abs(value) < thresh:
                    newy.append(0)
                else:
                    newy.append(value)

            set[1]=newy

        return plot


    def plotmanip_coincident(self,plot,current, customvalue=False):
        '''
        Shows only coincident events
        '''
        if current.curve.experiment != 'smfluo':
            return plot

        if not self.config['tccd_coincident'] and (not customvalue):
            return plot

        newred=[]
        newblue=[]
        for index in range(len(plot.vectors[0][1])):
            if abs(plot.vectors[0][1][index])>self.config['tccd_threshold'] and abs(plot.vectors[1][1][index])>self.config['tccd_threshold']:
                newred.append(plot.vectors[0][1][index])
                newblue.append(plot.vectors[1][1][index])
            else:
                newred.append(0)
                newblue.append(0)

        plot.vectors[0][1]=newred
        plot.vectors[1][1]=newblue

        return plot
