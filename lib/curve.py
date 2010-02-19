#!/usr/bin/env python

'''
curve.py

Curve and related classes for Hooke.

Copyright 2010 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

class Curve(object):

    def __init__(self):
        self.color = 'blue'
        self.destination = Destination()
        self.label = ''
        self.linewidth = 1
        self.size = 0.5
        self.style = 'plot'
        self.title = ''
        self.units = Units()
        self.visible = True
        self.x = []
        self.y = []


class Destination(object):

    def __init__(self):
        self.column = 1
        self.row = 1


class Units(object):

    def __init__(self):
        self.x = ''
        self.y = ''
