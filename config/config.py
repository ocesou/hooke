#!/usr/bin/env python

'''
config.py

Configuration for Hooke.

Copyright 2009 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

from configobj import ConfigObj
from validate import Validator
import os.path

import lib.libhooke as lh

#configuration file
config = ConfigObj()
filename_ini = lh.get_file_path('hooke.ini', ['config'])
#default values for configuration file
filename_configspec = lh.get_file_path('hooke configspec.ini', ['config'])
if os.path.isfile(filename_ini) and os.path.isfile(filename_configspec):
    config = ConfigObj(filename_ini, configspec=filename_configspec)
    validator = Validator()
    if not config.validate(validator):
        #TODO: send message
        print 'Ini file validation failed'
else:
    #TODO: send message
    print 'Ini file not found'
