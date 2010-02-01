#!/usr/bin/env python

'''
autopeak.py

Automatic peak detection and analysis.

Copyright ???? by ?
with modifications by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

import lib.libhooke as lh
import wxversion
wxversion.select(lh.WX_GOOD)

import copy
from numpy import mean, RankWarning

import warnings
warnings.simplefilter('ignore', RankWarning)

#import config
import lib.plugin
import lib.results

class autopeakCommands:
    '''
    Autopeak carries out force curve fitting with a chosen model:
        - WLC
        - FJC
        - FJC-PEG
    '''

    def do_autopeak(self, plot=None):
        '''
        AUTOPEAK
        (autopeak.py)
        Automatically performs a number of analyses on the peaks of the given curve.
        Currently it automatically:
        - fits peaks with WLC or FJC function (depending on how the fit_function variable is set)
        - measures peak maximum forces with a baseline
        - measures slope in proximity of peak maximum
        Requires flatten plotmanipulator , fit.py plugin , flatfilts.py plugin with convfilt

        Syntax:
        autopeak [rebase] [persistence_length=value] [t=value] [noauto] [reclick]

        rebase : Re-asks baseline interval

        persistence_length=[value] : Use a fixed persistent length for the fit. If persistence_length is not given,
                     the fit will be a 2-variable
                     fit. DO NOT put spaces between 'persistence_length', '=' and the value.
                     The value must be in nanometers.
                     Scientific notation like 0.35 is fine.

        t=[value] : Use a user-defined temperature. The value must be in
                    kelvins; by default it is 293 K.
                    DO NOT put spaces between 't', '=' and the value.

        noauto : allows for clicking the contact point by
                 hand (otherwise it is automatically estimated) the first time.
                 If subsequent measurements are made, the same contact point
                 clicked the first time is used

        reclick : redefines by hand the contact point, if noauto has been used before
                  but the user is unsatisfied of the previously choosen contact point.

        usepoints : fit interval by number of points instead than by nanometers

        noflatten : does not use the "flatten" plot manipulator

        When you first issue the command, it will ask for the filename. If you are giving the filename
        of an existing file, autopeak will resume it and append measurements to it. If you are giving
        a new filename, it will create the file and append to it until you close Hooke.


        Useful variables (to set with SET command):
        ---
        fit_function = type of function to use for elasticity. If "wlc" worm-like chain is used, if "fjc" freely jointed
                       chain is used

        temperature= temperature of the system for wlc/fjc fit (in K)

        auto_slope_span = number of points on which measure the slope, for slope

        auto_fit_nm = number of nm to fit before the peak maximum, for WLC/FJC (if usepoints false)
        auto_fit_points = number of points to fit before the peak maximum, for WLC/FJC (if usepoints true)

        baseline_clicks = contact point: no baseline, f=0 at the contact point (whether hand-picked or automatically found)
                          automatic:     automatic baseline
                          1 point:       decide baseline with a single click and length defined in auto_left_baseline
                          2 points:      let user click points of baseline
        auto_left_baseline = length in nm to use as baseline from the right point (if baseline_clicks = automatic , 1 point)
        auto_right_baseline = distance in nm of peak-most baseline point from last peak (if baseline_clicks = automatic)

        auto_min_p ; auto_max_p = Minimum and maximum persistence length (if using WLC) or Kuhn length (if using FJC)
                                  outside of which the peak is automatically discarded (in nm)
        '''

        #default fit etc. variables
        auto_fit_nm = self.GetFloatFromConfig('autopeak', 'auto_fit_nm')
        auto_left_baseline = self.GetFloatFromConfig('autopeak', 'auto_left_baseline')
        auto_max_p = self.GetFloatFromConfig('autopeak', 'auto_max_p')
        auto_min_p = self.GetFloatFromConfig('autopeak', 'auto_min_p')
        auto_right_baseline = self.GetFloatFromConfig('autopeak', 'auto_right_baseline')
        baseline_clicks = self.GetStringFromConfig('autopeak', 'baseline_clicks')
        fit_function = self.GetStringFromConfig('autopeak', 'fit_function')
        fit_points = self.GetIntFromConfig('autopeak', 'auto_fit_points')
        noauto = self.GetBoolFromConfig('autopeak', 'noauto')
        #noflatten: if true we do not flatten the curve
        noflatten = self.GetBoolFromConfig('autopeak', 'noflatten')
        peak_show = self.GetBoolFromConfig('autopeak', 'peak_show')
        persistence_length = self.GetFloatFromConfig('autopeak', 'persistence_length')
        #rebase: redefine the baseline
        rebase = self.GetBoolFromConfig('autopeak', 'rebase')
        reclick = self.GetBoolFromConfig('autopeak', 'reclick')
        slope_span = self.GetIntFromConfig('autopeak', 'auto_slope_span')
        T = self.GetFloatFromConfig('autopeak', 'temperature')
        usepl = self.GetBoolFromConfig('autopeak', 'usepl')
        if not usepl:
            pl_value = None
        else:
            pl_value = persistence_length / 10**9
        usepoints = self.GetBoolFromConfig('autopeak', 'usepoints')
        whatset_str = self.GetStringFromConfig('autopeak', 'whatset')
        if whatset_str == 'extension':
            whatset = lh.EXTENSION
        if whatset_str == 'retraction':
            whatset = lh.RETRACTION

        #TODO: should this be variable?
        delta_force = 10

        #setup header column labels for results
        if fit_function == 'wlc':
            fit_results = lib.results.ResultsWLC()
            segment_str = 'Persistence length'
            sigma_segment_str = 'sigma persistence length'
        elif fit_function == 'fjc' or fit_function == 'fjcPEG':
            fit_results = lib.results.ResultsFJC()
            segment_str = 'Kuhn length'
            sigma_segment_str = 'sigma Kuhn length'
        else:
            self.AppendToOutput('Unknown fit function, Please set fit_function as wlc, fjc or fjcPEG')
            return

        #initialize output data vectors
        c_lengths = []
        p_lengths = []
        sigma_c_lengths = []
        sigma_p_lengths = []
        forces = []
        slopes = []

        #pick up plot
        if plot is None:
            plot = copy.deepcopy(self.GetActivePlot())
        filename = self.GetActiveFile().name

        #apply all active plotmanipulators and add the 'manipulated' data
        for plotmanipulator in self.plotmanipulators:
            if self.GetBoolFromConfig('core', 'plotmanipulators', plotmanipulator.name):
                if plotmanipulator.name == 'flatten':
                    if not noflatten:
                        plot = plotmanipulator.method(plot, self.GetActiveFile())
                else:
                    plot = plotmanipulator.method(plot, self.GetActiveFile())

        #--Using points instead of nm interval
        if not usepoints:
            fit_points = None

        #--Contact point arguments
        if reclick:
            contact_point, contact_point_index = self.pickup_contact_point(filename=filename)
        elif noauto:
            if self.wlccontact_index is None or self.wlccurrent != filename:
                contact_point, contact_point_index = self.pickup_contact_point(filename=filename)
            else:
                contact_point = self.wlccontact_point
                contact_point_index = self.wlccontact_index
        else:
            #Automatically find contact point
            cindex = self.find_contact_point(plot)
            contact_point = self._clickize(plot.curves[lh.RETRACTION].x, plot.curves[lh.EXTENSION].y, cindex)

        #peak_size comes from convolution curve
        peak_location, peak_size = self.find_current_peaks(plot=plot, noflatten=noflatten)

        if len(peak_location) == 0:
            self.AppendToOutput('No peaks to fit.')
            return

        #Pick up force baseline
        if baseline_clicks == 'contact point':
            try:
                avg = plot.curves[lh.RETRACTION].y[contact_point_index]
            except:
                avg = plot.curves[lh.RETRACTION].y[cindex]

        if rebase or (self.basecurrent != filename) or self.basepoints is None:
            if baseline_clicks == 'automatic':
                self.basepoints = []
                base_index_0 = peak_location[-1] + self.fit_interval_nm(peak_location[-1], plot.curves[lh.RETRACTION].x, auto_right_baseline, False)
                self.basepoints.append(self._clickize(plot.curves[lh.RETRACTION].x, plot.curves[lh.RETRACTION].y, base_index_0))
                base_index_1 = self.basepoints[0].index + self.fit_interval_nm(self.basepoints[0].index, plot.curves[lh.RETRACTION].x, auto_left_baseline, False)
                self.basepoints.append(self._clickize(plot.curves[lh.RETRACTION].x, plot.curves[lh.RETRACTION].y, base_index_1))
            if baseline_clicks == '1 point':
                self.basepoints=self._measure_N_points(N=1, message='Click on 1 point to select the baseline.', whatset=whatset)
                base_index_1 = self.basepoints[0].index + self.fit_interval_nm(self.basepoints[0].index, plot.curves[lh.RETRACTION].x, auto_left_baseline, False)
                self.basepoints.append(self._clickize(plot.curves[lh.RETRACTION].x, plot.curves[lh.RETRACTION].y, base_index_1))
            if baseline_clicks == '2 points':
                self.basepoints=self._measure_N_points(N=2, message='Click on 2 points to select the baseline.', whatset=whatset)
        if baseline_clicks != 'contact point':
            boundaries=[self.basepoints[0].index, self.basepoints[1].index]
            boundaries.sort()
            to_average = plot.curves[lh.RETRACTION].y[boundaries[0]:boundaries[1]] #y points to average
            avg = mean(to_average)
            self.basecurrent = filename

        x_values = plot.curves[lh.RETRACTION].x
        y_values = plot.curves[lh.RETRACTION].y
        for index, peak in enumerate(peak_location):
            #WLC FITTING
            #define fit interval
            if not usepoints:
                fit_points = self.fit_interval_nm(peak, plot.curves[lh.RETRACTION].x, auto_fit_nm, True)
            peak_point = self._clickize(x_values, y_values, peak)
            other_fit_point=self._clickize(x_values, y_values, peak - fit_points)

            #points for the fit
            points = [contact_point, peak_point, other_fit_point]

            if abs(peak_point.index - other_fit_point.index) < 2:
                continue

            if fit_function == 'wlc':
                params, yfit, xfit, fit_errors = self.wlc_fit(points, x_values, y_values, pl_value, T, return_errors=True)
            elif fit_function == 'fjc':
                params, yfit, xfit, fit_errors = self.fjc_fit(points, x_values, y_values, pl_value, T, return_errors=True)
            elif fit_function == 'fjcPEG':
                params, yfit, xfit, fit_errors = self.fjcPEG_fit(points, x_values, y_values, pl_value, T, return_errors=True)

            #Measure forces
            delta_to_measure = y_values[peak - delta_force:peak + delta_force]
            y = min(delta_to_measure)
            #save force values (pN)
            #Measure slopes
            slope = self.linefit_between(peak - slope_span, peak, whatset=lh.RETRACTION)[0]

            #check fitted data and, if right, add peak to the measurement
            fit_result = lib.results.Result()

            fit_result.result['Contour length'] = params[0]
            fit_result.result['sigma contour length'] = fit_errors[0]
            fit_result.result['Rupture force'] = abs(y - avg)
            fit_result.result['Slope'] = slope
            active_file = self.GetActiveFile()
            if active_file.driver.retract_velocity:
                fit_result.result['Loading rate'] = slope * active_file.driver.retract_velocity
            else:
                fit_result.result['Loading rate'] = -1
            if len(params) == 1: #if we did choose 1-value fit
                fit_result.result[segment_str] = pl_value
                fit_result.result[sigma_segment_str] = 0

                p_lengths.append(pl_value)
                c_lengths.append(params[0]*(1.0e+9))
                sigma_p_lengths.append(0)
                sigma_c_lengths.append(fit_errors[0]*(1.0e+9))
                forces.append(abs(y-avg)*(1.0e+12))
                slopes.append(slope)
            else: #2-value fit
                p_leng = params[1] * (1.0e+9)
                #check if persistence length makes sense, otherwise discard peak.
                if p_leng > auto_min_p and p_leng < auto_max_p:
                    fit_result.result[segment_str] = params[1]
                    fit_result.result[sigma_segment_str] = fit_errors[1]

                    p_lengths.append(p_leng)
                    c_lengths.append(params[0]*(1.0e+9))
                    sigma_c_lengths.append(fit_errors[0]*(1.0e+9))
                    sigma_p_lengths.append(fit_errors[1]*(1.0e+9))
                    forces.append(abs(y-avg)*(1.0e+12))
                    slopes.append(slope)
                else:
                    fit_result.result = {}

            if len(fit_result.result) > 0:
                fit_result.label = fit_function + '_' + str(index)
                fit_result.title = plot.curves[lh.RETRACTION].title
                fit_result.units.x = plot.curves[lh.RETRACTION].units.x
                fit_result.units.y = plot.curves[lh.RETRACTION].units.y
                fit_result.visible = True
                fit_result.x = xfit
                fit_result.y = yfit
                fit_results.results.append(fit_result)

        if fit_results.results:
            fit_results.set_multipliers(0)
            plot = self.GetActivePlot()
            plot.results[fit_function] = fit_results
            if peak_show:
                plugin = lib.plugin.Plugin()
                plugin.name = 'autopeak'
                plugin.section = 'autopeak'
                plugin.prefix = 'peak_'
                self.do_peaks(plugin=plugin, peak_location=peak_location, peak_size=peak_size)
            else:
                self.UpdatePlot()

        else:
            self.AppendToOutput('No peaks found.')

        #TODO:
        #self.do_note('autopeak')

    def find_current_peaks(self, plot=None, noflatten=True):
        if not noflatten:
            plot_temp = self.plotmanip_flatten(plot, self.GetActiveFile(), customvalue=1)
        peak_location, peak_size = self.has_peaks(plot_temp)
        return peak_location, peak_size

    def fit_interval_nm(self, start_index, x_vect, nm, backwards):
        '''
        Calculates the number of points to fit, given a fit interval in nm
        start_index: index of point
        plot: plot to use
        backwards: if true, finds a point backwards.
        '''

        c = 0
        i = start_index
        maxlen=len(x_vect)
        while abs(x_vect[i] - x_vect[start_index]) * (10**9) < nm:
            if i == 0 or i == maxlen-1: #we reached boundaries of vector!
                return c
            if backwards:
                i -= 1
            else:
                i += 1
            c += 1
        return c

    def pickup_contact_point(self, filename=''):
        '''
        macro to pick up the contact point by clicking
        '''
        contact_point = self._measure_N_points(N=1, message='Please click on the contact point.')[0]
        contact_point_index = contact_point.index
        self.wlccontact_point = contact_point
        self.wlccontact_index = contact_point.index
        self.wlccurrent = filename
        return contact_point, contact_point_index


