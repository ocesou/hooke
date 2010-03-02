#!/usr/bin/env python

'''
curve.py

Curve and related classes for Hooke.

Copyright 2010 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

from  matplotlib.ticker import Formatter
import lib.prettyformat

class Curve(object):

    def __init__(self):
        self.color = 'blue'
        self.decimals = Decimals()
        self.destination = Destination()
        self.label = ''
        self.legend = False
        self.linewidth = 1
        self.prefix = Prefix()
        self.size = 0.5
        self.style = 'plot'
        self.title = ''
        self.units = Units()
        self.visible = True
        self.x = []
        self.y = []


class Data(object):

    def __init__(self):
        self.x = []
        self.y = []


class Decimals(object):

    def __init__(self):
        self.x = 2
        self.y = 2


class Destination(object):

    def __init__(self):
        self.column = 1
        self.row = 1


class Prefix(object):

    def __init__(self):
        self.x = 'n'
        self.y = 'p'


class PrefixFormatter(Formatter):
    '''
    Formatter (matplotlib) class that uses power prefixes.
    '''
    def __init__(self, decimals=2, prefix='n', use_zero=True):
        self.decimals = decimals
        self.prefix = prefix
        self.use_zero = use_zero

    def __call__(self, x, pos=None):
        'Return the format for tick val *x* at position *pos*'
        if self.use_zero:
            if x == 0:
                return '0'
        multiplier = lib.prettyformat.get_exponent(self.prefix)
        decimals_str = '%.' + str(self.decimals) + 'f'
        return decimals_str % (x / (10 ** multiplier))


class Units(object):

    def __init__(self):
        self.x = ''
        self.y = ''
