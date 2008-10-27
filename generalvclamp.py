#!/usr/bin/env python

'''
generalvclamp.py

Plugin regarding general velocity clamp measurements
'''

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


class generalvclampCommands:
    
    def _plug_init(self):
        self.basecurrent=None
        self.basepoints=None
        self.autofile=''
    
    def do_distance(self,args):
        '''
        DISTANCE
        (generalvclamp.py)
        Measure the distance (in nm) between two points.
        For a standard experiment this is the delta X distance.
        For a force clamp experiment this is the delta Y distance (actually becomes
        an alias of zpiezo)
        -----------------
        Syntax: distance
        '''
        if self.current.curve.experiment == 'clamp':
            print 'You wanted to use zpiezo perhaps?'
            return
        else:
            dx,unitx,dy,unity=self._delta(set=1)
            print str(dx*(10**9))+' nm'
            to_dump='distance '+self.current.path+' '+str(dx*(10**9))+' nm'
            self.outlet.push(to_dump)


    def do_force(self,args):
        '''
        FORCE
        (generalvclamp.py)
        Measure the force difference (in pN) between two points
        ---------------
        Syntax: force
        '''    
        if self.current.curve.experiment == 'clamp':
            print 'This command makes no sense for a force clamp experiment.'
            return
        dx,unitx,dy,unity=self._delta(set=1)
        print str(dy*(10**12))+' pN'
        to_dump='force '+self.current.path+' '+str(dy*(10**12))+' pN'
        self.outlet.push(to_dump)
        
        
    def do_forcebase(self,args):
        '''
        FORCEBASE
        (generalvclamp.py)
        Measures the difference in force (in pN) between a point and a baseline
        took as the average between two points.
        
        The baseline is fixed once for a given curve and different force measurements,
        unless the user wants it to be recalculated
        ------------
        Syntax: forcebase [rebase]
                rebase: Forces forcebase to ask again the baseline
                max: Instead of asking for a point to measure, asks for two points and use
                     the maximum peak in between
        '''
        rebase=False #if true=we select rebase
        maxpoint=False #if true=we measure the maximum peak
        
        plot=self._get_displayed_plot()
        whatset=1 #fixme: for all sets
        if 'rebase' in args or (self.basecurrent != self.current.path):
            rebase=True
        if 'max' in args:
            maxpoint=True
               
        if rebase:
            print 'Select baseline'
            self.basepoints=self._measure_N_points(N=2, whatset=whatset)
            self.basecurrent=self.current.path
        
        if maxpoint:
            print 'Select two points'
            points=self._measure_N_points(N=2, whatset=whatset)
            boundpoints=[points[0].index, points[1].index]
            boundpoints.sort()
            try:
                y=min(plot.vectors[whatset][1][boundpoints[0]:boundpoints[1]])
            except ValueError:
                print 'Chosen interval not valid. Try picking it again. Did you pick the same point as begin and end of interval?'
        else:
            print 'Select point to measure'
            points=self._measure_N_points(N=1, whatset=whatset)
            #whatplot=points[0].dest
            y=points[0].graph_coords[1]
        
        #fixme: code duplication
        boundaries=[self.basepoints[0].index, self.basepoints[1].index]
        boundaries.sort()
        to_average=plot.vectors[whatset][1][boundaries[0]:boundaries[1]] #y points to average
        
        avg=np.mean(to_average)
        forcebase=abs(y-avg)
        print str(forcebase*(10**12))+' pN'
        to_dump='forcebase '+self.current.path+' '+str(forcebase*(10**12))+' pN'
        self.outlet.push(to_dump)
        
    
    def plotmanip_flatten(self, plot, current, customvalue=False):
        '''
        Subtracts a polynomial fit to the non-contact part of the curve, as to flatten it.
        the best polynomial fit is chosen among polynomials of degree 1 to n, where n is 
        given by the configuration file or by the customvalue.
        
        customvalue= int (>0) --> starts the function even if config says no (default=False)
        '''
        
        #not a smfs curve...
        if current.curve.experiment != 'smfs':
            return plot
        
        #only one set is present...
        if len(self.plots[0].vectors) != 2:
            return plot
        
        #config is not flatten, and customvalue flag is false too
        if (not self.config['flatten']) and (not customvalue):
            return plot
        
        max_exponent=12
        delta_contact=0
        
        if customvalue:
            max_cycles=customvalue
        else:
            max_cycles=self.config['flatten'] #Using > 1 usually doesn't help and can give artefacts. However, it could be useful too.
        
        contact_index=self.find_contact_point()
        
        valn=[[] for item in range(max_exponent)]
        yrn=[0.0 for item in range(max_exponent)]
        errn=[0.0 for item in range(max_exponent)]
        
        for i in range(int(max_cycles)):
            
            x_ext=plot.vectors[0][0][contact_index+delta_contact:]
            y_ext=plot.vectors[0][1][contact_index+delta_contact:]
            x_ret=plot.vectors[1][0][contact_index+delta_contact:]
            y_ret=plot.vectors[1][1][contact_index+delta_contact:]
            for exponent in range(max_exponent):
                try:
                    valn[exponent]=sp.polyfit(x_ext,y_ext,exponent)
                    yrn[exponent]=sp.polyval(valn[exponent],x_ret)
                    errn[exponent]=sp.sqrt(sum((yrn[exponent]-y_ext)**2)/float(len(y_ext)))
                except Exception,e:
                    print 'Cannot flatten!'
                    print e
                    return plot

            best_exponent=errn.index(min(errn))
            
            #extension
            ycorr_ext=y_ext-yrn[best_exponent]+y_ext[0] #noncontact part
            yjoin_ext=np.array(plot.vectors[0][1][0:contact_index+delta_contact]) #contact part        
            #retraction
            ycorr_ret=y_ret-yrn[best_exponent]+y_ext[0] #noncontact part
            yjoin_ret=np.array(plot.vectors[1][1][0:contact_index+delta_contact]) #contact part
                
            ycorr_ext=np.concatenate((yjoin_ext, ycorr_ext))
            ycorr_ret=np.concatenate((yjoin_ret, ycorr_ret))
        
            plot.vectors[0][1]=list(ycorr_ext)
            plot.vectors[1][1]=list(ycorr_ret)
        
        return plot
            
    #---SLOPE---
    def do_slope(self,args):
        '''
        SLOPE
        (generalvclamp.py)
        Measures the slope of a delimited chunk on the return trace.
        The chunk can be delimited either by two manual clicks, or have
        a fixed width, given as an argument.
        ---------------
        Syntax: slope [width]
                The facultative [width] parameter specifies how many
                points will be considered for the fit. If [width] is
                specified, only one click will be required.
        (c) Marco Brucale, Massimo Sandal 2008
        '''

        # Reads the facultative width argument
        try:
            fitspan=int(args)
        except:
            fitspan=0

        # Decides between the two forms of user input, as per (args)
        if fitspan == 0:
            # Gets the Xs of two clicked points as indexes on the current curve vector
            print 'Click twice to delimit chunk'
            clickedpoints=[]
            points=self._measure_N_points(N=2,whatset=1)
            clickedpoints=[points[0].index,points[1].index]
            clickedpoints.sort()
        else:
            print 'Click once on the leftmost point of the chunk (i.e.usually the peak)'
            clickedpoints=[]
            points=self._measure_N_points(N=1,whatset=1)
            clickedpoints=[points[0].index-fitspan,points[0].index]
        
        # Calls the function linefit_between
        parameters=[0,0,[],[]]
        parameters=self.linefit_between(clickedpoints[0],clickedpoints[1])
          
        # Outputs the relevant slope parameter
        print 'Slope:'
        print str(parameters[0])
        to_dump='slope '+self.current.path+' '+str(parameters[0])
        self.outlet.push(to_dump)
                
        # Makes a vector with the fitted parameters and sends it to the GUI
        xtoplot=parameters[2]
        ytoplot=[]
        x=0
        for x in xtoplot:
            ytoplot.append((x*parameters[0])+parameters[1])
            
        clickvector_x, clickvector_y=[], []
        for item in points:
            clickvector_x.append(item.graph_coords[0])
            clickvector_y.append(item.graph_coords[1])

        lineplot=self._get_displayed_plot(0) #get topmost displayed plot
        
        lineplot.add_set(xtoplot,ytoplot)
        lineplot.add_set(clickvector_x, clickvector_y)
                
        if lineplot.styles==[]:
            lineplot.styles=[None,None,None,'scatter']
        else:
            lineplot.styles+=[None,'scatter']
        
        self._send_plot([lineplot])

    def linefit_between(self,index1,index2):
        '''
        Creates two vectors (xtofit,ytofit) slicing out from the
        current return trace a portion delimited by the two indexes
        given as arguments.
        Then does a least squares linear fit on that slice.
        Finally returns [0]=the slope, [1]=the intercept of the
        fitted 1st grade polynomial, and [2,3]=the actual (x,y) vectors
        used for the fit.
        (c) Marco Brucale, Massimo Sandal 2008
        '''
        # Translates the indexes into two vectors containing the x,y data to fit
        xtofit=self.plots[0].vectors[1][0][index1:index2]
        ytofit=self.plots[0].vectors[1][1][index1:index2]
        
        # Does the actual linear fitting (simple least squares with numpy.polyfit)
        linefit=[]
        linefit=np.polyfit(xtofit,ytofit,1)

        return (linefit[0],linefit[1],xtofit,ytofit)
    
