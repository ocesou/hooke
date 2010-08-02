#!/usr/bin/env python

'''
generalvclamp.py

Plugin regarding general velocity clamp measurements

Copyright 2008 by Massimo Sandal, Fabrizio Benedetti, Marco Brucale, Bruno Samori (University of Bologna, Italy),
and Alberto Gomez-Casado (University of Twente)
with modifications by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

import lib.libhooke as lh
import wxversion
wxversion.select(lh.WX_GOOD)

import numpy as np
import scipy as sp

import warnings
warnings.simplefilter('ignore', np.RankWarning)

import lib.curve
import lib.prettyformat

class generalvclampCommands:

    def _plug_init(self):
        self.basecurrent = ''
        self.basepoints = []
        #TODO: what is self.autofile for?
        #self.autofile = ''

    def do_distance(self):
        '''
        DISTANCE
        (generalvclamp.py)
        Measure the distance (in nm) between two points.
        For a standard experiment this is the delta X distance.
        For a force clamp experiment this is the delta Y distance (actually becomes
        an alias of zpiezo)
        -----------------
        Syntax: distance
        '''
        color = self.GetColorFromConfig('generalvclamp', 'distance', 'color')
        decimals = self.GetIntFromConfig('generalvclamp', 'distance', 'decimals')
        prefix = self.GetStringFromConfig('generalvclamp', 'distance', 'prefix')
        multiplier = 10 ** lib.prettyformat.get_exponent(prefix)
        show =  self.GetBoolFromConfig('generalvclamp', 'distance', 'show')
        show_in_legend = self.GetBoolFromConfig('generalvclamp', 'distance', 'show_in_legend')
        size = self.GetIntFromConfig('generalvclamp', 'distance', 'size')
        whatset_str = self.GetStringFromConfig('generalvclamp', 'distance', 'whatset')
        whatset = 'retraction'
        if whatset_str == 'extension':
            whatset = lh.EXTENSION
        if whatset_str == 'retraction':
            whatset = lh.RETRACTION

        active_file = self.GetActiveFile()
        if active_file.driver.experiment == 'clamp':
            self.AppendToOutput('You wanted to use zpiezo perhaps?')
            return
        plugin = lib.plugin.Plugin()
        plugin.name = 'generalvclamp'
        plugin.section = 'distance'
        delta = self._delta(message='Click 2 points to measure the distance.', whatset=whatset)

        plot = self.GetDisplayedPlotCorrected()
        if show:
            #add the points to the plot
            points = lib.curve.Curve()
            points.color = color
            if show_in_legend:
                points.label = 'distance'
            else:
                points.label = '_nolegend_'
            points.size = size
            points.style = 'scatter'
            points.units.x = delta.units.x
            points.units.y = delta.units.y
            points.x = [delta.point1.x, delta.point2.x]
            points.y = [delta.point1.y, delta.point2.y]
            plot.curves.append(points)

        self.UpdatePlot(plot)

        output_str = lib.prettyformat.pretty_format(abs(delta.get_delta_x()), delta.units.x, decimals, multiplier)
        self.AppendToOutput(''.join(['Distance: ', output_str]))

    def do_force(self):
        '''
        FORCE
        (generalvclamp.py)
        Measure the force difference (in pN) between two points
        ---------------
        Syntax: force
        '''
        color = self.GetColorFromConfig('generalvclamp', 'force', 'color')
        decimals = self.GetIntFromConfig('generalvclamp', 'force', 'decimals')
        prefix = self.GetStringFromConfig('generalvclamp', 'force', 'prefix')
        multiplier = 10 ** lib.prettyformat.get_exponent(prefix)
        show = self.GetBoolFromConfig('generalvclamp', 'force', 'show')
        show_in_legend = self.GetBoolFromConfig('generalvclamp', 'force', 'show_in_legend')
        size = self.GetIntFromConfig('generalvclamp', 'force', 'size')
        whatset_str = self.GetStringFromConfig('generalvclamp', 'force', 'whatset')
        whatset = 'retraction'
        if whatset_str == 'extension':
            whatset = lh.EXTENSION
        if whatset_str == 'retraction':
            whatset = lh.RETRACTION

        active_file = self.GetActiveFile()
        if active_file.driver.experiment == 'clamp':
            self.AppendToOutput('This command makes no sense for a force clamp experiment.')
            return
        plugin = lib.plugin.Plugin()
        plugin.name = 'generalvclamp'
        plugin.section = 'force'
        delta = self._delta(message='Click 2 points to measure the force.', whatset=whatset)

        plot = self.GetDisplayedPlotCorrected()
        if show:
            #add the points to the plot
            points = lib.curve.Curve()
            points.color = color
            if show_in_legend:
                points.label = 'force'
            else:
                points.label = '_nolegend_'
            points.size = size
            points.style = 'scatter'
            points.units.x = delta.units.x
            points.units.y = delta.units.y
            points.x = [delta.point1.x, delta.point2.x]
            points.y = [delta.point1.y, delta.point2.y]
            plot.curves.append(points)

        self.UpdatePlot(plot)

        output_str = lib.prettyformat.pretty_format(abs(delta.get_delta_y()), delta.units.y, decimals, multiplier)
        self.AppendToOutput(''.join(['Force: ', output_str]))

    def do_forcebase(self):
        '''
        FORCEBASE
        (generalvclamp.py)
        Measures the difference in force (in pN) between a point and a baseline
        taken as the average between two points.

        The baseline is fixed once for a given curve and different force measurements,
        unless the user wants it to be recalculated
        ------------
        Syntax: forcebase [rebase]
                rebase: Forces forcebase to ask again the baseline
                max: Instead of asking for a point to measure, asks for two points and use
                     the maximum peak in between
        '''
        baseline_color =  self.GetColorFromConfig('generalvclamp', 'forcebase', 'baseline_color')
        baseline_show = self.GetBoolFromConfig('generalvclamp', 'forcebase', 'baseline_show')
        baseline_show_in_legend = self.GetBoolFromConfig('generalvclamp', 'forcebase', 'baseline_show_in_legend')
        baseline_size = self.GetIntFromConfig('generalvclamp', 'forcebase', 'baseline_size')
        decimals = self.GetIntFromConfig('generalvclamp', 'forcebase', 'decimals')
        maximum_color =  self.GetColorFromConfig('generalvclamp', 'forcebase', 'maximum_color')
        maximum_show = self.GetBoolFromConfig('generalvclamp', 'forcebase', 'maximum_show')
        maximum_show_in_legend = self.GetBoolFromConfig('generalvclamp', 'forcebase', 'maximum_show_in_legend')
        maximum_size = self.GetIntFromConfig('generalvclamp', 'forcebase', 'maximum_size')
        maximumrange_color =  self.GetColorFromConfig('generalvclamp', 'forcebase', 'maximumrange_color')
        maximumrange_show = self.GetBoolFromConfig('generalvclamp', 'forcebase', 'maximumrange_show')
        maximumrange_show_in_legend = self.GetBoolFromConfig('generalvclamp', 'forcebase', 'maximumrange_show_in_legend')
        maximumrange_size = self.GetIntFromConfig('generalvclamp', 'forcebase', 'maximumrange_size')
        maxpoint = self.GetBoolFromConfig('generalvclamp', 'forcebase', 'max')
        prefix = self.GetStringFromConfig('generalvclamp', 'forcebase', 'prefix')
        multiplier = 10 ** lib.prettyformat.get_exponent(prefix)
        rebase = self.GetBoolFromConfig('generalvclamp', 'forcebase', 'rebase')
        whatset_str = self.GetStringFromConfig('generalvclamp', 'forcebase', 'whatset')
        whatset = 'retraction'
        if whatset_str == 'extension':
            whatset = lh.EXTENSION
        if whatset_str == 'retraction':
            whatset = lh.RETRACTION

        plot = self.GetDisplayedPlotCorrected()

        filename = self.GetActiveFile().name
        if rebase or (self.basecurrent != filename):
            self.basepoints = self._measure_N_points(N=2, message='Click on 2 points to select the baseline.', whatset=whatset)
            self.basecurrent = filename

        #TODO: maxpoint does not seem to be picking up the 'real' maximum (at least not with test.hkp/default.000)
        maximumrange_points = []
        maximum_point = []
        if maxpoint:
            maximumrange_points = self._measure_N_points(N=2, message='Click 2 points to select the range for maximum detection.', whatset=whatset)
            boundpoints = [maximumrange_points[0].index, maximumrange_points[1].index]
            boundpoints.sort()
            try:
                vector_x = plot.curves[whatset].x[boundpoints[0]:boundpoints[1]]
                vector_y = plot.curves[whatset].y[boundpoints[0]:boundpoints[1]]
                y = min(vector_y)
                index = vector_y.index(y)
                maximum_point = [self._clickize(vector_x, vector_y, index)]
            except ValueError:
                self.AppendToOutput('Chosen interval not valid. Try picking it again. Did you pick the same point as begin and end of the interval?')
                return
        else:
            maximum_point = self._measure_N_points(N=1, message='Click on the point to measure.', whatset=whatset)
            y = maximum_point[0].graph_coords[1]

        boundaries = [self.basepoints[0].index, self.basepoints[1].index]
        boundaries.sort()
        to_average = plot.curves[whatset].y[boundaries[0]:boundaries[1]] #y points to average

        avg = np.mean(to_average)
        forcebase = abs(y - avg)

        curve = plot.curves[whatset]
        if self.basepoints and baseline_show:
            #add the baseline points to the plot
            baseline = lib.curve.Curve()
            baseline.color = baseline_color
            if baseline_show_in_legend:
                baseline.label = 'baseline'
            else:
                baseline.label = '_nolegend_'
            baseline.size = baseline_size
            baseline.style = 'scatter'
            baseline.units.x = curve.units.x
            baseline.units.y = curve.units.y
            for point in self.basepoints:
                baseline.x += [point.graph_coords[0]]
                baseline.y += [point.graph_coords[1]]
            plot.curves.append(baseline)

        if maximumrange_points and maximumrange_show:
            #add the range points to the plot
            maximumrange = lib.curve.Curve()
            maximumrange.color = maximumrange_color
            if maximumrange_show_in_legend:
                maximumrange.label = 'maximumrange'
            else:
                maximumrange.label = '_nolegend_'
            maximumrange.size = maximumrange_size
            maximumrange.style = 'scatter'
            maximumrange.units.x = curve.units.x
            maximumrange.units.y = curve.units.y
            for point in maximumrange_points:
                maximumrange.x += [point.graph_coords[0]]
                maximumrange.y += [point.graph_coords[1]]
            plot.curves.append(maximumrange)

        if maximum_show:
            #add the maximum to the plot
            maximum = lib.curve.Curve()
            maximum.color = maximum_color
            if maximum_show_in_legend:
                maximum.label = 'maximum'
            else:
                maximum.label = '_nolegend_'
            maximum.size = maximum_size
            maximum.style = 'scatter'
            maximum.units.x = curve.units.x
            maximum.units.y = curve.units.y
            maximum.x = [maximum_point[0].graph_coords[0]]
            maximum.y = [maximum_point[0].graph_coords[1]]
            plot.curves.append(maximum)

        self.UpdatePlot(plot)

        unit_str = plot.curves[whatset].units.y
        output_str = lib.prettyformat.pretty_format(forcebase, unit_str, decimals, multiplier)
        self.AppendToOutput(''.join(['Force: ', output_str]))

    def plotmanip_multiplier(self, plot, current, customvalue=False):
        '''
        Multiplies all the Y values of an SMFS curve by a value stored in the 'force_multiplier'
        configuration variable. Useful for calibrations and other stuff.
        '''

        #not a smfs curve...
        if current.driver.experiment != 'smfs':
            return plot

        force_multiplier = self.GetFloatFromConfig('generalvclamp', 'force_multiplier')
        if force_multiplier == 1:
            return plot

        plot.curves[lh.EXTENSION].y = [element * force_multiplier for element in plot.curves[lh.EXTENSION].y]
        plot.curves[lh.RETRACTION].y = [element * force_multiplier for element in plot.curves[lh.RETRACTION].y]

        return plot

    def plotmanip_flatten(self, plot, current, customvalue=0):
        '''
        Subtracts a polynomial fit to the non-contact part of the curve, as to flatten it.
        the best polynomial fit is chosen among polynomials of degree 1 to n, where n is
        given by the configuration file or by the customvalue.

        customvalue = int (>0) --> starts the function even if config says no (default=0)
        '''

        #not a smfs curve...
        if current.driver.experiment != 'smfs':
            return current

        #config is not flatten, and customvalue flag is false too
        #if (not self.config['generalvclamp']['flatten'].as_bool('value')) and (customvalue == 0):
        ##TODO: do we need this?
        #if (not self.GetBoolFromConfig('generalvclamp', 'flatten')) and (customvalue == 0):
            #return plot

        max_exponent = 12
        delta_contact = 0

        if customvalue > 0:
            max_cycles = customvalue
        else:
            #Using > 1 usually doesn't help and can give artefacts. However, it could be useful too.
            max_cycles = self.GetIntFromConfig('generalvclamp', 'max_cycles')

        contact_index = self.find_contact_point(plot)

        valn = [[] for item in range(max_exponent)]
        yrn = [0.0 for item in range(max_exponent)]
        errn = [0.0 for item in range(max_exponent)]

        for i in range(int(max_cycles)):
            x_ext = plot.curves[lh.EXTENSION].x[contact_index + delta_contact:]
            y_ext = plot.curves[lh.EXTENSION].y[contact_index + delta_contact:]
            x_ret = plot.curves[lh.RETRACTION].x[contact_index + delta_contact:]
            y_ret = plot.curves[lh.RETRACTION].y[contact_index + delta_contact:]
            for exponent in range(max_exponent):
                try:
                    valn[exponent] = sp.polyfit(x_ext, y_ext, exponent)
                    yrn[exponent] = sp.polyval(valn[exponent], x_ret)
                    errn[exponent] = sp.sqrt(sum((yrn[exponent] - y_ext) ** 2) / float(len(y_ext)))
                except Exception, e:
                    print 'Cannot flatten!'
                    print e
                    return current

            best_exponent = errn.index(min(errn))

            #extension
            ycorr_ext = y_ext - yrn[best_exponent] + y_ext[0] #noncontact part
            yjoin_ext = np.array(plot.curves[lh.EXTENSION].y[0:contact_index + delta_contact]) #contact part
            #retraction
            ycorr_ret = y_ret - yrn[best_exponent] + y_ext[0] #noncontact part
            yjoin_ret = np.array(plot.curves[lh.RETRACTION].y[0:contact_index + delta_contact]) #contact part

            ycorr_ext = np.concatenate((yjoin_ext, ycorr_ext))
            ycorr_ret = np.concatenate((yjoin_ret, ycorr_ret))

            plot.curves[lh.EXTENSION].y = list(ycorr_ext)
            plot.curves[lh.RETRACTION].y = list(ycorr_ret)

        return plot

    #---SLOPE---
    def do_slope(self):
        '''
        SLOPE
        (generalvclamp.py)
        Measures the slope of a delimited chunk on the return trace.
        The chunk can be delimited either by two manual clicks, or have
        a fixed width, given as an argument.
        ---------------
        Syntax: slope [width]
                The facultative [width] parameter specifies how many
                points will be considered for the fit. If [width] is
                specified, only one click will be required.
        Copyright 2008 by Marco Brucale, Massimo Sandal
        '''

        decimals = self.GetIntFromConfig('generalvclamp', 'slope', 'decimals')
        fitspan = self.GetIntFromConfig('generalvclamp', 'slope', 'fitspan')
        point_color = self.GetColorFromConfig('generalvclamp', 'slope', 'point_color')
        point_show = self.GetBoolFromConfig('generalvclamp', 'slope', 'point_show')
        point_show_in_legend = self.GetBoolFromConfig('generalvclamp', 'slope', 'point_show_in_legend')
        point_size = self.GetIntFromConfig('generalvclamp', 'slope', 'point_size')
        slope_color = self.GetColorFromConfig('generalvclamp', 'slope', 'slope_color')
        slope_linewidth = self.GetIntFromConfig('generalvclamp', 'slope', 'slope_linewidth')
        slope_show = self.GetBoolFromConfig('generalvclamp', 'slope', 'slope_show')
        slope_show_in_legend = self.GetBoolFromConfig('generalvclamp', 'slope', 'slope_show_in_legend')
        whatset_str = self.GetStringFromConfig('generalvclamp', 'slope', 'whatset')
        whatset = 'retraction'
        if whatset_str == 'extension':
            whatset = lh.EXTENSION
        if whatset_str == 'retraction':
            whatset = lh.RETRACTION

        # Decides between the two forms of user input
        #TODO: add an option 'mode' with options 'chunk' and 'point'
        if fitspan == 0:
            # Gets the Xs of two clicked points as indexes on the curve curve vector
            clicked_points = []
            points = self._measure_N_points(N=2, message='Click 2 points to select the chunk.', whatset=whatset)
            clicked_points = [points[0].index, points[1].index]
            clicked_points.sort()
        else:
            clicked_points = []
            points = self._measure_N_points(N=1, message='Click on the leftmost point of the chunk (i.e.usually the peak).', whatset=whatset)
            clicked_points = [points[0].index - fitspan, points[0].index]

        # Calls the function linefit_between
        parameters = [0, 0, [], []]
        try:
            parameters = self.linefit_between(clicked_points[0], clicked_points[1], whatset=whatset)
        except:
            self.AppendToOutput('Cannot fit. Did you click the same point twice?')
            return

        plot = self.GetDisplayedPlotCorrected()
        # Makes a vector with the fitted parameters and sends it to the GUI
        xtoplot=parameters[2]
        ytoplot=[]
        x = 0
        for x in xtoplot:
            ytoplot.append((x * parameters[0]) + parameters[1])

        clickvector_x = []
        clickvector_y = []
        for item in points:
            clickvector_x.append(item.graph_coords[0])
            clickvector_y.append(item.graph_coords[1])

        if point_show:
            #add the clicked point to the plot
            point = lib.curve.Curve()
            point.color = point_color
            if point_show_in_legend:
                point.label = 'clicked point'
            else:
                point.label = '_nolegend_'
            point.size = point_size
            point.style = 'scatter'
            point.x = clickvector_x
            point.y = clickvector_y
            plot.curves.append(point)

        if slope_show:
            #add the slope to the plot
            slope = lib.curve.Curve()
            slope.color = slope_color
            if slope_show_in_legend:
                slope.label = 'slope'
            else:
                slope.label = '_nolegend_'
            slope.linewidth = slope_linewidth
            slope.style = 'plot'
            slope.units.x = plot.curves[whatset].units.x
            slope.units.y = plot.curves[whatset].units.y
            slope.x = xtoplot
            slope.y = ytoplot
            plot.curves.append(slope)

        self.UpdatePlot(plot)

        # Outputs the relevant slope parameter
        unit_str = plot.curves[whatset].units.x + '/' + plot.curves[whatset].units.y
        output_str = lib.prettyformat.pretty_format(parameters[0], unit_str, decimals, 1)
        self.AppendToOutput(''.join(['Slope: ', output_str]))

    def linefit_between(self, index1, index2, whatset=lh.RETRACTION):
        '''
        Creates two vectors (xtofit, ytofit) slicing out from the
        curve return trace a portion delimited by the two indeces
        given as arguments.
        Then does a least squares linear fit on that slice.
        Finally returns [0]=the slope, [1]=the intercept of the
        fitted 1st grade polynomial, and [2,3]=the actual (x,y) vectors
        used for the fit.
        Copyright 2008 by Marco Brucale, Massimo Sandal
        '''
        # Translates the indeces into two vectors containing the x, y data to fit
        plot = self.displayed_plot
        xtofit = plot.corrected_curves[whatset].x[index1:index2]
        ytofit = plot.corrected_curves[whatset].y[index1:index2]

        # Does the actual linear fitting (simple least squares with numpy.polyfit)
        linefit = np.polyfit(xtofit, ytofit, 1)

        return (linefit[0], linefit[1], xtofit, ytofit)



