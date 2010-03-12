#!/usr/bin/env python

'''
multifit.py

Alberto Gomez-Casado, (c) 2010, University of Twente (The Netherlands)
Licensed under GNU GPL v2
'''

#FIXME clean this, probably some dependencies are not needed

from libhooke import WX_GOOD, ClickedPoint
import wxversion
wxversion.select(WX_GOOD)
from wx import PostEvent
import numpy as np
import scipy as sp
import copy
import os.path
import time
import tempfile
import warnings
warnings.simplefilter('ignore',np.RankWarning)
import Queue

global measure_wlc
global EVT_MEASURE_WLC

global events_from_fit
events_from_fit=Queue.Queue() #GUI ---> CLI COMMUNICATION


class multifitCommands:

    def do_multifit(self,args):
        '''
        MULTIFIT
        (multifit.py)
        Presents curves for manual analysis in a comfortable mouse-only fashion.
        Obtains contour length, persistance length, rupture force and 
        slope - loading rate.
        WLC is shown in red, FJC in blue.
        -------------
        Syntax:
        multifit [pl=value] [kl=value] [t=value] [slopew=value] [basew=value]
                [justone]

        pl=[value] and kl=[value]: Use a fixed persistent length (WLC) or Kuhn
                length (FJC) for the fit. If pl is not given, the fit will be 
                a 2-variable fit. 
                DO NOT put spaces between 'pl', '=' and the value.
                The value must be in nanometers. 

        t=[value] : Use a user-defined temperature. The value must be in 
                kelvins; by default it is 293 K.
                DO NOT put spaces between 't', '=' and the value.

        slopew and basew : width in points for slope fitting (points to the
                right of clicked rupture) and base level fitting (points to
                the left of clicked top of rupture), default is 15.
                DO NOT put spaces between 'slopew' or 'basew', '=' value.
                
        justone : performs the fits over current curve instead of iterating

        See fit command help for more information on the options and fit 
        procedures.
        NOTE: centerzero plot modifier should be activated (set centerzero 1).
        '''

		#NOTE duplicates a lot of code from do_fit in fit.py, a call to it could be used directly
		#but it is easier to control the program flow bypassing it
	
        pl_value=None
        kl_value=None
        T=self.config['temperature']
        slopew=15
        basew=15
        justone=False
        
        #FIXME spaces are not allowed between pl or t and value
        for arg in args.split():
            #look for a persistent length argument.
            if 'pl=' in arg:
                pl_expression=arg.split('=')
                pl_value=float(pl_expression[1]) #actual value
            if 'kl=' in arg:
                kl_expression=arg.split('=')
                kl_value=float(kl_expression[1]) #actual value
            #look for a T argument.
            if ('t=' in arg) or ('T=' in arg):
                t_expression=arg.split('=')
                T=float(t_expression[1])
            #look for a basew argument.
            if ('basew=' in arg):
                basew_expression=arg.split('=')
                basew=int(basew_expression[1])
            #look for a slopew argument.
            if ('slopew=' in arg):
                slopew_expression=arg.split('=')
                slopew=int(slopew_expression[1])
            if('justone' in arg):
                justone=True
		
        counter=0
        savecounter=0
        curveindex=0
        
        if not justone:
            print 'What curve no. you would like to start? (enter for ignoring)'
            skip=raw_input()

            if skip.isdigit()==False:
                skip=0
            else:
                skip=int(skip)-1
                print 'Skipping '+str(skip)+ ' curves'
        else:
            skip=0
        #begin presenting curves for analysis
        while curveindex <len(self.current_list):
            if not justone:
                counter+=1
                curve=self.current_list[curveindex]
                if skip>curveindex:
                    curveindex+=1
                    continue	

            #give periodically the opportunity to stop the analysis
                if counter%20==0 and counter>0:
                    print '\nYou checked '+str(counter)+' curves. Do you want to continue?'
                    self.current=curve
                    self.do_plot(0)
                    if self.YNclick():
                        print 'Going on...'
                    else:
                        break
                else:
                    self.current=curve
                    self.do_plot(0)
            else:
                curve=self.current
                self.do_plot(0)
            if not justone:
                print '\nCurve '+str(curveindex+1)+' of '+str(len(self.current_list))       
            print 'Click contact point or left end of the curve to skip'
            #FIXME "left half" is a bit ad hoc, and "set correct 1" makes
            #the 3/4s point not very reliable. 
            #Anyway clicking the end should be safe
            contact_point=self._measure_N_points(N=1, whatset=1)[0]
            contact_point_index=contact_point.index

            retract=self.plots[0].vectors[1][0]
            
            #some fixing for x data that is negative (depends on driver)
            if min(retract)<0:
                cppoint=contact_point.graph_coords[0]+abs(min(retract))
                retract=retract+abs(min(retract))
            else:
                cppoint=contact_point.graph_coords[0]
            threequarters=3*(max(retract)-min(retract))/4
                
  
            if cppoint < threequarters:
                if justone:
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

            fitpoints=[contact_point]+wlcpoints
            #use the currently displayed plot for the fit
            displayed_plot=self._get_displayed_plot()

            #use both fit functions
            try:
                wlcparams, wlcyfit, wlcxfit, wlcfit_errors = self.wlc_fit(fitpoints, displayed_plot.vectors[1][0], displayed_plot.vectors[1][1],pl_value,T, return_errors=True )
                wlcerror=False	
            except:
                print 'WLC fit not possible'
                wlcerror=True

            try:
                fjcparams, fjcyfit, fjcxfit, fjcfit_errors = self.fjc_fit(fitpoints, displayed_plot.vectors[1][0], displayed_plot.vectors[1][1],kl_value,T, return_errors=True )
                fjcerror=False
            except:
                print 'FJC fit not possible'
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
            
            
            print '\nRESULTS'
            print 'WLC contour : '+str(1e9*wlcparams[0])+u' \u00b1 '+str(wlcfit_nm[0])+' nm'
            print 'Per. length : '+str(1e9*wlcparams[1])+u' \u00b1 '+str(wlcfit_nm[1])+' nm'
            print '---'
            print 'FJC contour : '+str(1e9*fjcparams[0])+u' \u00b1 '+str(fjcfit_nm[0])+' nm'
            print 'Kuhn length : '+str(1e9*fjcparams[1])+u' \u00b1 '+str(fjcfit_nm[1])+' nm'    
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
            
            if justone:
                return
            
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
                        f.write(' File ; WLC Cont. length (nm) ; Sigma WLC cl;  Per. Length (nm) ; Sigma pl; FJC Cont. length (nm) ; Sigma FJC cl ; Kuhn length (nm); Sigma kl ; Force (pN) ; Slope (N/m) ; (untested) Loading rate (pN/s)\n')
                        f.close()
        
                if not os.path.exists(self.autofile):
                    f=open(self.autofile,'a+')
                    f.write('Analysis started '+time.asctime()+'\n')
                    f.write('----------------------------------------\n')
                    f.write(' File ; WLC Cont. length (nm) ; Sigma WLC cl;  Per. Length (nm) ; Sigma pl; FJC Cont. length (nm) ; Sigma FJC cl ; Kuhn length (nm); Sigma kl ; Force (pN) ; Slope (N/m) ; (untested) Loading rate (pN/s)\n')
                    f.close()
                
                print 'Saving...'
                savecounter+=1
                f=open(self.autofile,'a+')
                f.write(self.current.path)
                f.write(' ; '+str(1e9*wlcparams[0])+' ; '+str(wlcfit_nm[0])+' ; '+str(1e9*wlcparams[1])+' ; '+str(wlcfit_nm[1])+' ; '+str(1e9*fjcparams[0])+' ; '+str(fjcfit_nm[0])+' ; '+str(1e9*fjcparams[1])+' ; '+str(fjcfit_nm[1])+' ; '+str(1e12*force)+' ; '+ str(slope)+' ; '+str(lrate)+'\n')
                f.close()
            else:
                print '\nWould you like to try again on this same curve?'
                if self.YNclick():
                    continue
            curveindex+=1

        if not justone:
            print 'You saved '+str(savecounter)+' out of '+str(len(self.current_list))+' total curves.'
            
            
            
    def YNclick(self):
        print 'Click any point over y=0 for Yes, under it for No'
        point=self._measure_N_points(N=1,whatset=1)[0]
        value=point.absolute_coords[1]
        if value<0:
            return False
        else:
            return True




