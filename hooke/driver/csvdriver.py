# Copyright (C) 2008-2010 Massimo Sandal <devicerandom@gmail.com>
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

"""Simple driver to read general comma-separated values in Hooke

Columns are read this way:

X1 , Y1 , X2 , Y2 , X3 , Y3 ...

If the number of columns is odd, the last column is ignored.
"""

import csv
import os.path

import lib.curve
import lib.driver
import lib.libhooke
import lib.plot

class csvdriverDriver(lib.driver.Driver):

    def __init__(self, filename):

        self.filedata = open(filename,'r')
        self.data = list(self.filedata)
        self.filedata.close()
        self.filename=filename

    def close_all(self):
        self.filedata.close()

    def default_plots(self):
        rrows=csv.reader(self.data)
        rows=list(rrows) #transform the csv.reader iterator into a normal list
        columns=lib.libhooke.transposed2(rows[1:])

        for index in range(0, len(columns), 2):
            temp_x=columns[index]
            temp_y=columns[index+1]
            #convert to float (the csv gives strings)
            temp_x=[float(item) for item in temp_x]
            temp_y=[float(item) for item in temp_y]

            curve = lib.curve.Curve()

            curve.destination.row = index + 1
            curve.label = 'curve ' + str(index)
            curve.style = 'plot'
            curve.units.x = 'x'
            curve.units.y = 'y'
            curve.x = temp_x
            curve.y = temp_y

            plot = lib.plot.Plot()
            plot.title = os.path.basename(self.filename)
            plot.curves.append(curve)

        #TODO: is normalization helpful or detrimental here?
        #plot.normalize()
        return plot

    def is_me(self):
        myfile=file(self.filename)
        headerline=myfile.readlines()[0]
        myfile.close()

        #using a custom header makes things much easier...
        #(looking for raw CSV data is at strong risk of confusion)
        if headerline[:-1]=='Hooke data':
            return True
        else:
            return False
