#!/usr/bin/env python

'''
libhemingclamp.py

Library for interpreting Hemingway force spectroscopy files.

Copyright (C) 2006 Massimo Sandal (University of Bologna, Italy) 

This program is released under the GNU General Public License version 2.
'''
__version__='2007_02_15_devel'

__changelog__='''
2007_02_15: fixed time counter with my counter
2007_02_07: Initial implementation
'''
import string
import libhookecurve as lhc 

def hemingclamp_magic(filepath):
    '''
    we define our magic heuristic for HemingClamp files
    '''
    myfile=file(filepath)
    headerlines=myfile.readlines()[0:3]
    if headerlines[0][0:10]=='#Hemingway' and headerlines[1][0:19]=='#Experiment: FClamp':
        return True
    else:
        return False

class DataChunk(list):
    '''Dummy class to provide ext and ret methods to the data list.
    In this case ext and self can be equal.
    '''
    
    def ext(self):
        return self
        
    def ret(self):
        return self

class hemingclampDriver(lhc.Driver):
    
    def __init__(self, filename):
        
        self.filedata = open(filename,'r')
        self.data = self.filedata.readlines()[6:]
        self.filedata.close()
        
        self.filetype = 'hemingclamp'
        self.experiment = 'clamp'
        
        self.filename=filename
       
    def __del__(self):
        self.filedata.close()   
    
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
        
    def _getdata_all(self):
        time = []
        zpiezo = []
        defl = []
                
        for i in self.data:
            temp = string.split(i)
            #time.append(float(temp[0])*(1.0e-3))
            zpiezo.append(float(temp[2])*(1.0e-9))
            defl.append(float(temp[3])*(1.0e-9))
        
        #we rebuild the time counter assuming 1 point = 1 millisecond
        c=0.0
        for z in zpiezo:
            time.append(c)
            c+=(1.0e-3)
            
        return time,zpiezo,defl
        
    def time(self):
        return DataChunk(self._getdata_all()[0])
     
    def zpiezo(self):
        return DataChunk(self._getdata_all()[1])
     
    def deflection(self):
        return DataChunk(self._getdata_all()[2])
    
    def close_all(self):
        '''
        Explicitly closes all files
        '''
        self.filedata.close()
    
    def default_plots(self):
        main_plot=lhc.PlotObject()
        defl_plot=lhc.PlotObject()
        
        time=self.time()
        zpiezo=self.zpiezo()
        deflection=self.deflection()
        
        main_plot.vectors=[[time,zpiezo]]
        main_plot.units=['seconds','meters']
        main_plot.destination=0
        main_plot.title=self.filename
        
        defl_plot.vectors=[[time,deflection]]
        defl_plot.units=['seconds','Newtons']
        defl_plot.destination=1
        
        return [main_plot, defl_plot]
    