#!/usr/bin/env python

'''
hemingclamp.py

Library for interpreting Hemingway force spectroscopy files.

Copyright 2008 by Massimo Sandal, Marco Brucale (University of Bologna, Italy)
with modifications by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

__version__='2007_02_15_devel'

__changelog__='''
2010_01_22: initial release for Hooke GUI
2007_02_15: fixed time counter with my counter
2007_02_07: initial implementation
'''

import copy
import os.path
import string

import lib.curve
import lib.driver
import lib.plot

class DataChunk(list):
    #TODO: something similar is also used in jpk.py
    #potential for OOP/inheritance?
    '''
    Dummy class to provide ext and ret methods to the data list.
    In this case ext and self can be equal.
    '''

    def ext(self):
        return self

    def ret(self):
        return self

class hemingclampDriver(lib.driver.Driver):

    def __init__(self, filename):

        self.filedata = open(filename,'r')
        self.data = self.filedata.readlines()[6:]
        self.filedata.close()

        self.filetype = 'hemingclamp'
        self.experiment = 'clamp'

        self.filename=filename

    def __del__(self):
        self.filedata.close()

    def _getdata_all(self):
        time = []
        phase = []
        zpiezo = []
        defl = []
        imposed = []
        trim_indexes = []
        trim_counter = 0.0

        for i in self.data:
            temp = string.split(i)
            #time.append(float(temp[0])*(1.0e-3)) # This is managed differently now, since each data point = 1ms: see below
            phase.append(float(temp[1])*(1.0e-7)) # The nonsensical (e-7) multiplier is just there to make phase data nicely plottable along other data
            zpiezo.append(float(temp[2])*(1.0e-9))
            defl.append(float(temp[3])*(1.0e-9))
            imposed.append(float(temp[4])*(1.0e-9))

        for x in range (0,len(phase)):
            if phase[x] != trim_counter:
                trim_indexes.append(x)
                trim_counter = phase[x]

        #we rebuild the time counter assuming 1 point = 1 millisecond
        c=0.0
        for z in zpiezo:
            time.append(c)
            c+=(1.0e-3)

        return time,phase,zpiezo,defl,imposed,trim_indexes

    def close_all(self):
        '''
        Explicitly closes all files
        '''
        self.filedata.close()

    def default_plots(self):
        time=self.time()
        phase=self.phase()
        zpiezo=self.zpiezo()
        deflection=self.deflection()
        imposed=self.imposed()

        #return [main_plot, defl_plot]
        main_extension = lib.curve.Curve()
        main_retraction = lib.curve.Curve()

        #TODO: check 'title' below
        main_extension.color = 'red'
        main_extension.label = 'extension'
        main_extension.style = 'plot'
        main_extension.title = 'Force curve'
        main_extension.units.x = 's'
        main_extension.units.y = 'm'
        main_extension.x = time
        main_extension.y = zpiezo
        main_retraction.color = 'blue'
        main_retraction.label = 'retraction'
        main_retraction.style = 'plot'
        main_retraction.title = 'Force curve'
        main_retraction.units.x = 's'
        #TODO: what is the real unit for y?
        main_retraction.units.y = 'degree'
        main_retraction.x = time
        main_retraction.y = phase

        deflection_extension = copy.deepcopy(main_extension)
        deflection_retraction = copy.deepcopy(main_retraction)
        #TODO: check 'title' below
        deflection_extension.destination.row = 2
        deflection_extension.units.y = 'N'
        deflection_extension.y = deflection
        #TODO: what is the real unit for y?
        deflection_retraction.destination.row = 2
        deflection_retraction.units.y = 'N'
        deflection_retraction.y = imposed

        plot = lib.plot.Plot()
        plot.title = os.path.basename(self.filename)
        plot.curves.append(main_extension)
        plot.curves.append(main_retraction)
        plot.curves.append(deflection_extension)
        plot.curves.append(deflection_retraction)

        plot.normalize()
        return plot

    def deflection(self):
        return DataChunk(self._getdata_all()[3])

    def imposed(self):
        return DataChunk(self._getdata_all()[4])

    def is_me(self):
        '''
        we define our magic heuristic for HemingClamp files
        '''
        myfile=file(self.filename)
        headerlines=myfile.readlines()[0:3]
        myfile.close()
        if headerlines[0][0:10]=='#Hemingway' and headerlines[1][0:19]=='#Experiment: FClamp':
            return True
        else:
            return False

    def phase(self):
        return DataChunk(self._getdata_all()[1])

    def time(self):
        return DataChunk(self._getdata_all()[0])

    def trimindexes(self):
        return DataChunk(self._getdata_all()[5])

    def zpiezo(self):
        return DataChunk(self._getdata_all()[2])
