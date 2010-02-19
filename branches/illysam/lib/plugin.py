#!/usr/bin/env python

'''
plugin.py

ConfigObj plugin class for Hooke.

Copyright 2010 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

class Plugin(object):
    '''
    Plugin is a class that is used to facilitate accessing
    configuration parameters in a ConfigObj from different plugins.
    '''

    def __init__(self):
        self.name = ''
        #if the calling plugin uses a prefix, this can be added to the name
        #e.g. autopeak.ini: [[peak_color]]
        #flatfilts.ini [[color]]
        #are both used to set the color of the peak plot (scatter plot)
        #in order to access 'peak_color' rather than 'color', the prefix needs to
        #be set to 'peak_'
        #if the names are identical, set prefix to ''
        self.prefix = ''
        self.section = ''
