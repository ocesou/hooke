#!/usr/bin/env python

'''
delta.py

Delta class for Hooke to describe differences between 2 points.

Copyright 2010 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

from lib.curve import Units

class Point(object):

    def __init__(self):
        self.x = 0
        self.y = 0

class Delta(object):

    def __init__(self):
        self.point1 = Point()
        self.point2 = Point()
        self.units = Units()

    def get_delta_x(self):
        return self.point1.x - self.point2.x

    def get_delta_y(self):
        return self.point1.y - self.point2.y


