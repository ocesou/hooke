#!/usr/bin/env python

from libhooke import WX_GOOD, ClickedPoint
import wxversion
wxversion.select(WX_GOOD)
from wx import PostEvent
import numpy as np
import scipy as sp
import copy
import os.path
import time

import warnings
warnings.simplefilter('ignore',np.RankWarning)


class autopeakCommands:
    
    def do_autopeak(self,args):
        '''
        AUTOPEAK
        (autopeak.py)
        Automatically performs a number of analyses on the peaks of the given curve.
        Currently it automatically:
        - fits peaks with WLC function
        - measures peak maximum forces with a baseline
        - measures slope in proximity of peak maximum
        Requires flatten plotmanipulator , fit.py plugin , flatfilts.py plugin with convfilt
        
        Syntax:
        autopeak [rebase] [pl=value] [t=value] [noauto] [reclick]
        
        rebase : Re-asks baseline interval
        
        pl=[value] : Use a fixed persistent length for the fit. If pl is not given, 
                     the fit will be a 2-variable  
                     fit. DO NOT put spaces between 'pl', '=' and the value.
                     The value must be in meters. 
                     Scientific notation like 0.35e-9 is fine.
        
        t=[value] : Use a user-defined temperature. The value must be in
                    kelvins; by default it is 293 K.
                    DO NOT put spaces between 't', '=' and the value.
        
        noauto : allows for clicking the contact point by 
                 hand (otherwise it is automatically estimated) the first time.
                 If subsequent measurements are made, the same contact point
                 clicked the first time is used
        
        reclick : redefines by hand the contact point, if noauto has been used before
                  but the user is unsatisfied of the previously choosen contact point.
        
        usepoints : fit interval by number of points instead than by nanometers
        
        When you first issue the command, it will ask for the filename. If you are giving the filename
        of an existing file, autopeak will resume it and append measurements to it. If you are giving
        a new filename, it will create the file and append to it until you close Hooke.
        
        
        Useful variables (to set with SET command):
        ---
        temperature= temperature of the system for wlc fit (in K)
        
        auto_slope_span = number of points on which measure the slope, for slope
        
        auto_fit_nm = number of nm to fit before the peak maximum, for WLC (if usepoints false)
        auto_fit_points = number of points to fit before the peak maximum, for WLC (if usepoints true)
        
        baseline_clicks = 0: automatic baseline
                          1: decide baseline with a single click and length defined in auto_left_baseline
                          2: let user click points of baseline
        auto_left_baseline = length in nm to use as baseline from the right point (if baseline_clicks=0 , 1)
        auto_right_baseline = distance in nm of peak-most baseline point from last peak (if baseline_clicks = 0)
        '''
        
        #MACROS.
        #FIXME: to move outside function
        def fit_interval_nm(start_index,plot,nm,backwards):
            '''
            Calculates the number of points to fit, given a fit interval in nm
            start_index: index of point
            plot: plot to use
            backwards: if true, finds a point backwards.
            '''
            x_vect=plot.vectors[1][0]
            
            c=0
            i=start_index
            start=x_vect[start_index]
            maxlen=len(x_vect)
            while abs(x_vect[i]-x_vect[start_index])*(10**9) < nm:
                if i==0 or i==maxlen-1: #we reached boundaries of vector!
                    return c
                
                if backwards:
                    i-=1
                else:
                    i+=1
                c+=1
            return c
                
        def pickup_contact_point():
            '''macro to pick up the contact point by clicking'''
            contact_point=self._measure_N_points(N=1, whatset=1)[0]
            contact_point_index=contact_point.index
            self.wlccontact_point=contact_point
            self.wlccontact_index=contact_point.index
            self.wlccurrent=self.current.path
            return contact_point, contact_point_index
        
        def find_current_peaks():
            #Find peaks.
            defplot=self.current.curve.default_plots()[0]
            flatten=self._find_plotmanip('flatten') #Extract flatten plotmanip
            defplot=flatten(defplot, self.current, customvalue=1) #Flatten curve before feeding it to has_peaks
            peak_location,peak_size=self.has_peaks(defplot, self.convfilt_config['mindeviation'])
            return peak_location, peak_size
    
        #default fit etc. variables
        pl_value=None
        T=self.config['temperature']
        
        slope_span=int(self.config['auto_slope_span'])
        delta_force=10
        rebase=False #if true=we select rebase
        
        #initialize output data vectors
        c_lengths=[]
        p_lengths=[]
        forces=[]
        slopes=[]
        
        #pick up plot
        displayed_plot=self._get_displayed_plot(0)
        
        #COMMAND LINE PARSING
        #--Using points instead of nm interval
        if 'usepoints' in args.split():
            fit_points=int(self.config['auto_fit_points'])
            usepoints=True
        else:
            fit_points=None
            usepoints=False
        #--Recalculate baseline
        if 'rebase' in args or (self.basecurrent != self.current.path):
            rebase=True 
        
        #--Custom persistent length / custom temperature
        for arg in args.split():
            #look for a persistent length argument.
            if 'pl=' in arg:
                pl_expression=arg.split('=')
                pl_value=float(pl_expression[1]) #actual value
            #look for a T argument. FIXME: spaces are not allowed between 'pl' and value
            if ('t=' in arg[0:2]) or ('T=' in arg[0:2]):
                t_expression=arg.split('=')
                T=float(t_expression[1])                   
        #--Contact point arguments
        if 'reclick' in args.split():
            print 'Click contact point'
            contact_point, contact_point_index = pickup_contact_point()
        elif 'noauto' in args.split():
            if self.wlccontact_index==None or self.wlccurrent != self.current.path:
                print 'Click contact point'
                contact_point , contact_point_index = pickup_contact_point()
            else:
                contact_point=self.wlccontact_point
                contact_point_index=self.wlccontact_index
        else:
            #Automatically find contact point
            cindex=self.find_contact_point()
            contact_point=self._clickize(displayed_plot.vectors[1][0], displayed_plot.vectors[1][1], cindex)
        #--END COMMAND LINE PARSING--
        
        
        peak_location, peak_size = find_current_peaks()
        
        fitplot=copy.deepcopy(displayed_plot)
        
        #Pick up force baseline
        if rebase:
            clicks=self.config['baseline_clicks']
            if clicks==0:
                self.basepoints=[]
                base_index_0=peak_location[-1]+fit_interval_nm(peak_location[-1], displayed_plot, self.config['auto_right_baseline'],False)
                self.basepoints.append(self._clickize(displayed_plot.vectors[1][0],displayed_plot.vectors[1][1],base_index_0))
                base_index_1=self.basepoints[0].index+fit_interval_nm(self.basepoints[0].index, displayed_plot, self.config['auto_left_baseline'],False)
                self.basepoints.append(self._clickize(displayed_plot.vectors[1][0],displayed_plot.vectors[1][1],base_index_1))
            elif clicks>0:
                print 'Select baseline'
                if clicks==1:
                    self.basepoints=self._measure_N_points(N=1, whatset=whatset)
                    base_index_1=self.basepoints[0].index+fit_interval_nm(self.basepoints[0].index, displayed_plot, self.config['auto_left_baseline'], False)
                    self.basepoints.append(self._clickize(displayed_plot.vectors[1][0],displayed_plot.vectors[1][1],base_index_1))
                else:
                    self.basepoints=self._measure_N_points(N=2, whatset=whatset)
            
            self.basecurrent=self.current.path
        
        boundaries=[self.basepoints[0].index, self.basepoints[1].index]
        boundaries.sort()
        to_average=displayed_plot.vectors[1][1][boundaries[0]:boundaries[1]] #y points to average
        avg=np.mean(to_average)
        
        
        for peak in peak_location:
            #WLC FITTING
            #define fit interval
            if not usepoints:
                fit_points=fit_interval_nm(peak, displayed_plot, self.config['auto_fit_nm'], True)
            peak_point=self._clickize(displayed_plot.vectors[1][0],displayed_plot.vectors[1][1],peak)
            other_fit_point=self._clickize(displayed_plot.vectors[1][0],displayed_plot.vectors[1][1],peak-fit_points)
            
            #points for the fit
            points=[contact_point, peak_point, other_fit_point]
            
            if abs(peak_point.index-other_fit_point.index) < 2:
                continue
            
            params, yfit, xfit, fit_errors = self.wlc_fit(points, displayed_plot.vectors[1][0], displayed_plot.vectors[1][1], pl_value, T)
            
                
            #Measure forces
            delta_to_measure=displayed_plot.vectors[1][1][peak-delta_force:peak+delta_force]
            y=min(delta_to_measure)
            #save force values (pN)   
            #Measure slopes
            slope=self.linefit_between(peak-slope_span,peak)[0]
            
            
            #check fitted data and, if right, add peak to the measurement
            #FIXME: code duplication
            if len(params)==1: #if we did choose 1-value fit
                p_lengths.append(pl_value)
                c_lengths.append(params[0]*(1.0e+9))
                forces.append(abs(y-avg)*(1.0e+12))
                slopes.append(slope)     
                #Add WLC fit lines to plot
                fitplot.add_set(xfit,yfit)
                if len(fitplot.styles)==0:
                    fitplot.styles=[]
                else:
                    fitplot.styles.append(None)
            else:
                p_leng=params[1]*(1.0e+9)
                #check if persistent length makes sense. otherwise, discard peak.
                if p_leng>self.config['auto_min_p'] and p_leng<self.config['auto_max_p']:
                    p_lengths.append(p_leng)       
                    c_lengths.append(params[0]*(1.0e+9))
                    forces.append(abs(y-avg)*(1.0e+12))
                    slopes.append(slope)     
                    
                    #Add WLC fit lines to plot
                    fitplot.add_set(xfit,yfit)
                    if len(fitplot.styles)==0:
                        fitplot.styles=[]
                    else:
                        fitplot.styles.append(None)
                else:
                    pass
 
            
        #add basepoints to fitplot
        fitplot.add_set([self.basepoints[0].graph_coords[0],self.basepoints[1].graph_coords[0]],[self.basepoints[0].graph_coords[1],self.basepoints[1].graph_coords[1]]) 
        fitplot.styles.append('scatter')
        
        
        #Show wlc fits and peak locations
        self._send_plot([fitplot])
        #self.do_peaks('')
        
        
        #Ask the user what peaks to ignore from analysis.
        print 'Peaks to ignore (0,1...n from contact point,return to take all)'
        print 'N to discard measurement'
        exclude_raw=raw_input('Input:')
        if exclude_raw=='N':
            print 'Discarded.'
            return
        if not exclude_raw=='':
            exclude=exclude_raw.split(',')
            try:
                exclude=[int(item) for item in exclude]
                for i in exclude:
                    c_lengths[i]=None
                    p_lengths[i]=None
                    forces[i]=None
                    slopes[i]=None
            except:
                 print 'Bad input, taking all...'
        #Clean data vectors from ignored peaks        
        c_lengths=[item for item in c_lengths if item != None]
        p_lengths=[item for item in p_lengths if item != None]
        forces=[item for item in forces if item != None]
        slopes=[item for item in slopes if item != None]    
        print 'contour (nm)',c_lengths
        print 'p (nm)',p_lengths
        print 'forces (pN)',forces
        print 'slopes (N/m)',slopes
        
        #Save file info
        if self.autofile=='':
            self.autofile=raw_input('Autopeak filename? (return to ignore) ')
            if self.autofile=='':
                print 'Not saved.'
                return
        
        if not os.path.exists(self.autofile):
            f=open(self.autofile,'w+')
            f.write('Analysis started '+time.asctime()+'\n')
            f.write('----------------------------------------\n')
            f.write('; Contour length (nm)  ;  Persistence length (nm) ;  Max.Force (pN)  ;  Slope (N/m) \n')
            f.close()
            
        print 'Saving...'
        f=open(self.autofile,'a+')
        
        f.write(self.current.path+'\n')
        for i in range(len(c_lengths)):
            f.write(' ; '+str(c_lengths[i])+' ; '+str(p_lengths[i])+' ; '+str(forces[i])+' ; '+str(slopes[i])+'\n')
            
        f.close()
        self.do_note('autopeak')
        