#!/usr/bin/env python

'''
plot.py

Plot class for Hooke.

Copyright 2010 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

class Invert(object):

    def __init__(self):
        self.x = False
        self.y = False


class Plot(object):

    def __init__(self):
        self.corrected_curves = []
        self.curves = []
        self.invert = Invert()
        self.raw_curves = []
        self.results = {}
        self.title = ''

    def normalize(self):
        '''
        Trims the vector lengths as to be equal in a plot.
        '''
        lengths = []
        for curve in self.curves:
            lengths.append(len(curve.x))
            lengths.append(len(curve.y))
            if min(lengths) != max(lengths):
                curve.x = curve.x[0:min(lengths)]
                curve.y = curve.y[0:min(lengths)]
