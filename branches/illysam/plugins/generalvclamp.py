#!/usr/bin/env python

'''
generalvclamp.py

Plugin regarding general velocity clamp measurements

Copyright ???? by ?
with modifications by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

import lib.libhooke as lh
import wxversion
wxversion.select(lh.WX_GOOD)

from copy import deepcopy
import numpy as np
import scipy as sp

import warnings
warnings.simplefilter('ignore', np.RankWarning)

import lib.curve

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
        active_file = self.GetActiveFile()
        plot = self.GetActivePlot()
        if active_file.driver.experiment == 'clamp':
            self.AppendToOutput('You wanted to use zpiezo perhaps?')
            return
        plugin = lib.plugin.Plugin()
        plugin.name = 'generalvclamp'
        plugin.section = 'distance'
        dx, unitx, dy, unity = self._delta(message='Click 2 points to measure the distance.', plugin=plugin)
        #TODO: pretty format
        self.AppendToOutput(str(dx * (10 ** 9)) + ' nm')

    def do_force(self):
        '''
        FORCE
        (generalvclamp.py)
        Measure the force difference (in pN) between two points
        ---------------
        Syntax: force
        '''
        active_file = self.GetActiveFile()
        plot = self.GetActivePlot()
        if active_file.driver.experiment == 'clamp':
            self.AppendToOutput('This command makes no sense for a force clamp experiment.')
            return
        plugin = lib.plugin.Plugin()
        plugin.name = 'generalvclamp'
        plugin.section = 'force'
        dx, unitx, dy, unity = self._delta(message='Click 2 points to measure the force.', plugin=plugin)
        #TODO: pretty format
        self.AppendToOutput(str(dy * (10 ** 12)) + ' pN')

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
        color =  self.GetColorFromConfig('generalvclamp', 'forcebase', 'color')
        maxpoint = self.GetBoolFromConfig('generalvclamp', 'forcebase', 'max')
        rebase = self.GetBoolFromConfig('generalvclamp', 'forcebase', 'rebase')
        show_points = self.GetBoolFromConfig('generalvclamp', 'forcebase', 'show_points')
        size = self.GetIntFromConfig('generalvclamp', 'forcebase', 'size')
        whatset_str = self.GetStringFromConfig('generalvclamp', 'forcebase', 'whatset')
        whatset = 'retraction'
        if whatset_str == 'extension':
            whatset = lh.EXTENSION
        if whatset_str == 'retraction':
            whatset = lh.RETRACTION

        plot = self.GetDisplayedPlotCorrected()

        clicked_points = []

        filename = self.GetActiveFile().name
        if rebase or (self.basecurrent != filename):
            self.basepoints = self._measure_N_points(N=2, message='Click on 2 points to select the baseline.', whatset=whatset)
            self.basecurrent = filename
            clicked_points = self.basepoints

        #TODO: maxpoint does not seem to be picking up the 'real' minimum (at least not with test.hkp/default.000)
        if maxpoint:
            boundpoints = []
            points = self._measure_N_points(N=2, message='Click 2 points to select the range for maximum detection.', whatset=whatset)
            boundpoints = [points[0].index, points[1].index]
            boundpoints.sort()
            clicked_points += points
            try:
                vector_x = plot.curves[whatset].x[boundpoints[0]:boundpoints[1]]
                vector_y = plot.curves[whatset].y[boundpoints[0]:boundpoints[1]]
                y = min(vector_y)
                index = vector_y.index(y)
                clicked_points += [self._clickize(vector_x, vector_y, index)]
            except ValueError:
                self.AppendToOutput('Chosen interval not valid. Try picking it again. Did you pick the same point as begin and end of the interval?')
                return
        else:
            points = self._measure_N_points(N=1, message='Click on the point to measure.', whatset=whatset)
            y = points[0].graph_coords[1]
            clicked_points += [points[0]]

        boundaries = [self.basepoints[0].index, self.basepoints[1].index]
        boundaries.sort()
        to_average = plot.curves[whatset].y[boundaries[0]:boundaries[1]] #y points to average

        avg = np.mean(to_average)
        forcebase = abs(y - avg)

        if show_points:
            curve = plot.curves[whatset]
            for point in clicked_points:
                points = deepcopy(curve)
                points.x = point.graph_coords[0]
                points.y = point.graph_coords[1]

                points.color = color
                points.size = size
                points.style = 'scatter'
                plot.curves.append(points)

        self.UpdatePlot(plot)
        #TODO: pretty format
        self.AppendToOutput(str(forcebase * (10 ** 12)) + ' pN')

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

        fitspan = self.GetIntFromConfig('generalvclamp', 'slope', 'fitspan')
        point_color = self.GetColorFromConfig('generalvclamp', 'slope', 'point_color')
        point_show = self.GetBoolFromConfig('generalvclamp', 'slope', 'point_show')
        point_size = self.GetIntFromConfig('generalvclamp', 'slope', 'point_size')
        slope_color = self.GetColorFromConfig('generalvclamp', 'slope', 'slope_color')
        slope_linewidth = self.GetIntFromConfig('generalvclamp', 'slope', 'slope_linewidth')
        slope_show = self.GetBoolFromConfig('generalvclamp', 'slope', 'slope_show')
        whatset_str = self.GetStringFromConfig('generalvclamp', 'forcebase', 'whatset')
        whatset = 'retraction'
        if whatset_str == 'extension':
            whatset = lh.EXTENSION
        if whatset_str == 'retraction':
            whatset = lh.RETRACTION

        # Decides between the two forms of user input
        #TODO: add an option 'mode' with options 'chunk' and 'point'
        if fitspan == 0:
            # Gets the Xs of two clicked points as indexes on the curve curve vector
            clickedpoints = []
            points = self._measure_N_points(N=2, message='Click 2 points to select the chunk.', whatset=whatset)
            clickedpoints = [points[0].index, points[1].index]
            clickedpoints.sort()
        else:
            clickedpoints = []
            points = self._measure_N_points(N=1, message='Click on the leftmost point of the chunk (i.e.usually the peak).', whatset=whatset)
            clickedpoints = [points[0].index - fitspan, points[0].index]

        # Calls the function linefit_between
        parameters = [0, 0, [], []]
        try:
            parameters = self.linefit_between(clickedpoints[0], clickedpoints[1], whatset=whatset)
        except:
            self.AppendToOutput('Cannot fit. Did you click the same point twice?')
            return

        # Outputs the relevant slope parameter
        #TODO: pretty format with units
        self.AppendToOutput(''.join(['Slope: ', str(parameters[0])]))

        #TODO: add option to keep previous slope
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

        if slope_show:
            #add the slope to the plot
            slope = lib.curve.Curve()
            slope.color = slope_color
            slope.label = 'slope'
            slope.linewidth = slope_linewidth
            slope.style = 'plot'
            slope.x = xtoplot
            slope.y = ytoplot
            plot.curves.append(slope)

        if point_show:
            #add the clicked points to the plot
            points = lib.curve.Curve()
            points.color = point_color
            points.label = 'points'
            points.size = point_size
            points.style = 'scatter'
            points.x = clickvector_x
            points.y = clickvector_y
            plot.curves.append(points)

        self.UpdatePlot(plot)

    def linefit_between(self, index1, index2, whatset=1):
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



