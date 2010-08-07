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
from numpy import arange, diff, fft, median
from scipy.signal import medfilt

from lib.peakspot import conv_dx
import lib.prettyformat

class procplotsCommands:

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
