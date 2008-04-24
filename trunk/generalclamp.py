#!/usr/bin/env python

'''
GENERALCLAMP.py

Plugin regarding general force clamp measurements
'''
from libhooke import WX_GOOD, ClickedPoint
import wxversion
wxversion.select(WX_GOOD)
from wx import PostEvent

class generalclampCommands:
    
        
    def do_showdefl(self,args):
        '''
        SHOWDEFL
        Shows the deflection plot for a force clamp curve.
        Use 'close' to close the plot.
        ---
        Syntax: showdefl
        '''
        if self.current.curve.experiment != 'clamp':
            print 'This command makes no sense for a non-force clamp experiment!'
        else:
            self.current.vectors_to_plot(self.config['correct'],self.config['medfilt'],yclamp='defl')
            plot_graph=self.list_of_events['plot_graph']       
            wx.PostEvent(self.frame,plot_graph(current=self.current,xaxes=self.config['xaxes'],yaxes=self.config['yaxes'], destination=1))
    
    def do_time(self,args):
        '''
        TIME
        Measure the time difference (in seconds) between two points
        Implemented only for force clamp
        ----
        Syntax: time
        '''
        if self.current.curve.experiment == 'clamp':
            print 'Click two points.'
            points=self._measure_N_points(N=2)
            time=abs(points[0].graph_coords[0]-points[1].graph_coords[0])
            print str(time)+' s'
        else:
            print 'This command makes no sense for a non-force clamp experiment.'
            
    def do_zpiezo(self,args):
        '''
        ZPIEZO
        Measure the zpiezo difference (in nm) between two points
        Implemented only for force clamp
        ----
        Syntax: zpiezo
        '''
        if self.current.curve.experiment == 'clamp':
            print 'Click two points.'
            points=self._measure_N_points(N=2)
            zpiezo=abs(points[0].graph_coords[1]-points[1].graph_coords[1])
            print str(zpiezo*(10**9))+' nm'
        else:
            print 'This command makes no sense for a non-force clamp experiment.'
            
    def do_defl(self,args):
        '''
        DEFL
        Measure the deflection difference (in nm) between two points
        Implemented only for force clamp
        NOTE: It makes sense only on the time VS defl plot; it is still not masked for the other plot...
        -----
        Syntax: defl
        '''
        if self.current.curve.experiment == 'clamp':
            print 'Click two points.'
            points=self._measure_N_points(N=2)
            defl=abs(points[0].graph_coords[1]-points[1].graph_coords[1])
            print str(defl*(10**12))+' pN'
        else:
            print 'This command makes no sense for a non-force clamp experiment.'
            
    def do_step(self,args):
        '''
        STEP
        
        Measures the length and time duration of a time-Z step
        -----
        Syntax: step
        '''
        if self.current.curve.experiment == 'clamp':
            print 'Click three points in this fashion:'
            print ' (0)-------(1)'
            print '           |'
            print '           |'
            print '           (2)----------'
            points=self._measure_N_points(N=3,whatset=0)
            dz=abs(points[2].graph_coords[1]-points[1].graph_coords[1])*(10e+8)
            dt=abs(points[1].graph_coords[0]-points[0].graph_coords[0])
            print 'dZ: ',dz,' nm'
            print 'dT: ',dt,' s'
            
        else:
            print 'This command makes no sense for a non-force clamp experiment.'