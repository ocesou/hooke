#!/usr/bin/env python

'''
GENERALCLAMP.py

Plugin regarding general force clamp measurements
'''
from libhooke import WX_GOOD, ClickedPoint
import wxversion
import libhookecurve as lhc
wxversion.select(WX_GOOD)
from wx import PostEvent

class generalclampCommands:

    def plotmanip_clamp(self, plot, current, customvalue=False):
        '''
        Handles some viewing options for the "force clamp" data format, depending on the state of these configuration variables:
        (1) If self.config['fc_showphase'] != 0, the 'phase' data column (i.e. the 2nd) is shown in the 0th graph (else it isn't)
        (2) If self.config['fc_showimposed'] != 0, the 'imposed deflection' data column (i.e. the 5th) is shown in the 1st graph (else it isn't)
        (3) If self.config['fc_interesting'] == 0, the entire curve is shown in the graphs; if it has a non-zero value N, only phase N is shown.

        NOTE - my implementation of point(3) feels quite awkward - someone smarter than me plz polish that!

        '''
        
        #not a fclamp curve...
        if current.curve.experiment != 'clamp':
            return plot

        if self.config['fc_interesting'] != 0 and plot.destination==0:
            lower = int((self.config['fc_interesting'])-1)
            upper = int((self.config['fc_interesting'])+1)
            trim = current.curve.trimindexes()[lower:upper]
            newtime = []
            newzpiezo = []
            newphase = []
            for x in range(trim[0],trim[1]):
                newtime.append(self.plots[0].vectors[0][0][x])
                newzpiezo.append(self.plots[0].vectors[0][1][x])
                newphase.append(self.plots[0].vectors[1][1][x])
            self.plots[0].vectors[0][0] = newtime
            self.plots[0].vectors[0][1] = newzpiezo
            self.plots[0].vectors[1][0] = newtime
            self.plots[0].vectors[1][1] = newphase

        if self.config['fc_interesting'] != 0 and plot.destination==1:
            lower = int((self.config['fc_interesting'])-1)
            upper = int((self.config['fc_interesting'])+1)
            trim = current.curve.trimindexes()[lower:upper]
            newtime = []
            newdefl = []
            newimposed = []
            for x in range(trim[0],trim[1]):
                newtime.append(self.plots[1].vectors[0][0][x])
                newdefl.append(self.plots[1].vectors[0][1][x])
                newimposed.append(self.plots[1].vectors[1][1][x])
            self.plots[1].vectors[0][0] = newtime
            self.plots[1].vectors[0][1] = newdefl
            self.plots[1].vectors[1][0] = newtime
            self.plots[1].vectors[1][1] = newimposed            
                        
        if self.config['fc_showphase'] == 0 and plot.destination==0:
            self.plots[0].remove_set(1)
            
        if self.config['fc_showimposed'] == 0 and plot.destination==1:
            self.plots[1].remove_set(1)
                         
        return plot
      
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
            time=self._delta(set=0)[0]
            print str(time*1000)+' ms'
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