#!/usr/bin/env python

'''
prettyformat.py

Simple Python function to format values with nice prefixes
Version 1.0.1

History
2009 07 16: added negative number support
            added decimal-formatted output
2010 02 25: renamed variables to a more pythonic style
            added whitespace stripping option to prettyformat()
            added get_multiplier()
            added get_exponent()
            updated examples

Copyright 2009 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

import math
from numpy import isnan

def pretty_format(value, unit='', decimals=-1, multiplier=0, leading_spaces=False):
    if value == 0:
        return '0'
    if isnan(value):
        return 'NaN'

    output_str = ''
    leading_spaces_int = 0
    if leading_spaces:
        leading_spaces_int = 5
    if multiplier == 0:
        multiplier=get_multiplier(value)
    unit_str = ''
    if unit:
        unit_str = ' ' + get_prefix(multiplier) + unit
    if decimals >= 0:
        format_str = '% ' + repr(leading_spaces_int + decimals) + '.' + repr(decimals) + 'f'
        output_str = format_str % (value / multiplier) + unit_str
    else:
        output_str = str(value / multiplier) + unit_str

    if decimals < 0:
        output_str = str(value / multiplier) + ' ' + get_prefix(value / multiplier) + unit

    if leading_spaces_int == 0:
        output_str = output_str.lstrip()

    return output_str

def get_multiplier(value):
    return pow(10, get_power(value))

def get_power(value):
    if value != 0 and not isnan(value):
        #get the log10 from value (make sure the value is not negative)
        value_temp = math.floor(math.log10(math.fabs(value)))
        #reduce the log10 to a multiple of 3 and return it
        return value_temp - (value_temp % 3)
    else:
        return 0

def get_exponent(prefix):
    #set up a dictionary to find the exponent
    exponent = {
        'Y': 24,
        'Z': 21,
        'E': 18,
        'P': 15,
        'T': 12,
        'G': 9,
        'M': 6,
        'k': 3,
        '': 0,
        'm': -3,
        u'\u00B5': -6,
        'n': -9,
        'p': -12,
        'f': -15,
        'a': -18,
        'z': -21,
        'y': -24,
    }
    if exponent.has_key(prefix):
        return exponent[prefix]
    else:
        return 1

def get_prefix(value):
    #set up a dictionary to find the prefix
    prefix = {
        24: lambda: 'Y',
        21: lambda: 'Z',
        18: lambda: 'E',
        15: lambda: 'P',
        12: lambda: 'T',
        9: lambda: 'G',
        6: lambda: 'M',
        3: lambda: 'k',
        0: lambda: '',
        -3: lambda: 'm',
        -6: lambda: u'\u00B5',
        -9: lambda: 'n',
        -12: lambda: 'p',
        -15: lambda: 'f',
        -18: lambda: 'a',
        -21: lambda: 'z',
        -24: lambda: 'y',
    }
    if value != 0 and not isnan(value):
        #get the log10 from value
        value_temp = math.floor(math.log10(math.fabs(value)))
    else:
        value_temp = 0
    #reduce the log10 to a multiple of 3 and create the return string
    return prefix.get(value_temp - (value_temp % 3))()

'''
test_value=-2.4115665714484597e-008
print 'Value: '+str(test_value)+')'
print 'pretty_format example (value, unit)'
print pretty_format(test_value, 'N')
print'-----------------------'
print 'pretty_format example (value, unit, decimals)'
print pretty_format(test_value, 'N', 3)
print'-----------------------'
print 'pretty_format example (value, unit, decimals, multiplier)'
print pretty_format(test_value, 'N', 5, 0.000001)
print'-----------------------'
print 'pretty_format example (value, unit, decimals, multiplier, leading spaces)'
print pretty_format(0.0166276297705, 'N', 3, 0.001, True)
print pretty_format(0.00750520813323, 'N', 3, 0.001, True)
print pretty_format(0.0136453282825, 'N', 3, 0.001, True)
'''
'''
#to output a scale:
#choose any value on the axis and find the multiplier and prefix for it
#use those to format the rest of the scale
#as values can span several orders of magnitude, you have to decide what units to use

#tuple of values:
scale_values=0.000000000985, 0.000000001000, 0.000000001015
#use this element (change to 1 or 2 to see the effect on the scale and label)
index=0
#get the multiplier from the value at index
multiplier=get_multiplier(scale_values[index])
print '\nScale example'
decimals=3
#print the scale
for aValue in scale_values: print decimalFormat(aValue/multiplier, decimals),
#print the scale label using the value at index
print '\n'+get_prefix(scale_values[index])+'N'
'''