# Copyright (C) 2009-2010 Allen Chen
#                         Massimo Sandal <devicerandom@gmail.com>
#                         W. Trevor King <wking@drexel.edu>
#
# This file is part of Hooke.
#
# Hooke is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Hooke is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General
# Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with Hooke.  If not, see
# <http://www.gnu.org/licenses/>.

"""Driver for mcs fluorescence files.
"""

import os.path

import lib.curve
import lib.driver
import lib.plot
import struct

class mcsDriver(lib.driver.Driver):

    def __init__(self, filename):
        '''
        Open the RED (A) ones; the BLUE (D) mirror ones will be automatically opened
        '''
        #obtain name of blue files
        othername=filename
        if othername[-8]=='a': #fixme: how to make it general? (maybe should not be in driverspace but in environment...)
            oth=list(othername)
            oth[-8]='d'
            othername=''.join(oth)
        self.filename=filename
        self.othername=othername

        #print self.filename, self.othername

        self.filedata=open(filename,'rb')
        self.reddata=self.filedata.read()
        self.filedata.close()

        self.filebluedata=open(othername,'rb') #open also the blue ones
        self.bluedata=self.filebluedata.read()
        self.filebluedata.close()

        self.filetype = 'mcs'
        self.experiment = 'smfluo'

    def close_all(self):
        self.filedata.close()
        self.filebluedata.close()

    def default_plots(self):
        #TODO: rename blue and red data to something more appropriate if possible
        red_data=self.read_file(self.reddata)
        blue_data=self.read_file(self.bluedata)
        blue_data=[-1*float(item) for item in blue_data] #visualize blue as "mirror" of red

        extension = lib.curve.Curve()
        retraction = lib.curve.Curve()

        extension.color = 'red'
        extension.label = 'extension'
        extension.style = 'plot'
        extension.title = 'Force curve'
        #FIXME: if there's an header saying something about the time count, should be used
        #TODO: time is not really a unit
        extension.units.x = 'time'
        extension.units.y = 'count'
        extension.x = range(len(red_data))
        extension.y = red_data
        retraction.color = 'blue'
        retraction.label = 'retraction'
        retraction.style = 'plot'
        retraction.title = 'Force curve'
        #FIXME: if there's an header saying something about the time count, should be used
        #TODO: time is not really a unit
        retraction.units.x = 'time'
        retraction.units.y = 'count'
        retraction.x = range(len(blue_data))
        retraction.y = blue_data

        plot = lib.plot.Plot()
        plot.title = os.path.basename(self.filename)
        plot.curves.append(extension)
        plot.curves.append(retraction)

        plot.normalize()
        return plot

    def is_me(self):
        if self.filename[-3:].lower()=='mcs':
            return True
        else:
            return False

    def read_file(self, raw_data):
        real_data=[]
        intervalsperfile=struct.unpack('h', raw_data[10:12])[0] #read in number of intervals in this file
                                                                #this data is contained in bit offset 10-12 in mcs file
        #see http://docs.python.org/library/struct.html#module-struct for additional explanation

        numbytes=len(raw_data) #data is stored in 4-byte chunks, starting with pos 256
        for j in range(0,intervalsperfile): #read in all intervals in file
            temp=raw_data[256+j*4:256+j*4+4]    #data starts at byte offset 256
            real_data.append(struct.unpack('i', temp)[0]) #[0] because it returns a 1-element tuple
        return real_data
