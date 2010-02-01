#!/usr/bin/env python

'''
plugin.py

ConfigObj plugin class for Hooke.

Copyright 2010 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

class Plugin(object):

    def __init__(self):
        self.key = ''
        self.name = ''
        self.prefix = ''
