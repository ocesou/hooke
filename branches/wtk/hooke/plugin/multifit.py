# Copyright (C) 2010 Alberto Gomez-Casado
#                    W. Trevor King <wking@drexel.edu>
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

"""The ``multifit`` module provides :class:`MultifitPlugin` and
several associated :class:`hooke.command.Command`\s for fitting
all sorts of :class:`hooke.experiment.VelocityClamp` parameters.
"""

from ..command import Command, Argument, Failure
from ..playlist import FilePlaylist
from ..plugin import Plugin
from ..plugin.playlist import PlaylistArgument


class MultifitPlugin (Plugin):
    def __init__(self):
        super(MultifitPlugin, self).__init__(name='multifit')
        self._commands = [MultifitCommand(self)]


class MultifitCommand (Command):
    """Presents curves for interactive manual analysis.

    Obtains contour length, persistance length, rupture force and 
    slope (loading rate).

    See :class:`hooke.plugin.fit.FitCommand` help for more information
    on the options and fit procedures.
    """
    #NOTE: centerzero plot modifier should be activated (set centerzero
    #1).
    def __init__(self, plugin):
        super(MultifitCommand, self).__init__(
            name='multifit',
            arguments=[
                PlaylistArgument,
                Argument(name='persistence length', type='float',
                    help="""
Persistence length in meters for WLC fits.  If not given, the fit will
be a 2-variable fit.
""".strip()),
                Argument(name='Kuhn length', type='float',
                    help="""
Kuhn length in meters for eFJC fits.  If not given, the fit will be a
2-variable fit.  The eFJC fit works better with a fixed Kuhn length
(citation?).
""".strip()),
                Argument(name='temperature', type='float', default=293.0,
                    help="""
Temperature in Kelvin.  Defaults to 293 K.
""".strip()),
                Argument(name='slope width', type='int',
                    help="""
Width in points for slope fitting (points leading up to the rupture).
If not given, the routine will prompt for an extra point to fit the
slope.
""".strip()),
                Argument(name='base width', type='int', default=15,
                    help="""
Width in points for slope fitting (points following the rupture?).
""".strip()),
            Argument(name='point slope', type='bool', default=False,
                     help="""
Calculate the slope from the two selected points instead of fitting
data between them.
""".strip()),
            Argument(name='just one', type='bool', default=False,
                     help="""
Perform the fits on the current curve instead of iterating.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        counter=0
        savecounter=0
        curveindex=0
        
        start_curve = params['playlist'].current()
        curve = start_curve
        while True:
            outqueue.put('TODO to end %s execution' % self.name)
            self._fit_curve(hooke, inqueue, outqueue, params, curve)
            if params['just one'] == True:
                break
            params['playlist'].next()
            next_curve = params['playlist'].current()
            if next_curve == start_curve:
                break # loop through playlist complete
            curve = next_curve

    def _fit_curve(self, hooke, inqueue, outqueue, params, curve):
        contact = self._get_point('Mark the contact point of the curve.')
        #hightlights an area dedicated to reject current curve
        sizeret=len(self.plots[0].vectors[1][0])
        noarea=self.plots[0].vectors[1][0][-sizeret/6:-1]                
        noareaplot=copy.deepcopy(self._get_displayed_plot())
        #noise dependent slight shift to improve visibility
        noareaplot.add_set(noarea,np.ones_like(noarea)*5.0*np.std(self.plots[0].vectors[1][1][-sizeret/6:-1]))
        noareaplot.styles+=['scatter']
        noareaplot.colors+=["red"]
        self._send_plot([noareaplot])
        contact_point=self._measure_N_points(N=1, whatset=1)[0]
        contact_point_index=contact_point.index
        noareaplot.remove_set(-1)
        #remove set leaves some styles disturbing the next graph, fixed by doing do_plot
        self.do_plot(0)
        if contact_point_index>5.0/6.0*sizeret:
            if params['just one']:
                break
            curveindex+=1
            continue				
        
        self.wlccontact_point=contact_point
        self.wlccontact_index=contact_point.index
        self.wlccurrent=self.current.path
        
        print 'Now click two points for the fitting area (one should be the rupture point)'
        wlcpoints=self._measure_N_points(N=2,whatset=1)
        print 'And one point of the top of the jump'
        toppoint=self._measure_N_points(N=1,whatset=1)
        slopepoint=ClickedPoint()
        if slopew==None:
            print 'Click a point to calculate slope'
            slopepoint=self._measure_N_points(N=1,whatset=1)
            
        fitpoints=[contact_point]+wlcpoints
        #use the currently displayed plot for the fit
        displayed_plot=self._get_displayed_plot()
        
        #use both fit functions
        try:
            wlcparams, wlcyfit, wlcxfit, wlcfit_errors,wlc_qstd = self.wlc_fit(fitpoints, displayed_plot.vectors[1][0], displayed_plot.vectors[1][1],pl_value,T, return_errors=True )
            wlcerror=False	
        except:
            print 'WLC fit not possible'
            wlcerror=True
            
        try:
            fjcparams, fjcyfit, fjcxfit, fjcfit_errors,fjc_qstd = self.efjc_fit(fitpoints, displayed_plot.vectors[1][0], displayed_plot.vectors[1][1],kl_value,T, return_errors=True )
            fjcerror=False
        except:
            print 'eFJC fit not possible'
            fjcerror=True
                
        #Measure rupture force
        ruptpoint=ClickedPoint()    
        if wlcpoints[0].graph_coords[1]<wlcpoints[1].graph_coords[1]:
            ruptpoint=wlcpoints[0]
        else:
            ruptpoint=wlcpoints[1]
        tpindex=toppoint[0].index
        toplevel=np.average(displayed_plot.vectors[1][1][tpindex:tpindex+basew])
        force=toplevel-ruptpoint.graph_coords[1]					
        
        #Measure the slope - loading rate
            
        if slopew==None:
            if twops:
                xint=ruptpoint.graph_coords[0]-slopepoint[0].graph_coords[0]
                yint=ruptpoint.graph_coords[1]-slopepoint[0].graph_coords[1]
                slope=yint/xint
                slopeplot=self._get_displayed_plot(0) #get topmost displayed plot
                slopeplot.add_set([ruptpoint.graph_coords[0],slopepoint[0].graph_coords[0]],[ruptpoint.graph_coords[1],slopepoint[0].graph_coords[1]])
                if slopeplot.styles==[]:
                    slopeplot.styles=[None,None,'scatter']
                    slopeplot.colors=[None,None,'red']
                else:
                    slopeplot.styles+=['scatter']
                    slopeplot.colors+=['red']
            else:    
                slope=self._slope([ruptpoint]+slopepoint,slopew)
        else:
            slope=self._slope([ruptpoint],slopew)
         
        #plot results (_slope already did)
            
        #now we have the fit, we can plot it
        #add the clicked points in the final PlotObject
        clickvector_x, clickvector_y=[], []
        for item in wlcpoints:
            clickvector_x.append(item.graph_coords[0])
            clickvector_y.append(item.graph_coords[1])
            
        #create a custom PlotObject to gracefully plot the fit along the curves
            
        #first fix those irritating zoom-destroying fits
        lowestpoint=min(displayed_plot.vectors[1][1])
        for i in np.arange(0,len(wlcyfit)):
            if wlcyfit[i] < 1.2*lowestpoint:
                wlcyfit[i]=toplevel    
        for i in np.arange(0,len(fjcyfit)):
            if fjcyfit[i] < 1.2*lowestpoint:
                fjcyfit[i]=toplevel
            
        fitplot=copy.deepcopy(displayed_plot)
        fitplot.add_set(wlcxfit,wlcyfit)
        fitplot.add_set(fjcxfit,fjcyfit) 
        fitplot.add_set(clickvector_x,clickvector_y)

        fitplot.styles+=[None,None,'scatter']
        fitplot.colors+=["red","blue",None]
            
        self._send_plot([fitplot])
        

        #present results of measurement
        if len(wlcparams)==1:
            wlcparams.append(pl_value*1e-9)
        if len(fjcparams)==1:
            fjcparams.append(kl_value*1e-9)
                
        if fjcfit_errors:
            fjcfit_nm=[i*(10**9) for i in fjcfit_errors]
            if len(fjcfit_nm)==1:
                fjcfit_nm.append(0)
        else:
            fjcfit_errors=[0,0]        
        if wlcfit_errors:
            wlcfit_nm=[i*(10**9) for i in wlcfit_errors]
        if len(wlcfit_nm)==1:
            wlcfit_nm.append(0)
        else:
            wlcfit_errors=[0,0]
            
        wlc_fitq=wlc_qstd/np.std(displayed_plot.vectors[1][1][-20:-1])
        fjc_fitq=fjc_qstd/np.std(displayed_plot.vectors[1][1][-20:-1])
            
        print '\nRESULTS'
        print 'WLC contour : '+str(1e9*wlcparams[0])+u' \u00b1 '+str(wlcfit_nm[0])+' nm'
        print 'Per. length : '+str(1e9*wlcparams[1])+u' \u00b1 '+str(wlcfit_nm[1])+' nm'
        print 'Quality :'+str(wlc_fitq)
        print '---'
        print 'eFJC contour : '+str(1e9*fjcparams[0])+u' \u00b1 '+str(fjcfit_nm[0])+' nm'
        print 'Kuhn length (e): '+str(1e9*fjcparams[1])+u' \u00b1 '+str(fjcfit_nm[1])+' nm' 
        print 'Quality :'+str(fjc_fitq)   
        print '---'
        print 'Force : '+str(1e12*force)+' pN'
        print 'Slope : '+str(slope)+' N/m'

        try:
            #FIXME all drivers should provide retract velocity, in SI or homogeneous units    
            lrate=slope*self.current.curve.retract_velocity
            print 'Loading rate (UNTESTED):'+str(lrate)
        except:
            print 'Loading rate : n/a'
            lrate='n/a'
            
        #save accept/discard/repeat
        print '\n\nDo you want to save these?'
        if self.YNclick():
                    
        #Save file info
            if self.autofile=='':
                self.autofile=raw_input('Results filename? (press enter for a random generated name)')
                if self.autofile=='':
                    [osf,name]=tempfile.mkstemp(prefix='analysis-',suffix='.txt',text=True,dir=self.config['hookedir'])
                    print 'saving in '+name
                    self.autofile=name
                    os.close(osf)
                    f=open(self.autofile,'a+')
                    f.write('Analysis started '+time.asctime()+'\n')
                    f.write('----------------------------------------\n')
                    f.write(' File ; WLC Cont. length (nm) ; Sigma WLC cl;  Per. Length (nm) ; Sigma pl ; WLC-Q ; eFJC Cont. length (nm) ; Sigma eFJC cl ; Kuhn length (nm); Sigma kl ; FJC-Q ;Force (pN) ; Slope (N/m) ; (untested) Loading rate (pN/s)\n')
                    f.close()
                    
            if not os.path.exists(self.autofile):
                f=open(self.autofile,'a+')
                f.write('Analysis started '+time.asctime()+'\n')
                f.write('----------------------------------------\n')
                f.write(' File ; WLC Cont. length (nm) ; Sigma WLC cl;  Per. Length (nm) ; Sigma pl; WLC-Q ;eFJC Cont. length (nm) ; Sigma eFJC cl ; Kuhn length (nm); Sigma kl ; FJC-Q ;Force (pN) ; Slope (N/m) ; (untested) Loading rate (pN/s)\n')
                f.close()
                
            print 'Saving...'
            savecounter+=1
            f=open(self.autofile,'a+')
            f.write(self.current.path)
            f.write(' ; '+str(1e9*wlcparams[0])+' ; '+str(wlcfit_nm[0])+' ; '+str(1e9*wlcparams[1])+' ; '+str(wlcfit_nm[1])+' ; '+ str(wlc_fitq)+' ; '+str(1e9*fjcparams[0])+' ; '+str(fjcfit_nm[0])+' ; '+str(1e9*fjcparams[1])+' ; '+str(fjcfit_nm[1])+' ; '+str(fjc_fitq)+' ; '+str(1e12*force)+' ; '+ str(slope)+' ; '+str(lrate)+'\n')
            f.close()
        else:
            print '\nWould you like to try again on this same curve?'
            if self.YNclick():
                continue
        curveindex+=1
