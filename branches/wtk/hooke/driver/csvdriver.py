# Copyright

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

        self.filetype = 'generic'
        self.experiment = ''

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
