#!/usr/bin/env python

'''
prettyformat.py

Simple Python function to format values with nice prefixes
Version 1.0.1

History
2009 07 16: added negative number support
            added decimal-formatted output

Copyright 2009 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

import math
from numpy import isnan

def pretty_format(fValue, sUnit='', iDecimals=-1, iMultiplier=1, bLeadingSpaces=False):
    if fValue == 0:
        return '0'
    if isnan(fValue):
        return 'NaN'

    iLeadingSpaces = 0
    if bLeadingSpaces:
        iLeadingSpaces = 5
    if iMultiplier == 1:
        iMultiplier=get_multiplier(fValue)
    sUnitString = ''
    if sUnit != '':
        sUnitString = ' ' + get_prefix(iMultiplier) + sUnit
    if iDecimals >= 0:
        formatString = '% ' + repr(iLeadingSpaces + iDecimals) + '.' + repr(iDecimals) + 'f'
        return formatString % (fValue / iMultiplier) + sUnitString
    else:
        return str(fValue / iMultiplier) + sUnitString
    return str(fValue / iMultiplier) + ' ' + get_prefix(fValue / iMultiplier) + sUnit

def get_multiplier(fValue):
    return pow(10, get_power(fValue))

def get_power(fValue):
    if fValue != 0 and not isnan(fValue):
        #get the log10 from fValue (make sure the value is not negative)
        dHelp = math.floor(math.log10(math.fabs(fValue)))
        #reduce the log10 to a multiple of 3 and return it
        return dHelp-(dHelp % 3)
    else:
        return 0

def get_prefix(fValue):
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
    if fValue != 0 and not isnan(fValue):
        #get the log10 from fValue
        dHelp = math.floor(math.log10(math.fabs(fValue)))
    else:
        dHelp = 0
    #reduce the log10 to a multiple of 3 and create the return string
    return prefix.get(dHelp - (dHelp % 3))()

'''
dTestValue=-2.4115665714484597e-008
print 'Value: '+str(dTestValue)+')'
print 'pretty_format example (value, unit)'
print pretty_format(dTestValue, 'N')
print'-----------------------'
print 'pretty_format example (value, unit, decimals)'
print pretty_format(dTestValue, 'N', 3)
print'-----------------------'
print 'pretty_format example (value, unit, decimals, multiplier)'
print pretty_format(dTestValue, 'N', 5, 0.000001)
print'-----------------------'
print 'pretty_format example (value, unit, decimals, multiplier, leading spaces)'
print pretty_format(0.0166276297705, 'N', 3, 0.001, True)
print pretty_format(0.00750520813323, 'N', 3, 0.001, True)
print pretty_format(0.0136453282825, 'N', 3, 0.001, True)
'''
'''
#example use autoFormatValue
dTestValue=0.00000000567
print 'autoFormatValue example ('+str(dTestValue)+')'
print autoFormatValue(dTestValue, 'N')
#outputs 5.67 nN
'''
'''
#example use of decimalFormatValue(fValue, iDecimals, sUnit):
dTestValue=-2.4115665714484597e-008
iDecimals=3
print 'decimalFormatValue example ('+str(dTestValue)+')'
print decimalFormatValue(dTestValue, iDecimals, 'N')
#outputs -24.116 nN
#change iDecimals to see the effect
'''
'''
#example use formatValue
dTestValue=0.000000000567
print 'formatValue example ('+str(dTestValue)+')'
#find the (common) multiplier
iMultiplier=get_multiplier(dTestValue)
#use the multiplier and a unit to format the value
print formatValue(dTestValue, iMultiplier, 'N')
#outputs 567.0 pN
'''
'''
#to output a scale:
#choose any value on the axis and find the multiplier and prefix for it
#use those to format the rest of the scale
#as values can span several orders of magnitude, you have to decide what units to use

#tuple of values:
scaleValues=0.000000000985, 0.000000001000, 0.000000001015
#use this element (change to 1 or 2 to see the effect on the scale and label)
iIndex=0
#get the multiplier from the value at iIndex
iMultiplier=get_multiplier(scaleValues[iIndex])
print '\nScale example'
iDecimals=3
#print the scale
for aValue in scaleValues: print decimalFormat(aValue/iMultiplier, iDecimals),
#print the scale label using the value at iIndex
print '\n'+get_prefix(scaleValues[iIndex])+'N'
'''