#====================
#AUTOMATIC ANALYSES
#====================
    '''
    def do_autopeak(self,args):
        #FIXME: this function is too long. split it and make it rational.
        #FIXME: also, *generalize fits* to allow FJC and any other model in the future!
        
        def fit_interval_nm(start_index,plot,nm,backwards):
            '''
            '''
            Calculates the number of points to fit, given a fit interval in nm
            start_index: index of point
            plot: plot to use
            backwards: if true, finds a point backwards.
            '''
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
            
        
        pl_value=None
        T=self.config['temperature']
        
        if 'usepoints' in args.split():
            fit_points=int(self.config['auto_fit_points'])
            usepoints=True
        else:
            fit_points=None
            usepoints=False
            
        slope_span=int(self.config['auto_slope_span'])
        delta_force=10
        rebase=False #if true=we select rebase
        
        #Pick up plot
        displayed_plot=self._get_displayed_plot(0)
        
        if self.current.curve.experiment != 'smfs' or len(displayed_plot.vectors) < 2:
            print 'Cannot work on this curve.'
            return
        
        #Look for custom persistent length / custom temperature
        for arg in args.split():
            #look for a persistent length argument.
            if 'pl=' in arg:
                pl_expression=arg.split('=')
                pl_value=float(pl_expression[1]) #actual value
            #look for a T argument. FIXME: spaces are not allowed between 'pl' and value
            if ('t=' in arg[0:2]) or ('T=' in arg[0:2]):
                t_expression=arg.split('=')
                T=float(t_expression[1])
                              
        #Handle contact point arguments
        def pickup_contact_point():
            #macro to pick up the contact point by clicking
            contact_point=self._measure_N_points(N=1, whatset=1)[0]
            contact_point_index=contact_point.index
            self.wlccontact_point=contact_point
            self.wlccontact_index=contact_point.index
            self.wlccurrent=self.current.path
            return contact_point, contact_point_index
                
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
            contact_point=ClickedPoint()
            contact_point.absolute_coords=displayed_plot.vectors[1][0][cindex], displayed_plot.vectors[1][1][cindex]
            contact_point.find_graph_coords(displayed_plot.vectors[1][0], displayed_plot.vectors[1][1])
            contact_point.is_marker=True
        
        
        #Find peaks.
        defplot=self.current.curve.default_plots()[0]
        flatten=self._find_plotmanip('flatten') #Extract flatten plotmanip
        defplot=flatten(defplot, self.current, customvalue=1) #Flatten curve before feeding it to has_peaks
        peak_location,peak_size=self.has_peaks(defplot, self.convfilt_config['mindeviation'])
        
        #Create a new plot to send
        fitplot=copy.deepcopy(displayed_plot)
        
        #Pick up force baseline
        whatset=1 #fixme: for all sets
        if 'rebase' in args or (self.basecurrent != self.current.path):
            rebase=True               
        if rebase:
            clicks=self.config['baseline_clicks']
            if clicks==0:
                self.basepoints=[]
                self.basepoints.append(ClickedPoint())
                self.basepoints.append(ClickedPoint())
                self.basepoints[0].index=peak_location[-1]+fit_interval_nm(peak_location[-1], displayed_plot, self.config['auto_right_baseline'],False)
                self.basepoints[1].index=self.basepoints[0].index+fit_interval_nm(self.basepoints[0].index, displayed_plot, self.config['auto_left_baseline'],False)
                for point in self.basepoints:
                    #for graphing etc. purposes, fill-in with coordinates
                    point.absolute_coords=displayed_plot.vectors[1][0][point.index], displayed_plot.vectors[1][1][point.index]
                    point.find_graph_coords(displayed_plot.vectors[1][0], displayed_plot.vectors[1][1])
            elif clicks>0:
                print 'Select baseline'
                if clicks==1:
                    self.basepoints=self._measure_N_points(N=1, whatset=whatset)
                    self.basepoints.append(ClickedPoint())
                    self.basepoints[1].index=self.basepoints[0].index+fit_interval_nm(self.basepoints[0].index, displayed_plot, self.config['auto_left_baseline'], False)
                    #for graphing etc. purposes, fill-in with coordinates
                    self.basepoints[1].absolute_coords=displayed_plot.vectors[1][0][self.basepoints[1].index], displayed_plot.vectors[1][1][self.basepoints[1].index]
                    self.basepoints[1].find_graph_coords(displayed_plot.vectors[1][0], displayed_plot.vectors[1][1])
                else:
                    self.basepoints=self._measure_N_points(N=2, whatset=whatset)
            
            self.basecurrent=self.current.path
        
        boundaries=[self.basepoints[0].index, self.basepoints[1].index]
        boundaries.sort()
        to_average=displayed_plot.vectors[1][1][boundaries[0]:boundaries[1]] #y points to average
        avg=np.mean(to_average)
        
        
        #Initialize data vectors
        c_lengths=[]
        p_lengths=[]
        forces=[]
        slopes=[]
        
        
        
        #Cycle between peaks and do analysis.
        for peak in peak_location:
            #Do WLC fits.
            #FIXME: clean wlc fitting, to avoid this clickedpoint hell
            #-create a clicked point for the peak point
            peak_point=ClickedPoint()
            peak_point.absolute_coords=displayed_plot.vectors[1][0][peak], displayed_plot.vectors[1][1][peak]
            peak_point.find_graph_coords(displayed_plot.vectors[1][0], displayed_plot.vectors[1][1])    
            
            if not usepoints:
                fit_points=fit_interval_nm(peak, displayed_plot, self.config['auto_fit_nm'], True)
            
            #-create a clicked point for the other fit point
            other_fit_point=ClickedPoint()
            other_fit_point.absolute_coords=displayed_plot.vectors[1][0][peak-fit_points], displayed_plot.vectors[1][1][peak-fit_points]
            other_fit_point.find_graph_coords(displayed_plot.vectors[1][0], displayed_plot.vectors[1][1])    
            #do the fit
            points=[contact_point, peak_point, other_fit_point]
            
            #Check if we have enough points for a fit. If not, wlc_fit could crash
            if abs(peak_point.index-other_fit_point.index) < 2:
                continue
            
            params, yfit, xfit = self.wlc_fit(points, displayed_plot.vectors[1][0], displayed_plot.vectors[1][1],pl_value,T)
            #save wlc values (nm)
            c_lengths.append(params[0]*(1.0e+9))
            if len(params)==2: #if we did choose 2-value fit
                p_lengths.append(params[1]*(1.0e+9))
            else:
                p_lengths.append(pl_value)
            #Add WLC fit lines to plot
            fitplot.add_set(xfit,yfit)
            
            if len(fitplot.styles)==0:
                fitplot.styles=[]
            else:
                fitplot.styles.append(None)
 
            #Measure forces
            delta_to_measure=displayed_plot.vectors[1][1][peak-delta_force:peak+delta_force]
            y=min(delta_to_measure)
            #save force values (pN)
            forces.append(abs(y-avg)*(1.0e+12))
                
            #Measure slopes
            slope=self.linefit_between(peak-slope_span,peak)[0]
            slopes.append(slope)
        
        #--DEBUG STUFF--
        fitplot.add_set([self.basepoints[0].graph_coords[0],self.basepoints[1].graph_coords[0]],[self.basepoints[0].graph_coords[1],self.basepoints[1].graph_coords[1]]) 
        fitplot.styles.append('scatter')
        
        #Show wlc fits and peak locations
        self._send_plot([fitplot])
        self.do_peaks('')
        
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
        '''