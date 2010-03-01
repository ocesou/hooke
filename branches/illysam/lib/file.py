#!/usr/bin/env python

'''
file.py

File class for Hooke.

Copyright 2010 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

import os.path
import lib.plot

class File(object):

    def __init__(self, filename=None, drivers=None):
        self.driver = None
        self.note = ''
        self.plot = lib.plot.Plot()
        if filename is None:
            self.filename = None
            self.name = None
            self.path = None
        else:
            self.filename = filename
            self.path, self.name = os.path.split(filename)

    def identify(self, drivers):
        '''
        identifies a curve and returns the corresponding object
        '''
        for driver in drivers:
            current_driver = driver(self.filename)
            if current_driver.is_me():
                #bring on all the driver, with its load of methods etc.
                #so we can access the whole of it.
                self.plot = current_driver.default_plots()
                self.driver = current_driver
