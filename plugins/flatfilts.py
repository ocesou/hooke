#!/usr/bin/env python

'''
flatfilts.py

Force spectroscopy files filtering of flat files.

Plugin dependencies:
procplots.py (plot processing plugin)

Copyright ???? by ?
with modifications by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

import lib.libhooke as lh
import wxversion
wxversion.select(lh.WX_GOOD)

import copy
from numpy import diff, mean

import lib.peakspot as lps
import lib.curve

class flatfiltsCommands:

    def do_flatfilt(self):
        '''
        FLATFILT
        (flatfilts.py)
        Filters out flat (featureless) files of the current playlist,
        creating a playlist containing only the files with potential
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

        self.AppendToOutput('Processing playlist...')
        self.AppendToOutput('(Please wait)')
        features = []
        playlist = self.GetActivePlaylist()
        files = playlist.files
        file_index = 0
        for current_file in files:
            file_index += 1
            try:
                current_file.identify(self.drivers)
                notflat = self.has_features(copy.deepcopy(current_file))
                feature_string = ''
                if notflat != 1:
                    if notflat > 0:
                        feature_string = str(notflat) + ' features'
                    else:
                        feature_string = 'no features'
                else:
                    feature_string = '1 feature'
                output_string = ''.join(['Curve ', current_file.name, '(', str(file_index), '/', str(len(files)), '): ', feature_string])
            except:
                notflat = False
                output_string = ''.join(['Curve ', current_file.name, '(', str(file_index), '/', str(len(files)), '): cannot be filtered. Probably unable to retrieve force data from corrupt file.'])
            self.AppendToOutput(output_string)
            if notflat:
                current_file.features = notflat
                features.append(file_index - 1)
        if not features:
            self.AppendToOutput('Found nothing interesting. Check the playlist, could be a bug or criteria could be too stringent.')
        else:
            if len(features) < playlist.count:
                self.AppendToOutput(''.join(['Found ', str(len(features)), ' potentially interesting files.']))
                self.AppendToOutput('Regenerating playlist...')
                playlist_filtered = playlist.filter_curves(features)
                self.AddPlaylist(playlist_filtered, name='flatfilt')
            else:
                self.AppendToOutput('No files filtered. Try different filtering criteria.')

    def has_features(self, current_file):
        '''
        decides if a curve is flat enough to be rejected from analysis: it sees if there
        are at least min_npks points that are higher than min_deviation times the absolute value
        of noise.

        Algorithm original idea by Francesco Musiani, with my tweaks and corrections.
        '''
        #TODO: shoudl medianfilter be variable?
        medianfilter = 7
        #medianfilter = self.GetIntFromConfig('flatfilts', 'flatfilt', 'median_filter')
        mindeviation = self.GetIntFromConfig('flatfilts', 'flatfilt', 'min_deviation')
        minpeaks = self.GetIntFromConfig('flatfilts', 'flatfilt', 'min_npks')

        retvalue = 0

        #we assume the first is the plot with the force curve
        #do the median to better resolve features from noise
        flat_curve = self.plotmanip_median(current_file.plot, current_file, customvalue=medianfilter)

        #absolute value of derivate
        yretdiff = diff(flat_curve.curves[lh.RETRACTION].y)
        yretdiff = [abs(value) for value in yretdiff]
        #average of derivate values
        diffmean = mean(yretdiff)
        yretdiff.sort()
        yretdiff.reverse()
        c_pks = 0
        for value in yretdiff:
            if value / diffmean > mindeviation:
                c_pks += 1
            else:
                break

        if c_pks >= minpeaks:
            retvalue = c_pks

        return retvalue

    ################################################################
    #-----CONVFILT-------------------------------------------------
    #-----Convolution-based peak recognition and filtering.
    #Requires the peakspot.py library

    def has_peaks(self, plot=None, plugin=None):
        '''
        Finds peak position in a force curve.
        FIXME: should be moved to peakspot.py
        #TODO: should this really be moved? this is obviously tied into flatfilts/convfilt
        #flatfilts.py is where 'has_peaks' belongs
        '''

        if plugin is None:
            blindwindow = self.GetFloatFromConfig('flatfilts', 'convfilt', 'blindwindow')
            #need to convert the string that contains the list into a list
            convolution = eval(self.GetStringFromConfig('flatfilts', 'convfilt', 'convolution'))
            maxcut = self.GetFloatFromConfig('flatfilts', 'convfilt', 'maxcut')
            mindeviation = self.GetFloatFromConfig('flatfilts', 'convfilt', 'mindeviation')
            positive = self.GetBoolFromConfig('flatfilts', 'convfilt', 'positive')
            seedouble = self.GetIntFromConfig('flatfilts', 'convfilt', 'seedouble')
            stable = self.GetFloatFromConfig('flatfilts', 'convfilt', 'stable')
        else:
            blindwindow = self.GetFloatFromConfig(plugin.name, plugin.section, plugin.prefix + 'blindwindow')
            #need to convert the string that contains the list into a list
            convolution = eval(self.GetStringFromConfig(plugin.name, plugin.section, plugin.prefix + 'convolution'))
            maxcut = self.GetFloatFromConfig(plugin.name, plugin.section, plugin.prefix + 'maxcut')
            mindeviation = self.GetFloatFromConfig(plugin.name, plugin.section, plugin.prefix + 'mindeviation')
            positive = self.GetBoolFromConfig(plugin.name, plugin.section, plugin.prefix + 'positive')
            seedouble = self.GetIntFromConfig(plugin.name, plugin.section, plugin.prefix + 'seedouble')
            stable = self.GetFloatFromConfig(plugin.name, plugin.section, plugin.prefix + 'stable')

        if plot is None:
            plot = self.GetDisplayedPlotCorrected()

        retraction = plot.curves[lh.RETRACTION]
        #Calculate convolution
        convoluted = lps.conv_dx(retraction.y, convolution)

        #surely cut everything before the contact point
        cut_index = self.find_contact_point(plot)
        #cut even more, before the blind window
        start_x = retraction.x[cut_index]
        blind_index = 0
        for value in retraction.x[cut_index:]:
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
            maxpk = min(retraction.y[peak - 10:peak + 10])
            index_maxpk = retraction.y[peak - 10:peak + 10].index(maxpk) + (peak - 10)
            peak_location[i] = index_maxpk

        return peak_location, peak_size

    def do_peaks(self, plugin=None, peak_location=None, peak_size=None):
        '''
        Test command for convolution filter.
        ----
        Syntax: peaks [deviations]
        absolute deviation = number of times the convolution signal is above the noise absolute deviation.
        Default is 5.
        '''

        if plugin is None:
            color = self.GetColorFromConfig('flatfilts', 'peaks', 'color')
            size = self.GetIntFromConfig('flatfilts', 'peaks', 'size')
        else:
            color = self.GetColorFromConfig(plugin.name, plugin.section, plugin.prefix + 'color')
            size = self.GetIntFromConfig(plugin.name, plugin.section, plugin.prefix + 'size')

        plot = self.GetDisplayedPlotCorrected()

        if peak_location is None and peak_size is None:
            if not self.AppliesPlotmanipulator('flatten'):
                self.AppendToOutput('The flatten plot manipulator is not loaded. Enabling it could give better results.')

            peak_location, peak_size = self.has_peaks(plot)
            if len(peak_location) != 1:
                peak_str = ' peaks.'
            else:
                peak_str = ' peak.'
            self.AppendToOutput('Found ' + str(len(peak_location)) + peak_str)

        if peak_location:
            retraction = plot.curves[lh.RETRACTION]

            peaks = lib.curve.Curve()
            peaks.color = color
            peaks.size = size
            peaks.style = 'scatter'
            peaks.title = 'Peaks'
            peaks.x = [retraction.x[index] for index in peak_location]
            peaks.y = [retraction.y[index] for index in peak_location]

            plot.curves.append(peaks)

            self.UpdatePlot(plot)

    def do_convfilt(self):
        '''
        Filters out flat (featureless) files of the current playlist,
        creating a playlist containing only the files with potential
        features.
        ------------
        min_npks: minmum number of peaks
        min_deviation: minimum signal/noise ratio *in the convolution*
        '''

        self.AppendToOutput('Processing playlist...')
        self.AppendToOutput('(Please wait)')
        apply_plotmanipulators = self.GetStringFromConfig('flatfilts', 'convfilt', 'apply_plotmanipulators')
        minpeaks = self.GetIntFromConfig('flatfilts', 'convfilt', 'minpeaks')
        features = []
        playlist = self.GetActivePlaylist()

        files = self.GetActivePlaylist().files
        file_index = 0
        for current_file in files:
            number_of_peaks = 0
            file_index += 1
            try:
                current_file.identify(self.drivers)
                plot = self.ApplyPlotmanipulators(current_file.plot, current_file)
                peak_location, peak_size = self.has_peaks(plot)
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
                output_string = ''.join(['Curve ', current_file.name, '(', str(file_index), '/', str(len(files)), '): ', feature_string])
            except:
                peak_location = []
                peak_size = []
                output_string = ''.join(['Curve ', current_file.name, '(', str(file_index), '/', str(len(files)), '): cannot be filtered. Probably unable to retrieve force data from corrupt file.'])
            self.AppendToOutput(output_string)
            if number_of_peaks >= minpeaks:
                current_file.peak_location = peak_location
                current_file.peak_size = peak_size
                features.append(file_index - 1)

        #TODO: warn when flatten is not applied?
        if not features:
            self.AppendToOutput('Found nothing interesting. Check the playlist, could be a bug or criteria could be too stringent.')
        else:
            if len(features) < playlist.count:
                self.AppendToOutput(''.join(['Found ', str(len(features)), ' potentially interesting files.']))
                self.AppendToOutput('Regenerating playlist...')
                playlist_filtered = playlist.filter_curves(features)
                self.AddPlaylist(playlist_filtered, name='convfilt')
            else:
                self.AppendToOutput('No files filtered. Try different filtering criteria.')

