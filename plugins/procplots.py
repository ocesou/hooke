#!/usr/bin/env python

'''
procplots.py

Process plots plugin for force curves.

Copyright ???? by ?
with modifications by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

import lib.libhooke as lh
import wxversion
wxversion.select(lh.WX_GOOD)

import copy
from numpy import arange, diff, fft
from scipy.signal import medfilt

from lib.peakspot import conv_dx

class procplotsCommands:

    def _plug_init(self):
        pass

    def do_convplot(self):
        '''
        CONVPLOT
        (procplots.py)
        Plots the convolution data of the currently displayed force curve retraction.
        ------------
        Syntax:
        convplot
        '''

        #need to convert the string that contains the list into a list
        column = self.GetIntFromConfig('procplots', 'convplot', 'column')
        convolution = eval(self.GetStringFromConfig('procplots', 'convplot', 'convolution'))
        row = self.GetIntFromConfig('procplots', 'convplot', 'row')
        whatset_str = self.GetStringFromConfig('procplots', 'convplot', 'whatset')
        whatset = []
        if whatset_str == 'extension':
            whatset = [lh.EXTENSION]
        if whatset_str == 'retraction':
            whatset = [lh.RETRACTION]
        if whatset_str == 'both':
            whatset = [lh.EXTENSION, lh.RETRACTION]

        #TODO: add option to keep previous derivplot
        plot = self.GetDisplayedPlotCorrected()

        for index in whatset:
            conv_curve = copy.deepcopy(plot.curves[index])
            #Calculate convolution
            conv_curve.y = conv_dx(plot.curves[index].y, convolution)

            conv_curve.destination.column = column
            conv_curve.destination.row = row
            conv_curve.title = 'Convolution'
            plot.curves.append(conv_curve)

        #warn if no flattening has been done.
        if not self.AppliesPlotmanipulator('flatten'):
            self.AppendToOutput('Flatten manipulator was not applied. Processing was done without flattening.')
            self.AppendToOutput('Enable the flatten plotmanipulator for better results.')

        self.UpdatePlot(plot)


    def do_derivplot(self):
        '''
        DERIVPLOT
        (procplots.py plugin)
        Plots the discrete differentiation of the currently displayed force curve retraction
        ---------
        Syntax: derivplot
        '''
        column = self.GetIntFromConfig('procplots', 'derivplot', 'column')
        row = self.GetIntFromConfig('procplots', 'derivplot', 'row')
        select = self.GetBoolFromConfig('procplots', 'derivplot', 'select')
        whatset_str = self.GetStringFromConfig('procplots', 'derivplot', 'whatset')
        whatset = []
        if whatset_str == 'extension':
            whatset = [lh.EXTENSION]
        if whatset_str == 'retraction':
            whatset = [lh.RETRACTION]
        if whatset_str == 'both':
            whatset = [lh.EXTENSION, lh.RETRACTION]

        #TODO: add option to keep previous derivplot
        plot = self.GetDisplayedPlotCorrected()

        for index in whatset:
            deriv_curve = copy.deepcopy(plot.curves[index])
            deriv_curve.x = deriv_curve.x[:-1]
            deriv_curve.y = diff(deriv_curve.y).tolist()

            deriv_curve.destination.column = column
            deriv_curve.destination.row = row
            deriv_curve.title = 'Discrete differentiation'
            deriv_curve.units.y += ' ' + deriv_curve.units.x + '-1'
            plot.curves.append(deriv_curve)

        self.UpdatePlot(plot)

    def do_subtplot(self):
        '''
        SUBTPLOT
        (procplots.py plugin)
        Plots the difference between retraction and extension of the currently displayed curve
        -------
        Syntax: subtplot
        '''
        #TODO: what is sub_filter supposed to do?

        #TODO: add option to keep previous subtplot
        plot = self.GetDisplayedPlotCorrected()

        extension = plot.curves[lh.EXTENSION]
        retraction = plot.curves[lh.RETRACTION]

        extension, retraction = self.subtract_curves(extension, retraction)

        self.UpdatePlot(plot)

    def subtract_curves(self, minuend, subtrahend):
        '''
        calculates: difference = minuend - subtrahend
        (usually:              extension - retraction
        '''

        #we want the same number of points for minuend and subtrahend
        #TODO: is this not already done when normalizing in the driver?
        maxpoints_tot = min(len(minuend.x), len(subtrahend.x))
        minuend.x = minuend.x[0:maxpoints_tot]
        minuend.y = minuend.y[0:maxpoints_tot]
        subtrahend.x = subtrahend.x[0:maxpoints_tot]
        subtrahend.y = subtrahend.y[0:maxpoints_tot]

        subtrahend.y = [y_subtrahend - y_minuend for y_subtrahend, y_minuend in zip(subtrahend.y, minuend.y)]
        minuend.y = [0] * len(minuend.x)

        return minuend, subtrahend

#-----PLOT MANIPULATORS
    def plotmanip_median(self, plot, current, customvalue=False):
        '''
        does the median of the y values of a plot
        '''
        median_filter = self.GetIntFromConfig('procplots', 'median')
        if median_filter == 0:
            return plot

        if float(median_filter) / 2 == int(median_filter) / 2:
            median_filter += 1

        for curve in plot.curves:
            curve.y = medfilt(curve.y, median_filter).tolist()

        return plot

    def plotmanip_correct(self, plot, current, customvalue=False):
        '''
        does the correction for the deflection for a force spectroscopy curve.
        Assumes that:
        - the current plot has a deflection() method that returns a vector of values
        - the deflection() vector is as long as the X of extension + the X of retraction
        - plot.vectors[0][0] is the X of extension curve
        - plot.vectors[1][0] is the X of retraction curve

        FIXME: both this method and the picoforce driver have to be updated, deflection() must return
        a more sensible data structure!
        '''
        #use only for force spectroscopy experiments!
        if current.driver.experiment != 'smfs':
            return plot

        if not customvalue:
            customvalue = self.GetBoolFromConfig('procplots', 'correct')
        if not customvalue:
            return plot

        defl_ext, defl_ret = current.driver.deflection()

        plot.curves[lh.EXTENSION].x = [(zpoint - deflpoint) for zpoint,deflpoint in zip(plot.curves[lh.EXTENSION].x, defl_ext)]
        plot.curves[lh.RETRACTION].x = [(zpoint - deflpoint) for zpoint,deflpoint in zip(plot.curves[lh.RETRACTION].x, defl_ret)]

        return plot

#FFT---------------------------
    def fft_plot(self, curve, boundaries=[0, -1]):
        '''
        calculates the fast Fourier transform for the selected vector in the plot
        '''

        fftlen = len(curve.y[boundaries[0]:boundaries[1]]) / 2 #need just 1/2 of length
        curve.x = arange(1, fftlen).tolist()

        try:
            curve.y = abs(fft(curve.y[boundaries[0]:boundaries[1]])[1:fftlen]).tolist()
        except TypeError: #we take care of newer NumPy (1.0.x)
            curve.y = abs(fft.fft(curve.y[boundaries[0]:boundaries[1]])[1:fftlen]).tolist()

        return curve

    def do_fft(self):
        '''
        FFT
        (procplots.py plugin)
        Plots the fast Fourier transform of the selected plot
        ---
        Syntax: fft [top,bottom] [select] [0,1...]

        By default, fft performs the Fourier transform on all the 0-th data set on the
        top plot.

        [top, bottom]: which plot is the data set to fft (default: top)
        [select]: you pick up two points on the plot and fft only the segment between
        [0,1,...]: which data set on the selected plot you want to fft (default: 0)
        '''

        column = self.GetIntFromConfig('procplots', 'fft', 'column')
        row = self.GetIntFromConfig('procplots', 'fft', 'row')
        select = self.GetBoolFromConfig('procplots', 'fft', 'select')
        whatset_str = self.GetStringFromConfig('procplots', 'fft', 'whatset')
        whatset = []
        if whatset_str == 'extension':
            whatset = [lh.EXTENSION]
        if whatset_str == 'retraction':
            whatset = [lh.RETRACTION]
        if whatset_str == 'both':
            whatset = [lh.EXTENSION, lh.RETRACTION]

        if select:
            points = self._measure_N_points(N=2, message='Please select a region by clicking on the start and the end point.', whatset=1)
            boundaries = [points[0].index, points[1].index]
            boundaries.sort()
        else:
            boundaries = [0, -1]

        #TODO: add option to keep previous FFT
        plot = self.GetDisplayedPlotCorrected()

        for index in whatset:
            fft_curve = self.fft_plot(copy.deepcopy(plot.curves[index]), boundaries)

            fft_curve.destination.column = column
            fft_curve.destination.row = row
            fft_curve.title = 'FFT'
            fft_curve.units.x = 'frequency'
            fft_curve.units.y = 'power'
            plot.curves.append(fft_curve)

        self.UpdatePlot(plot)
