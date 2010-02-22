#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
multidistance.py

Calculates the distances between peaks.

Copyright 2010 by Fabrizio Benedetti
with modifications by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

import lib.libhooke as lh
import wxversion
wxversion.select(lh.WX_GOOD)

import copy
from numpy import RankWarning
import os.path
import time

import warnings
warnings.simplefilter('ignore', RankWarning)

import lib.plugin
import lib.results

class multidistanceCommands:

    def do_multidistance(self):
        '''
        MULTIDISTANCE
        multidistance.py
        Based on the convolution recognition automatically gives the distances between the peaks found.
        The command allows also to remove the unwanted peaks that can be due to interference.
        When you first issue the command, it will ask for a filename. If you are giving a filename
        of an existing file, autopeak will resume it and append measurements to it. If you are giving
        a new filename, it will create the file and append to it until you close Hooke.
        You can also define a minimun deviation of the peaks.

        Syntax:
        multidistance [deviation]
        deviation = number of times the convolution signal is above the noise absolute deviation.
        '''

        color = self.GetColorFromConfig('multidistance', 'color')
        size = self.GetIntFromConfig('multidistance', 'size')
        use_convfilt = self.GetBoolFromConfig('multidistance', 'use_convfilt')

        plot = self.GetDisplayedPlotCorrected()
        if use_convfilt:
            peak_location, peak_size = self.has_peaks(plot)
        else:
            plugin = lib.plugin.Plugin()
            plugin.name = 'multidistance'
            plugin.section = 'multidistance'
            peak_location, peak_size = self.has_peaks(plot, plugin)

        #if no peaks, we have nothing to plot. exit.
        if len(peak_location) == 0:
            self.AppendToOutput('No peaks found.')
            return

        retraction = plot.curves[lh.RETRACTION]
        results = lib.results.ResultsMultiDistance()

        for peak in peak_location:
            result = lib.results.Result()
            result.result['Distance'] = retraction.x[peak]
            result.color = color
            result.size = size
            result.x = retraction.x[peak]
            result.y = retraction.y[peak]
            results.results.append(result)

        results.update()

        self.results_str = 'multidistance'

        results.set_multipliers(-1)
        plot = self.GetActivePlot()
        plot.results['multidistance'] = results
        self.UpdatePlot()
