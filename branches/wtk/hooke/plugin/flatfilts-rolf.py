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

"""Force spectroscopy curves filtering of flat curves

Other plugin dependencies:
procplots.py (plot processing plugin)
"""

import xml.dom.minidom

import wx
#import scipy
import numpy
from numpy import diff
import os.path

#import pickle

import libpeakspot as lps
#import curve as lhc
import hookecurve as lhc
import libhooke as lh
import wxversion
wxversion.select(lh.WX_GOOD)


class flatfiltsCommands:

    def do_flatfilt(self):
        '''
        FLATFILT
        (flatfilts.py)
        Filters out flat (featureless) curves of the current playlist,
        creating a playlist containing only the curves with potential
        features.
        ------------
        Syntax:
        flatfilt [min_npks min_deviation]

        min_npks = minmum number of points over the deviation
        (default=4)

        min_deviation = minimum signal/noise ratio
        (default=9)

        If called without arguments, it uses default values, that
        should work most of the times.
        '''
        #TODO: should this be optional?
        medianfilter = 7

        self.AppendToOutput('Processing playlist...')
        self.AppendToOutput('(Please wait)')
        features = []
        playlist = self.GetActivePlaylist()
        curves = playlist.curves
        curve_index = 0
        for curve in curves:
            curve_index += 1
            try:
                notflat = self.has_features(curve)
                feature_string = ''
                if notflat != 1:
                    if notflat > 0:
                        feature_string = str(notflat) + ' features'
                    else:
                        feature_string = 'no features'
                else:
                    feature_string = '1 feature'
                output_string = ''.join(['Curve ', curve.name, '(', str(curve_index), '/', str(len(curves)), '): ', feature_string])
            except:
                notflat = False
                output_string = ''.join(['Curve ', curve.name, '(', str(curve_index), '/', str(len(curves)), '): cannot be filtered. Probably unable to retrieve force data from corrupt file.'])
            self.AppendToOutput(output_string)
            if notflat:
                curve.features = notflat
                features.append(curve_index - 1)
        if not features:
            self.AppendToOutput('Found nothing interesting. Check the playlist, could be a bug or criteria could be too stringent.')
        else:
            if len(features) < playlist.count:
                self.AppendToOutput(''.join(['Found ', str(len(features)), ' potentially interesting curves.']))
                self.AppendToOutput('Regenerating playlist...')
                playlist_filtered = playlist.filter_curves(features)
                self.AddPlaylist(playlist_filtered, name='flatfilt')
            else:
                self.AppendToOutput('No curves filtered. Try different filtering criteria.')

    def has_features(self, curve):
        '''
        decides if a curve is flat enough to be rejected from analysis: it sees if there
        are at least min_npks points that are higher than min_deviation times the absolute value
        of noise.

        Algorithm original idea by Francesco Musiani, with my tweaks and corrections.
        '''
        medianfilter = 7
        mindeviation = self.GetIntFromConfig('flatfilts', 'flatfilt', 'min_deviation')
        minpeaks = self.GetIntFromConfig('flatfilts', 'flatfilt', 'min_npks')
        #medianfilter = self.GetIntFromConfig('flatfilt', 'median_filter')
        #mindeviation = self.GetIntFromConfig('convfilt', 'mindeviation')
        #minpeaks = self.GetIntFromConfig('convfilt', 'minpeaks')

        retvalue = 0

        #item.identify(self.drivers)
        #we assume the first is the plot with the force curve
        #do the median to better resolve features from noise
        flat_plot = self.plotmanip_median(curve.driver.default_plots()[0], curve, customvalue=medianfilter)
        flat_vects = flat_plot.vectors
        curve.driver.close_all()
        #needed to avoid *big* memory leaks!
        #del item.driver
        #del item

        #absolute value of derivate
        yretdiff=diff(flat_vects[1][1])
        yretdiff=[abs(value) for value in yretdiff]
        #average of derivate values
        diffmean=numpy.mean(yretdiff)
        yretdiff.sort()
        yretdiff.reverse()
        c_pks=0
        for value in yretdiff:
            if value/diffmean > mindeviation:
                c_pks += 1
            else:
                break

        if c_pks >= minpeaks:
            retvalue = c_pks

        del flat_plot, flat_vects, yretdiff

        return retvalue

    ################################################################
    #-----CONVFILT-------------------------------------------------
    #-----Convolution-based peak recognition and filtering.
    #Requires the libpeakspot.py library

    def has_peaks(self, plot, curve=None):
        '''
        Finds peak position in a force curve.
        FIXME: should be moved to libpeakspot.py
        '''

        blindwindow = self.GetFloatFromConfig('flatfilts', 'convfilt', 'blindwindow')
        #need to convert the string that contains the list into a list
        convolution = eval(self.GetStringFromConfig('flatfilts', 'convfilt', 'convolution'))
        maxcut = self.GetFloatFromConfig('flatfilts', 'convfilt', 'maxcut')
        mindeviation = self.GetFloatFromConfig('flatfilts', 'convfilt', 'mindeviation')
        positive = self.GetBoolFromConfig('flatfilts', 'convfilt', 'positive')
        seedouble = self.GetIntFromConfig('flatfilts', 'convfilt', 'seedouble')
        stable = self.GetFloatFromConfig('flatfilts', 'convfilt', 'stable')

        xret = plot.vectors[1][0]
        yret = plot.vectors[1][1]
        #Calculate convolution
        convoluted = lps.conv_dx(yret, convolution)

        #surely cut everything before the contact point
        cut_index = self.find_contact_point(plot, curve)
        #cut even more, before the blind window
        start_x = xret[cut_index]
        blind_index = 0
        for value in xret[cut_index:]:
            if abs((value) - (start_x)) > blindwindow * (10 ** -9):
                break
            blind_index += 1
        cut_index += blind_index
        #do the dirty convolution-peak finding stuff
        noise_level = lps.noise_absdev(convoluted[cut_index:], positive, maxcut, stable)
        above = lps.abovenoise(convoluted, noise_level, cut_index, mindeviation)
        peak_location, peak_size = lps.find_peaks(above, seedouble=seedouble)
        #take the maximum
        for i in range(len(peak_location)):
            peak = peak_location[i]
            maxpk = min(yret[peak - 10:peak + 10])
            index_maxpk = yret[peak - 10:peak + 10].index(maxpk) + (peak - 10)
            peak_location[i] = index_maxpk

        return peak_location, peak_size

    def exec_has_peaks(self, curve):
        '''
        encapsulates has_peaks for the purpose of correctly treating the curve objects in the convfilt loop,
        to avoid memory leaks
        '''
        #item.identify(self.drivers)
        #we assume the first is the plot with the force curve
        plot = curve.driver.default_plots()[0]

        if self.HasPlotmanipulator('plotmanip_flatten'):
            #If flatten is present, use it for better recognition of peaks...
            #flatten = self._find_plotmanip('flatten') #extract flatten plot manipulator
            #plot = flatten(plot, item, customvalue=1)
            plot = self.plotmanip_flatten(plot, curve, customvalue=1)

        peak_location, peak_size = self.has_peaks(plot, curve)
        #close all open files
        curve.driver.close_all()
        #needed to avoid *big* memory leaks!
        #del item.driver
        #del item
        return peak_location, peak_size

    #------------------------
    #------commands----------
    #------------------------
    def do_peaks(self):
        '''
        PEAKS
        (flatfilts.py)
        Test command for convolution filter / test.
        ----
        Syntax: peaks [deviations]
        absolute deviation = number of times the convolution signal is above the noise absolute deviation.
        Default is 5.
        '''

        #TODO: check if the following line gives us what we need
        curve = self.GetActiveCurve()
        defplots = curve.driver.default_plots()[0] #we need the raw, uncorrected plots

        #if 'flatten' in self.config['plotmanips']:
        if self.HasPlotmanipulator('plotmanip_flatten'):
            #flatten=self._find_plotmanip('flatten') #extract flatten plot manipulator
            #defplots=flatten(defplots, self.current)
            defplots = self.plotmanip_flatten(defplots, curve, customvalue=0)
        else:
            self.AppendToOutput('The flatten plot manipulator is not loaded. Enabling it could give better results.')

        peak_location, peak_size = self.has_peaks(defplots, curve)
        self.AppendToOutput('Found ' + str(len(peak_location)) + ' peaks.')
        self.AppendToOutput('peaks ' + curve.filename + ' ' + str(len(peak_location)))
        #to_dump = 'peaks ' + current_curve.filename + ' ' + str(len(peak_location))
        #self.outlet.push(to_dump)

        #if no peaks, we have nothing to plot. exit.
        if peak_location:
            #otherwise, we plot the peak locations.
            xplotted_ret = curve.plots[0].vectors[1][0]
            yplotted_ret = curve.plots[0].vectors[1][1]
            xgood = [xplotted_ret[index] for index in peak_location]
            ygood = [yplotted_ret[index] for index in peak_location]

            curve.plots[0].add_set(xgood, ygood)
            curve.plots[0].styles.append('scatter')
            curve.plots[0].colors.append('indigo')

            #recplot = self._get_displayed_plot()
            #recplot.vectors.append([xgood,ygood])
            #if recplot.styles == []:
                #recplot.styles = [None, None, 'scatter']
                #recplot.colors = [None, None, None]
            #else:
                #recplot.styles += ['scatter']
                #recplot.colors += [None]

            #self._send_plot([recplot])
            self.UpdatePlot()

    def do_convfilt(self):
        '''
        CONVFILT
        (flatfilts.py)
        Filters out flat (featureless) curves of the current playlist,
        creating a playlist containing only the curves with potential
        features.
        ------------
        Syntax:
        convfilt [min_npks min_deviation]

        min_npks = minmum number of peaks
        (to set the default, see convfilt.conf file; CONVCONF and SETCONF commands)

        min_deviation = minimum signal/noise ratio *in the convolution*
        (to set the default, see convfilt.conf file; CONVCONF and SETCONF commands)

        If called without arguments, it uses default values.
        '''

        self.AppendToOutput('Processing playlist...')
        self.AppendToOutput('(Please wait)')
        minpeaks = self.GetIntFromConfig('flatfilts', 'convfilt', 'minpeaks')
        features = []
        playlist = self.GetActivePlaylist()

        curves = self.GetActivePlaylist().curves
        curve_index = 0
        for curve in curves:
            curve_index += 1
            try:
                peak_location, peak_size = self.exec_has_peaks(curve)
                number_of_peaks = len(peak_location)
                if number_of_peaks != 1:
                    if number_of_peaks > 0:
                        feature_string = str(number_of_peaks) + ' features'
                    else:
                        feature_string = 'no features'
                else:
                    feature_string = '1 feature'
                if number_of_peaks >= minpeaks:
                    feature_string += '+'
                output_string = ''.join(['Curve ', curve.name, '(', str(curve_index), '/', str(len(curves)), '): ', feature_string])
            except:
                peak_location = []
                peak_size = []
                output_string = ''.join(['Curve ', curve.name, '(', str(curve_index), '/', str(len(curves)), '): cannot be filtered. Probably unable to retrieve force data from corrupt file.'])
            self.AppendToOutput(output_string)
            if number_of_peaks >= minpeaks:
                curve.peak_location = peak_location
                curve.peak_size = peak_size
                features.append(curve_index - 1)

        #TODO: do we need this? Flattening might not be necessary/desired
        #Warn that no flattening had been done.
        if not self.HasPlotmanipulator('plotmanip_flatten'):
            self.AppendToOutput('Flatten manipulator was not found. Processing was done without flattening.')
            self.AppendToOutput('Try to enable it in the configuration file for better results.')
        if not features:
            self.AppendToOutput('Found nothing interesting. Check the playlist, could be a bug or criteria could be too stringent.')
        else:
            if len(features) < playlist.count:
                self.AppendToOutput(''.join(['Found ', str(len(features)), ' potentially interesting curves.']))
                self.AppendToOutput('Regenerating playlist...')
                playlist_filtered = playlist.filter_curves(features)
                self.AddPlaylist(playlist_filtered, name='convfilt')
            else:
                self.AppendToOutput('No curves filtered. Try different filtering criteria.')

