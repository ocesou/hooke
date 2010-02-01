#!/usr/bin/env python

'''
driver.py

Base class for file format drivers.

Copyright 2006 by Massimo Sandal (University of Bologna, Italy).

This program is released under the GNU General Public License version 2.
'''

import lib.plot

class Driver(object):
    '''
    Base class for file format drivers.

    To be overridden
    '''
    def __init__(self):
        self.experiment = ''
        self.filetype = ''

    def is_me(self):
        '''
        This method must read the file and return True if the filetype can be managed by the driver, False if not.
        '''
        return False

    def close_all(self):
        '''
        This method must close all the open files of the driver, explicitly.
        '''
        return None

    def default_plots(self):
        plot = lib.plot.Plot()
        plot.curves.append([0])
        plot.curves.append([0])
        
        return [plot]



