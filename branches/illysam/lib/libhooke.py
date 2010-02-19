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

def delete_empty_lines_from_xmlfile(filename):
    #the following 3 lines are needed to strip newlines.
    #Otherwise, since newlines are XML elements too, the parser would read them
    #(and re-save them, multiplying newlines...)
    aFile=file(filename).read()
    aFile=aFile.split('\n')
    aFile=''.join(aFile)
    return aFile

def get_file_path(filename, folders = []):
    if os.path.dirname(filename) == '' or os.path.isabs(filename) == False:
        path = ''
        for folder in folders:
            path = os.path.join(path, folder)
        filename = os.path.join(hookeDir, path, filename)

    return filename

def coth(z):
    '''
    hyperbolic cotangent
    '''
    return (numpy.exp(2 * z) + 1) / (numpy.exp(2 * z) - 1)

class ClickedPoint(object):
    '''
    this class defines what a clicked point on the curve plot is
    '''
    def __init__(self):

        self.is_marker = None #boolean ; decides if it is a marker
        self.is_line_edge = None #boolean ; decides if it is the edge of a line (unused)
        self.absolute_coords = (None, None) #(float,float) ; the absolute coordinates of the clicked point on the graph
        self.graph_coords = (None, None) #(float,float) ; the coordinates of the plot that are nearest in X to the clicked point
        self.index = None #integer ; the index of the clicked point with respect to the vector selected
        self.dest = None #0 or 1 ; 0=top plot 1=bottom plot

    def find_graph_coords(self, xvector, yvector):
        '''
        Given a clicked point on the plot, finds the nearest point in the dataset (in X) that
        corresponds to the clicked point.
        '''
        dists = []
        for index in scipy.arange(1, len(xvector), 1):
            dists.append(((self.absolute_coords[0] - xvector[index]) ** 2)+((self.absolute_coords[1] - yvector[index]) ** 2))

        self.index=dists.index(min(dists))
        self.graph_coords=(xvector[self.index], yvector[self.index])

#CSV-HELPING FUNCTIONS
def transposed2(lists, defval=0):
    '''
    transposes a list of lists, i.e. from [[a,b,c],[x,y,z]] to [[a,x],[b,y],[c,z]] without losing
    elements
    (by Zoran Isailovski on the Python Cookbook online)
    '''
    if not lists: return []
    return map(lambda *row: [elem or defval for elem in row], *lists)

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
