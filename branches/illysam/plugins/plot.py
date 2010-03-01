#!/usr/bin/env python

'''
plot.py

Global settings for plots

Copyright 2010 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

class plotCommands:

    def do_plot(self):
        active_file = self.GetActiveFile()
        for curve in active_file.plot.curves:
            curve.decimals.x = self.GetIntFromConfig('plot', 'x_decimals')
            curve.decimals.y = self.GetIntFromConfig('plot', 'y_decimals')
            curve.legend = self.GetBoolFromConfig('plot', 'legend')
            curve.multiplier.x = self.GetStringFromConfig('plot', 'x_multiplier')
            curve.multiplier.y = self.GetStringFromConfig('plot', 'y_multiplier')

        self.UpdatePlot();
