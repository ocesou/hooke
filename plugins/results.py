#!/usr/bin/env python

'''
results.py

Results commands for Hooke.

Copyright 2010 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

class resultsCommands(object):
    '''
    Results commands to show a certain type of results and to clear results
    '''

    def _plug_init(self):
        pass

    def do_clear_results(self):
        '''
        Deletes all fitting results from the curve.
        '''
        plot = self.GetActivePlot()
        if plot is not None:
            plot.results.clear()
        self.UpdatePlot()


    def do_show_results(self):
        '''
        Select which fitting results should be displayed on the plot.
        '''
        self.UpdatePlot()
