#!/usr/bin/env python

'''
libhooke.py

General library of internal objects and utilities for Hooke.

Copyright 2006 by Massimo Sandal (University of Bologna, Italy).
With algorithms contributed by Francesco Musiani (University of Bologna, Italy)
And additions contributed by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

import csv
import os.path
import numpy
import scipy

HOOKE_VERSION=['0.9.0_devel', 'Kenzo', '2010-01-31']
WX_GOOD=['2.6','2.8']
hookeDir=''

#constants for 'special' curves
#this can make it easier to understand what curve we are working on
EXTENSION = 0
RETRACTION = 1

def coth(z):
    '''
    Hyperbolic cotangent.
    '''
    return (numpy.exp(2 * z) + 1) / (numpy.exp(2 * z) - 1)

def delete_empty_lines_from_xmlfile(filename):
    #the following 3 lines are needed to strip newlines.
    #Otherwise, since newlines are XML elements too, the parser would read them
    #(and re-save them, multiplying newlines...)
    aFile=file(filename).read()
    aFile=aFile.split('\n')
    aFile=''.join(aFile)
    return aFile

def fit_interval_nm(start_index, x_vect, nm, backwards):
    '''
    Calculates the number of points to fit, given a fit interval in nm
    start_index: index of point
    plot: plot to use
    backwards: if true, finds a point backwards.
    '''
    c = 0
    i = start_index
    maxlen=len(x_vect)
    while abs(x_vect[i] - x_vect[start_index]) * (10**9) < nm:
        if i == 0 or i == maxlen-1: #we reached boundaries of vector!
            return c
        if backwards:
            i -= 1
        else:
            i += 1
        c += 1
    return c

def get_file_path(filename, folders = []):
    if os.path.dirname(filename) == '' or os.path.isabs(filename) == False:
        path = ''
        for folder in folders:
            path = os.path.join(path, folder)
        filename = os.path.join(hookeDir, path, filename)
    return filename

def remove_extension(filename):
    '''
    Removes the extension from a filename.
    '''
    name, extension = os.path.splitext(filename)
    return name

#CSV-HELPING FUNCTIONS
def csv_write_dictionary(f, data, sorting='COLUMNS'):
    '''
    Writes a CSV file from a dictionary, with keys as first column or row
    Keys are in "random" order.

    Keys should be strings
    Values should be lists or other iterables
    '''
    keys=data.keys()
    values=data.values()
    t_values=transposed2(values)
    writer=csv.writer(f)

    if sorting=='COLUMNS':
        writer.writerow(keys)
        for item in t_values:
            writer.writerow(item)

    if sorting=='ROWS':
        print 'Not implemented!' #FIXME: implement it.

def transposed2(lists, defval=0):
    '''
    transposes a list of lists, i.e. from [[a,b,c],[x,y,z]] to [[a,x],[b,y],[c,z]] without losing
    elements
    (by Zoran Isailovski on the Python Cookbook online)
    '''
    if not lists: return []
    return map(lambda *row: [elem or defval for elem in row], *lists)

