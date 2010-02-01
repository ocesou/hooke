#!/usr/bin/env python

'''
plotmanipulator.py

Plotmanipulator class for Hooke.

Copyright 2010 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

from string import replace

class Plotmanipulator(object):
    def __init__(self, command=None, method=None):
        #the command (e.g. plotmanip_correct)
        self.command = command
        #the method associated with the command
        self.method = method
        #the suffix of the command (e.g. correct) to retrieve
        #status (active or not from config)
        self.name = command.replace('plotmanip_', '')


