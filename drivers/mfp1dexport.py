#!/usr/bin/env python

'''
mfp1dexport.py

Driver for text-exported MFP-1D files.

Copyright 2009 by Massimo Sandal
with modifications by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

import os.path

import lib.driver
import lib.curve
import lib.plot

__version__='0.0.0.20090923'

class mfp1dexportDriver(lib.driver.Driver):

    def __init__(self, filename):
        '''
        This is a driver to import Asylum Research MFP-1D data.
        Status: experimental
        '''
        self.filename = filename
        self.filedata = open(filename,'rU')
        self.lines = list(self.filedata.readlines())
        self.filedata.close()

        self.filetype = 'mfp1dexport'
        self.experiment = 'smfs'

    def _read_columns(self):

        self.raw_columns=self.lines[39:]

        kline=None
        for line in self.lines:
            if line[:7]=='SpringC':
                kline=line
                break

        kline=kline.split(':')

        #self.k=float(self.raw_header[23][8:])
        self.k=float(kline[1])

        #find retract velocity to calculate loading rate
        retract_velocity = None
        for line in self.lines:
            if line.startswith('RetractVelocity:'):
                retract_velocity = line.split(':')
                self.retract_velocity = float(retract_velocity[1])
                break

        xext=[]
        xret=[]
        yext=[]
        yret=[]
        for line in self.raw_columns:
            spline=line.split()
            xext.append(float(spline[0]))
            yext.append(float(spline[1]))
            xret.append(float(spline[2]))
            yret.append(float(spline[3]))

        return [[xext,yext],[xret,yret]]

    def close_all(self):
        self.filedata.close()

    def is_me(self):
        try:
            self.raw_header = self.lines[0:38]
        except:
            #Not enough lines for a header; not a good file
            return False

        #FIXME: We want a more reasonable header recognition
        if self.raw_header[0].startswith('Wave'):
            return True
        else:
            return False

    def default_plots(self):
        '''
        loads the curve data
        '''
        defl_ext, defl_ret = self.deflection()
        yextforce = [i * self.k for i in defl_ext]
        yretforce = [i * self.k for i in defl_ret]

        extension = lib.curve.Curve()
        retraction = lib.curve.Curve()

        extension.color = 'red'
        extension.label = 'extension'
        extension.style = 'plot'
        extension.title = 'Force curve'
        extension.units.x = 'm'
        extension.units.y = 'N'
        extension.x = self.data[0][0]
        extension.y = yextforce
        retraction.color = 'blue'
        retraction.label = 'retraction'
        retraction.style = 'plot'
        retraction.title = 'Force curve'
        retraction.units.x = 'm'
        retraction.units.y = 'N'
        retraction.x = self.data[1][0]
        retraction.y = yretforce

        plot = lib.plot.Plot()
        plot.title = os.path.basename(self.filename)
        plot.curves.append(extension)
        plot.curves.append(retraction)

        plot.normalize()
        return plot

    def deflection(self):
        self.data = self._read_columns()
        return self.data[0][1], self.data[1][1]
