# Copyright (C) 2009-2010 Rolf Schmidt <rschmidt@alcor.concordia.ca>
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

"""This plugin contains a plotmanipulator to show the convoluted curve.
"""

import libpeakspot

class showconvolutedCommands:

    #def _plug_init(self):
        #pass

    def plotmanip_showconvoluted(self, plot, curve):
        '''
        BEGIN: taken from procplots.py
        might need some tweaking
        '''
        #use only for force spectroscopy experiments!
        if curve.driver.experiment != 'smfs':
            return plot

        '''
        END: taken from procplots.py
        '''

        #need to convert the string that contains the list into a list
        #convolution = eval(self.config['convfilt']['convolution']['value'])
        convolution = eval(self.GetStringFromConfig('flatfilts', 'convfilt', 'convolution'))

        xRet = plot.vectors[1][0]
        yRet = plot.vectors[1][1]
        convoluted = libpeakspot.conv_dx(yRet, convolution)
        #convoluted=libpeakspot.conv_dx(yRet, [-20, -10, -6, 0, 12, 12, 12])
        plot.add_set(xRet, convoluted)
        #plot.vectors[1][1]=[i for i in convoluted]
        #set contact point plot style to 'plot'
        #and the color to red
        plot.styles.append('plot')
        plot.colors.append('black')
        #peak_location, peak_size = self.has_peaks(plot, blindwindow, convolution, minpeaks)
        peak_locations, peak_sizes = self.has_peaks(plot, curve)

        if peak_locations:
            peak_locations_x = []
            peak_locations_y = []
            for location in peak_locations:
                peak_locations_x.append(xRet[location])
                peak_locations_y.append(yRet[location])
            plot.add_set(peak_locations_x, peak_locations_y)
            plot.styles.append('scatter')
            plot.colors.append('green')
            plot.add_set(peak_locations_x, peak_sizes)
            plot.styles.append('scatter')
            plot.colors.append('magenta')

        #Return the plot object.
        return plot
