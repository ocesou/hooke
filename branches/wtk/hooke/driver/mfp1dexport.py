# Copyright (C) 2009-2010 Massimo Sandal <devicerandom@gmail.com>
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

"""Driver for text-exported MFP 1D files
"""

import os
import os.path

from .. import libhooke as lh
from .. import curve as lhc


__version__='0.0.0.20090923'


class mfp1dexportDriver(lhc.Driver):

    def __init__(self, filename):
        '''
        This is a driver to import Asylum Research MFP 1D data.
        Status: experimental
        '''
        self.filename = filename
        self.filedata = open(filename,'rU')
        self.lines = list(self.filedata.readlines())
        self.filedata.close()

        self.filetype='mfp1dexport'
        self.experiment='smfs'

    def close_all(self):
        self.filedata.close()

    def is_me(self):
        if os.path.isdir(path):
            return False
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

    def deflection(self):
        self.data = self._read_columns()
        return self.data[0][1], self.data[1][1]

    def default_plots(self):
        main_plot = lhc.PlotObject()
        defl_ext,defl_ret = self.deflection()
        yextforce = [i*self.k for i in defl_ext]
        yretforce = [i*self.k for i in defl_ret]
        main_plot.add_set(self.data[0][0], yextforce)
        main_plot.add_set(self.data[1][0], yretforce)
        main_plot.normalize_vectors()
        #main_plot.units = ['Z','force']  #FIXME: if there's an header saying something about the time count, should be used
        main_plot.units = ['m','N']
        main_plot.destination = 0
        main_plot.filename = self.filename
        main_plot.title = os.path.basename(self.filename)
        main_plot.colors = ['red','blue']
        main_plot.style = ['plot','plot']
        return [main_plot]
