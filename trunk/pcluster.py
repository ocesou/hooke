#!/usr/bin/env python

from mdp import pca
from libhooke import WX_GOOD, ClickedPoint
import wxversion
wxversion.select(WX_GOOD)
from wx import PostEvent
import numpy as np
import scipy as sp
import copy
import os.path
import time
import libhookecurve as lhc

import warnings
warnings.simplefilter('ignore',np.RankWarning)


class pclusterCommands:
    
    def _plug_init(self):
        self.pca_paths=[]
        self.pca_myArray=None
        self.clustplot=None

    def do_pcluster(self,args):
        '''
        pCLUSTER
        (pcluster.py)
        Automatically measures peaks and extracts informations for further clustering
        (c)Paolo Pancaldi, Massimo Sandal 2009
        '''
        #--Custom persistent length
        pl_value=None
        for arg in args.split():
            #look for a persistent length argument.
            if 'pl=' in arg:
                pl_expression=arg.split('=')
                pl_value=float(pl_expression[1]) #actual value
            else:
                pl_value=None
                
        #configuration variables
        min_npks = self.convfilt_config['minpeaks']
        min_deviation = self.convfilt_config['mindeviation']
        
        pclust_filename=raw_input('Automeasure filename? ')
        realclust_filename=raw_input('Coordinates filename? ')
        
        f=open(pclust_filename,'w+')
        f.write('Analysis started '+time.asctime()+'\n')
        f.write('----------------------------------------\n')
        f.write('; Contour length (nm)  ;  Persistence length (nm) ;  Max.Force (pN)  ;  Slope (N/m) ;  Sigma contour (nm) ; Sigma persistence (nm)\n')
        f.close()
        
        f=open(realclust_filename,'w+')
        f.write('Analysis started '+time.asctime()+'\n')
        f.write('----------------------------------------\n')
        f.write('; Peak number ; Mean delta (nm)  ;  Median delta (nm) ;  Mean force (pN)  ;  Median force (pN) ; First peak length (nm) ; Last peak length (nm) ; Max force (pN) ; Min force (pN) ; Max delta (nm) ; Min delta (nm)\n')
        f.close()
        # ------ FUNCTION ------
        def fit_interval_nm(start_index,plot,nm,backwards):
            '''
            Calculates the number of points to fit, given a fit interval in nm
            start_index: index of point
            plot: plot to use
            backwards: if true, finds a point backwards.
            '''
            whatset=1 #FIXME: should be decidable
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

        def plot_informations(itplot,pl_value):
            '''
            OUR VARIABLES
            contact_point.absolute_coords		(2.4584142802103689e-007, -6.9647135616234017e-009)
            peak_point.absolute_coords			(3.6047748250571423e-008, -7.7142802788854212e-009)
            other_fit_point.absolute_coords	(4.1666139243838867e-008, -7.3759393477579707e-009)
            peak_location										[510, 610, 703, 810, 915, 1103]
            peak_size												[-1.2729111505202212e-009, -9.1632775347399312e-010, -8.1707438353929907e-010, -8.0335812578148904e-010, -8.7483955226387558e-010, -3.6269619757067322e-009]
            params													[2.2433999931959462e-007, 3.3230248825175678e-010]
            fit_errors											[6.5817195369767644e-010, 2.4415923138871498e-011]
            '''
            fit_points=int(self.config['auto_fit_points']) # number of points to fit before the peak maximum <50>
            
            T=self.config['temperature'] #temperature of the system in kelvins. By default it is 293 K. <301.0>
            cindex=self.find_contact_point() #Automatically find contact point <158, libhooke.ClickedPoint>
            contact_point=self._clickize(itplot[0].vectors[1][0], itplot[0].vectors[1][1], cindex)
            self.basepoints=[]
            base_index_0=peak_location[-1]+fit_interval_nm(peak_location[-1], itplot[0], self.config['auto_right_baseline'],False)
            self.basepoints.append(self._clickize(itplot[0].vectors[1][0],itplot[0].vectors[1][1],base_index_0))
            base_index_1=self.basepoints[0].index+fit_interval_nm(self.basepoints[0].index, itplot[0], self.config['auto_left_baseline'],False)
            self.basepoints.append(self._clickize(itplot[0].vectors[1][0],itplot[0].vectors[1][1],base_index_1))
            self.basecurrent=self.current.path
            boundaries=[self.basepoints[0].index, self.basepoints[1].index]
            boundaries.sort()
            to_average=itplot[0].vectors[1][1][boundaries[0]:boundaries[1]] #y points to average
            avg=np.mean(to_average)
            return fit_points, contact_point, pl_value, T, cindex, avg

        def features_peaks(itplot, peak, fit_points, contact_point, pl_value, T, cindex, avg):
            '''
            calculate informations for each peak and add they in 
            c_lengths, p_lengths, sigma_c_lengths, sigma_p_lengths, forces, slopes
            '''
            c_leng=None
            p_leng=None
            sigma_c_leng=None
            sigma_p_leng=None
            force=None
            slope=None
            
            delta_force=10
            slope_span=int(self.config['auto_slope_span'])
            
            peak_point=self._clickize(itplot[0].vectors[1][0],itplot[0].vectors[1][1],peak)
            other_fit_point=self._clickize(itplot[0].vectors[1][0],itplot[0].vectors[1][1],peak-fit_points)
            
            points=[contact_point, peak_point, other_fit_point]
            
            params, yfit, xfit, fit_errors = self.wlc_fit(points, itplot[0].vectors[1][0], itplot[0].vectors[1][1], pl_value, T, return_errors=True)
            
            #Measure forces
            delta_to_measure=itplot[0].vectors[1][1][peak-delta_force:peak+delta_force]
            y=min(delta_to_measure)
            #Measure slopes
            slope=self.linefit_between(peak-slope_span,peak)[0]
            #check fitted data and, if right, add peak to the measurement
            if len(params)==1: #if we did choose 1-value fit
                p_leng=pl_value
                c_leng=params[0]*(1.0e+9)
                sigma_p_lengths=0
                sigma_c_lengths=fit_errors[0]*(1.0e+9)
                force = abs(y-avg)*(1.0e+12)
            else: #2-value fit
                p_leng=params[1]*(1.0e+9)
                #check if persistent length makes sense. otherwise, discard peak.
                if p_leng>self.config['auto_min_p'] and p_leng<self.config['auto_max_p']:
                    '''
                    p_lengths.append(p_leng)       
                    c_lengths.append(params[0]*(1.0e+9))
                    sigma_c_lengths.append(fit_errors[0]*(1.0e+9))
                    sigma_p_lengths.append(fit_errors[1]*(1.0e+9))
                    forces.append(abs(y-avg)*(1.0e+12))
                    slopes.append(slope)     
                    '''
                    c_leng=params[0]*(1.0e+9)
                    sigma_c_leng=fit_errors[0]*(1.0e+9)
                    sigma_p_leng=fit_errors[1]*(1.0e+9)
                    force=abs(y-avg)*(1.0e+12)
                else:
                    p_leng=None
                    slope=None
            #return c_lengths, p_lengths, sigma_c_lengths, sigma_p_lengths, forces, slopes
            return  c_leng, p_leng, sigma_c_leng, sigma_p_leng, force, slope


        # ------ PROGRAM -------
        c=0
        for item in self.current_list:
            c+=1
            item.identify(self.drivers)
            itplot=item.curve.default_plots()
            try:
                peak_location,peak_size=self.exec_has_peaks(item,min_deviation)
            except: 
                #We have troubles with exec_has_peaks (bad curve, whatever).
                #Print info and go to next cycle.
                print 'Cannot process ',item.path
                continue 

            if len(peak_location)==0:
                continue

            fit_points, contact_point, pl_value, T, cindex, avg = plot_informations(itplot,pl_value)
            print '\n\nCurve',item.path, 'is',c,'of',len(self.current_list),': found '+str(len(peak_location))+' peaks.'

            #initialize output data vectors
            c_lengths=[]
            p_lengths=[]
            sigma_c_lengths=[]
            sigma_p_lengths=[]
            forces=[]
            slopes=[]

            #loop each peak of my curve
            for peak in peak_location:
                c_leng, p_leng, sigma_c_leng, sigma_p_leng, force, slope = features_peaks(itplot, peak, fit_points, contact_point, pl_value, T, cindex, avg)
                for var, vector in zip([c_leng, p_leng, sigma_c_leng, sigma_p_leng, force, slope],[c_lengths, p_lengths, sigma_c_lengths, sigma_p_lengths, forces, slopes]):
                    if var is not None:
                        vector.append(var)

            #FIXME: We need a dictionary here...
            allvects=[c_lengths, p_lengths, sigma_c_lengths, sigma_p_lengths, forces, slopes]
            for vect in allvects:
                if len(vect)==0:
                    for i in range(len(c_lengths)):
                        vect.append(0)
            
            print 'Measurements for all peaks detected:'
            print 'contour (nm)', c_lengths
            print 'sigma contour (nm)',sigma_c_lengths
            print 'p (nm)',p_lengths
            print 'sigma p (nm)',sigma_p_lengths
            print 'forces (pN)',forces
            print 'slopes (N/m)',slopes
            
            '''
            write automeasure text file
            '''
            print 'Saving automatic measurement...'
            f=open(pclust_filename,'a+')
            f.write(item.path+'\n')
            for i in range(len(c_lengths)):
                f.write(' ; '+str(c_lengths[i])+' ; '+str(p_lengths[i])+' ; '+str(forces[i])+' ; '+str(slopes[i])+' ; '+str(sigma_c_lengths[i])+' ; '+str(sigma_p_lengths[i])+'\n')
            f.close()
            
            '''
            calculate clustering coordinates
            '''
            peak_number=len(c_lengths)
            if peak_number > 1:
                deltas=[]
                for i in range(len(c_lengths)-1):
                    deltas.append(c_lengths[i+1]-c_lengths[i])
                
                delta_mean=np.mean(deltas)
                delta_median=np.median(deltas)
                
                force_mean=np.mean(forces)
                force_median=np.median(forces)
                
                first_peak_cl=c_lengths[0]
                last_peak_cl=c_lengths[-1]
                
                max_force=max(forces[:-1])
                min_force=min(forces)
                
                max_delta=max(deltas)
                min_delta=min(deltas)
                
                delta_stdev=np.std(deltas)
                forces_stdev=np.std(forces[:-1])
                
                print 'Coordinates'
                print 'Peaks',peak_number
                print 'Mean delta',delta_mean
                print 'Median delta',delta_median
                print 'Mean force',force_mean
                print 'Median force',force_median
                print 'First peak',first_peak_cl
                print 'Last peak',last_peak_cl
                print 'Max force',max_force
                print 'Min force',min_force
                print 'Max delta',max_delta
                print 'Min delta',min_delta
                print 'Delta stdev',delta_stdev
                print 'Forces stdev',forces_stdev
                
                '''
                write clustering coordinates
                '''
                f=open(realclust_filename,'a+')
                f.write(item.path+'\n')
                f.write(' ; '+str(peak_number)+' ; '+str(delta_mean)+' ; '+str(delta_median)+' ; '+str(force_mean)+' ; '+str(force_median)+' ; '+str(first_peak_cl)+' ; '+str(last_peak_cl)+ ' ; '+str(max_force)+' ; '
                +str(min_force)+' ; '+str(max_delta)+' ; '+str(min_delta)+ ' ; '+str(delta_stdev)+ ' ; '+str(forces_stdev)+'\n')
                f.close()
            else:
                pass
                
    def do_pca(self,args):
        '''
        PCA
        Automatically measures pca from coordinates filename and shows two interactives plots
        (c)Paolo Pancaldi, Massimo Sandal 2009
        '''
        
        self.pca_myArray = []
        self.pca_paths = {}
        plot_path_temp = ""
        nPlotTot = 0
        nPlotGood = 0
        
        file_name=args
        
        for arg in args.split():
            #look for a file argument.
            if 'f=' in arg:
                file_temp=arg.split('=')[1] #actual coordinates filename
                try:
                    f=open(file_temp)
                    f.close()
                    file_name = file_temp
                    print "Coordinates filename used: " + file_name
                except:
                    print "Impossibile to find " + file_temp + " in current directory"
                    print "Coordinates filename used: " + file_name
            
        f=open(file_name)
        rows = f.readlines()
        for row in rows:
            if row[0]=="/":
                nPlotTot = nPlotTot+1
                #plot_path_temp = row.split("/")[6][:-1]
                plot_path_temp = row
            if row[0]==" " and row.find('nan')==-1:
                row = row[row.index(";",2)+2:].split(" ; ")	# non considero la prima colonna col #picchi
                row = [float(i) for i in row]
                        
                #0:Mean delta, 1:Median delta, 2:Mean force, 3:Median force, 4:First peak length, 5:Last peak length
                        #6:Max delta 7:Min delta 8:Max force 9:Min force 10:Std delta 11:Std force
                if (row[0]<9000 and row[1]<9000 and row[2]<9000 and row[3]<9000 and row[4]<9000 and row[5]<9000):
                    if (row[0]>0 and row[1]>0 and row[2]>0 and row[3]>0 and row[4]>0 and row[5]>0):
                        self.pca_paths[nPlotGood] = plot_path_temp
                        row=[row[1],row[2]]
                        self.pca_myArray.append(row)
                        nPlotGood = nPlotGood+1
                        
        f.close()
        print nPlotGood, "of", nPlotTot
        
        # array convert, calculate PCA, transpose
        self.pca_myArray = np.array(self.pca_myArray,dtype='float')
        print self.pca_myArray.shape
        '''for i in range(len(self.pca_myArray)):
            print i, self.pca_paths[i]
            print i, self.pca_myArray[i]'''
        self.pca_myArray = pca(self.pca_myArray, output_dim=2)	#other way -> y = mdp.nodes.PCANode(output_dim=2)(gigi)
        myArrayTr = np.transpose(self.pca_myArray)
        
        '''for i in range(len(self.pca_myArray)):
            print i, self.pca_paths[i]
            print i, self.pca_myArray[i]'''
        
        # plotting
        X=myArrayTr[0]
        Y=myArrayTr[1]
        clustplot=lhc.PlotObject()
        
        Xsyn=[]
        Ysyn=[]
        Xgb1=[]
        Ygb1=[]
        for index in range(len(self.pca_paths)):
            if 'syn' in self.pca_paths[index]:
                Xsyn.append(X[index])
                Ysyn.append(Y[index])
            else:
                Xgb1.append(X[index])
                Ygb1.append(Y[index])
        
        clustplot.add_set(Xsyn,Ysyn)
        clustplot.add_set(Xgb1,Ygb1)
        clustplot.normalize_vectors()
        clustplot.styles=['scatter', 'scatter']
        clustplot.colors=[None,'red']
        #clustplot.styles=['scatter',None]
        clustplot.destination=1
        self._send_plot([clustplot])
        self.clustplot=clustplot
        
        
    def do_pclick(self,args):        
        
        self._send_plot([self.clustplot]) #quick workaround for BAD problems in the GUI
        print 'Click point'
        point = self._measure_N_points(N=1, whatset=0)
        indice = point[0].index
        plot_file = self.pca_paths[indice]
        dot_coord = self.pca_myArray[indice]
        print "file: " + str(plot_file).rstrip()
        print "id: " + str(indice)
        print "coord: " + str(dot_coord)
        self.do_genlist(str(plot_file))
        #self.do_jump(str(plot_file))