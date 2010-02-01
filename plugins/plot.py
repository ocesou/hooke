#!/usr/bin/env python

'''
plot.py

Plot commands for Hooke.

Copyright 2010 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

class plotCommands(object):
    '''
    Plot commands to replot the original data with fits (if applicable)
    but without secondary plots (unless they are part of the original data)
    '''

    def _plug_init(self):
        pass

    def do_replot(self):
        self.UpdatePlot()
