#!/usr/bin/env python

'''
plot.py

Global settings for plots

Copyright 2010 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

class plotCommands:

    def do_preferences(self):
        active_file = self.GetActiveFile()
        for curve in active_file.plot.curves:
            curve.decimals.x = self.GetIntFromConfig('plot', 'preferences', 'x_decimals')
            curve.decimals.y = self.GetIntFromConfig('plot', 'preferences', 'y_decimals')
            curve.legend = self.GetBoolFromConfig('plot', 'preferences', 'legend')
            curve.prefix.x = self.GetStringFromConfig('plot', 'preferences', 'x_prefix')
            curve.prefix.y = self.GetStringFromConfig('plot', 'preferences', 'y_prefix')

        self.UpdatePlot();
