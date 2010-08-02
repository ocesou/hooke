# Copyright (C) 2008-2010 Alberto Gomez-Casado
#                         Fabrizio Benedetti
#                         Massimo Sandal <devicerandom@gmail.com>
#                         W. Trevor King <wking@drexel.edu>
#
# This file is part of Hooke.
#
# Hooke is free software: you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# Hooke is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with Hooke.  If not, see
# <http://www.gnu.org/licenses/>.

"""Force spectroscopy curves basic fitting plugin.

Non-standard Dependencies:
procplots.py (plot processing plugin)
"""

from ..libhooke import WX_GOOD, ClickedPoint

import wxversion
wxversion.select(WX_GOOD)
#from wx import PostEvent
#from wx.lib.newevent import NewEvent
import scipy
import scipy.odr
import scipy.stats
import numpy as np
import copy
import Queue

global measure_wlc
global EVT_MEASURE_WLC

#measure_wlc, EVT_MEASURE_WLC = NewEvent()

global events_from_fit
events_from_fit=Queue.Queue() #GUI ---> CLI COMMUNICATION


class fitCommands(object):

    def _plug_init(self):
        self.wlccurrent=None
        self.wlccontact_point=None
        self.wlccontact_index=None
        
    def dist2fit(self):
        '''Calculates the average distance from data to fit, scaled by the standard deviation
        of the free cantilever area (thermal noise)
        '''
                
        
    
    def wlc_fit(self,clicked_points,xvector,yvector, pl_value, T=293, return_errors=False):
        '''
        Worm-like chain model fitting.
        The function is the simple polynomial worm-like chain as proposed by C.Bustamante, J.F.Marko, E.D.Siggia
        and S.Smith (Science. 1994 Sep 9;265(5178):1599-600.)
        '''

        '''
        clicked_points[0] = contact point (calculated or hand-clicked)
        clicked_points[1] and [2] are edges of chunk
        '''

        #STEP 1: Prepare the vectors to apply the fit.
        if pl_value is not None:
            pl_value=pl_value/(10**9)

        #indexes of the selected chunk
        first_index=min(clicked_points[1].index, clicked_points[2].index)
        last_index=max(clicked_points[1].index, clicked_points[2].index)

        #getting the chunk and reverting it
        xchunk,ychunk=xvector[first_index:last_index],yvector[first_index:last_index]
        xchunk.reverse()
        ychunk.reverse()
        #put contact point at zero and flip around the contact point (the fit wants a positive growth for extension and force)
        xchunk_corr_up=[-(x-clicked_points[0].graph_coords[0]) for x in xchunk]
        ychunk_corr_up=[-(y-clicked_points[0].graph_coords[1]) for y in ychunk]

        #make them arrays
        xchunk_corr_up=scipy.array(xchunk_corr_up)
        ychunk_corr_up=scipy.array(ychunk_corr_up)


        #STEP 2: actually do the fit

        #Find furthest point of chunk and add it a bit; the fit must converge
        #from an excess!
        xchunk_high=max(xchunk_corr_up)
        xchunk_high+=(xchunk_high/10)

        #Here are the linearized start parameters for the WLC.
        #[lambd=1/Lo , pii=1/P]

        p0=[(1/xchunk_high),(1/(3.5e-10))]
        p0_plfix=[(1/xchunk_high)]
        '''
        ODR STUFF
        fixme: remove these comments after testing
        '''
        def dist(px,py,linex,liney):
            distancesx=scipy.array([(px-x)**2 for x in linex])
            minindex=np.argmin(distancesx)
            print px, linex[0], linex[-1]
            return (py-liney[minindex])**2
        
        def f_wlc(params,x,T=T):
            '''
            wlc function for ODR fitting
            '''
            lambd,pii=params
            Kb=(1.38065e-23)
            therm=Kb*T
            y=(therm*pii/4.0) * (((1-(x*lambd))**-2) - 1 + (4*x*lambd))
            return y

        def f_wlc_plfix(params,x,pl_value=pl_value,T=T):
            '''
            wlc function for ODR fitting
            '''
            lambd=params
            pii=1/pl_value
            Kb=(1.38065e-23)
            therm=Kb*T
            y=(therm*pii/4.0) * (((1-(x*lambd))**-2) - 1 + (4*x*lambd))
            return y

        #make the ODR fit
        realdata=scipy.odr.RealData(xchunk_corr_up,ychunk_corr_up)
        if pl_value:
            model=scipy.odr.Model(f_wlc_plfix)
            o = scipy.odr.ODR(realdata, model, p0_plfix)
        else:
            model=scipy.odr.Model(f_wlc)
            o = scipy.odr.ODR(realdata, model, p0)

        o.set_job(fit_type=2)
        out=o.run()
        fit_out=[(1/i) for i in out.beta]

        #Calculate fit errors from output standard deviations.
        #We must propagate the error because we fit the *inverse* parameters!
        #The error = (error of the inverse)*(value**2)
        fit_errors=[]
        for sd,value in zip(out.sd_beta, fit_out):
            err_real=sd*(value**2)
            fit_errors.append(err_real)

        def wlc_eval(x,params,pl_value,T):
            '''
            Evaluates the WLC function
            '''
            if not pl_value:
                lambd, pii = params
            else:
                lambd = params

            if pl_value:
                pii=1/pl_value

            Kb=(1.38065e-23) #boltzmann constant
            therm=Kb*T #so we have thermal energy

            return ( (therm*pii/4.0) * (((1-(x*lambd))**-2.0) - 1 + (4.0*x*lambd)) )
        
        
        #STEP 3: plotting the fit

        #obtain domain to plot the fit - from contact point to last_index plus 20 points
        thule_index=last_index+10
        if thule_index > len(xvector): #for rare cases in which we fit something at the END of whole curve.
            thule_index = len(xvector)
        #reverse etc. the domain
        xfit_chunk=xvector[clicked_points[0].index:thule_index]
        xfit_chunk.reverse()
        xfit_chunk_corr_up=[-(x-clicked_points[0].graph_coords[0]) for x in xfit_chunk]
        xfit_chunk_corr_up=scipy.array(xfit_chunk_corr_up)

        #the fitted curve: reflip, re-uncorrect
        yfit=wlc_eval(xfit_chunk_corr_up, out.beta, pl_value,T)
        yfit_down=[-y for y in yfit]
        yfit_corr_down=[y+clicked_points[0].graph_coords[1] for y in yfit_down]
        
        
        #calculate fit quality 
        qsum=0
        yqeval=wlc_eval(xchunk_corr_up,out.beta,pl_value,T)
        #we need to cut the extra from thuleindex
        for qindex in np.arange(0,len(yqeval)):
            qsum+=(yqeval[qindex]-ychunk_corr_up[qindex])**2        
        qstd=np.sqrt(qsum/len(ychunk_corr_up))        
        
    
        if return_errors:
            return fit_out, yfit_corr_down, xfit_chunk, fit_errors, qstd
        else:
            return fit_out, yfit_corr_down, xfit_chunk, None, qstd
    
    def fjc_fit(self,clicked_points,xvector,yvector, pl_value, T=293, return_errors=False):
        '''
        Freely-jointed chain function
        ref: C.Ray and B.B. Akhremitchev; http://www.chem.duke.edu/~boris/research/force_spectroscopy/fit_efjc.pdf
        '''
        '''
        clicked_points[0] is the contact point (calculated or hand-clicked)
        clicked_points[1] and [2] are edges of chunk
        '''

        #STEP 1: Prepare the vectors to apply the fit.
        if pl_value is not None:
            pl_value=pl_value/(10**9)

        #indexes of the selected chunk
        first_index=min(clicked_points[1].index, clicked_points[2].index)
        last_index=max(clicked_points[1].index, clicked_points[2].index)

        #getting the chunk and reverting it
        xchunk,ychunk=xvector[first_index:last_index],yvector[first_index:last_index]
        xchunk.reverse()
        ychunk.reverse()
        #put contact point at zero and flip around the contact point (the fit wants a positive growth for extension and force)
        xchunk_corr_up=[-(x-clicked_points[0].graph_coords[0]) for x in xchunk]
        ychunk_corr_up=[-(y-clicked_points[0].graph_coords[1]) for y in ychunk]


        #make them arrays
        xchunk_corr_up=scipy.array(xchunk_corr_up)
        ychunk_corr_up=scipy.array(ychunk_corr_up)


        #STEP 2: actually do the fit

        #Find furthest point of chunk and add it a bit; the fit must converge
        #from an excess!
        xchunk_high=max(xchunk_corr_up)
        xchunk_high+=(xchunk_high/10)

        #Here are the linearized start parameters for the WLC.
        #[lambd=1/Lo , pii=1/P]

        p0=[(1/xchunk_high),(1/(3.5e-10))]
        p0_plfix=[(1/xchunk_high)]
        '''
        ODR STUFF
        fixme: remove these comments after testing
        '''
        def dist(px,py,linex,liney):
            distancesx=scipy.array([(px-x)**2 for x in linex])
            minindex=np.argmin(distancesx)
            print minindex, px, linex[0], linex[-1]
            return (py-liney[minindex])**2
        
        def coth(z):
            '''
            hyperbolic cotangent
            '''
            return (np.exp(2*z)+1)/(np.exp(2*z)-1)

        def x_fjc(params,f,T=T):
            '''
            fjc function for ODR fitting
            '''
            lambd,pii=params
            Kb=(1.38065e-23)
            therm=Kb*T

            #x=(therm*pii/4.0) * (((1-(x*lambd))**-2) - 1 + (4*x*lambd))
            x=(1/lambd)*(coth(f*(1/pii)/therm) - (therm*pii)/f)
            return x

        def x_fjc_plfix(params,f,pl_value=pl_value,T=T):
            '''
            fjc function for ODR fitting
            '''
            lambd=params
            pii=1/pl_value
            Kb=(1.38065e-23)
            therm=Kb*T
            #y=(therm*pii/4.0) * (((1-(x*lambd))**-2) - 1 + (4*x*lambd))
            x=(1/lambd)*(coth(f*(1/pii)/therm) - (therm*pii)/f)
            return x

        #make the ODR fit
        realdata=scipy.odr.RealData(ychunk_corr_up,xchunk_corr_up)
        if pl_value:
            model=scipy.odr.Model(x_fjc_plfix)
            o = scipy.odr.ODR(realdata, model, p0_plfix)
        else:
            model=scipy.odr.Model(x_fjc)
            o = scipy.odr.ODR(realdata, model, p0)

        o.set_job(fit_type=2)
        out=o.run()
        fit_out=[(1/i) for i in out.beta]

        #Calculate fit errors from output standard deviations.
        #We must propagate the error because we fit the *inverse* parameters!
        #The error = (error of the inverse)*(value**2)
        fit_errors=[]
        for sd,value in zip(out.sd_beta, fit_out):
            err_real=sd*(value**2)
            fit_errors.append(err_real)

        def fjc_eval(y,params,pl_value,T):
            '''
            Evaluates the WLC function
            '''
            if not pl_value:
                lambd, pii = params
            else:
                lambd = params

            if pl_value:
                pii=1/pl_value

            Kb=(1.38065e-23) #boltzmann constant
            therm=Kb*T #so we have thermal energy
            #return ( (therm*pii/4.0) * (((1-(x*lambd))**-2.0) - 1 + (4.0*x*lambd)) )
            return (1/lambd)*(coth(y*(1/pii)/therm) - (therm*pii)/y)



        #STEP 3: plotting the fit
        #obtain domain to plot the fit - from contact point to last_index plus 20 points
        thule_index=last_index+10
        if thule_index > len(xvector): #for rare cases in which we fit something at the END of whole curve.
            thule_index = len(xvector)
        #reverse etc. the domain
        ychunk=yvector[clicked_points[0].index:thule_index]

        if len(ychunk)>0:
            y_evalchunk=np.linspace(min(ychunk),max(ychunk),100)
        else:
            #Empty y-chunk. It happens whenever we set the contact point after a recognized peak,
            #or other buggy situations. Kludge to live with it now...
            ychunk=yvector[:thule_index]
            y_evalchunk=np.linspace(min(ychunk),max(ychunk),100)

        yfit_down=[-y for y in y_evalchunk]
        yfit_corr_down=[y+clicked_points[0].graph_coords[1] for y in yfit_down]
        yfit_corr_down=scipy.array(yfit_corr_down)

        #the fitted curve: reflip, re-uncorrect
        xfit=fjc_eval(yfit_corr_down, out.beta, pl_value,T)
        xfit=list(xfit)
        xfit.reverse()
        xfit_chunk_corr_up=[-(x-clicked_points[0].graph_coords[0]) for x in xfit]

        #xfit_chunk_corr_up=scipy.array(xfit_chunk_corr_up)
        #deltay=yfit_down[0]-yvector[clicked_points[0].index]

        #This is a terrible, terrible kludge to find the point where it should normalize (and from where it should plot)
        xxxdists=[]
        for index in scipy.arange(1,len(xfit_chunk_corr_up),1):
            xxxdists.append((clicked_points[0].graph_coords[0]-xfit_chunk_corr_up[index])**2)
        normalize_index=xxxdists.index(min(xxxdists))
        #End of kludge

        deltay=yfit_down[normalize_index]-clicked_points[0].graph_coords[1]
        yfit_corr_down=[y-deltay for y in yfit_down]
        
        
        #calculate fit quality
        #creates dense y vector
        yqeval=np.linspace(np.min(ychunk_corr_up)/2,np.max(ychunk_corr_up)*2,10*len(ychunk_corr_up))
        #corresponding fitted x
        xqeval=fjc_eval(yqeval,out.beta,pl_value,T)
        
        qsum=0
        for qindex in np.arange(0,len(ychunk_corr_up)):
            qsum+=dist(xchunk_corr_up[qindex],ychunk_corr_up[qindex],xqeval,yqeval)        
        qstd=np.sqrt(qsum/len(ychunk_corr_up))        
        
            
        if return_errors:
            return fit_out, yfit_corr_down[normalize_index+1:], xfit_chunk_corr_up[normalize_index+1:], fit_errors, qstd
        else:
            return fit_out, yfit_corr_down[normalize_index+1:], xfit_chunk_corr_up[normalize_index+1:], None, qstd
    
    def efjc_fit(self,clicked_points,xvector,yvector, pl_value, T=293.0, return_errors=False):
        '''
        Extended Freely-jointed chain function
        ref: F Oesterhelt, M Rief and H E Gaub, New Journal of Physics 1 (1999) 6.1–6.11 
        Please note that 2-parameter fitting (length and kl) usually does not converge, use fixed kl
        '''
        '''
        clicked_points[0] is the contact point (calculated or hand-clicked)
        clicked_points[1] and [2] are edges of chunk
        
        '''
        #Fixed parameters from reference
        Kb=(1.38065e-2) #in pN.nm
        Lp=0.358 #planar, nm
        Lh=0.280 #helical, nm
        Ks=150e3  #pN/nm
        
       
        #STEP 1: Prepare the vectors to apply the fit.
        
        #indexes of the selected chunk
        first_index=min(clicked_points[1].index, clicked_points[2].index)
        last_index=max(clicked_points[1].index, clicked_points[2].index)
        
        #getting the chunk and reverting it
        xchunk,ychunk=xvector[first_index:last_index],yvector[first_index:last_index]
        xchunk.reverse()
        ychunk.reverse()    
        #put contact point at zero and flip around the contact point (the fit wants a positive growth for extension and force)
        xchunk_corr_up=[-(x-clicked_points[0].graph_coords[0]) for x in xchunk]
        ychunk_corr_up=[-(y-clicked_points[0].graph_coords[1]) for y in ychunk]
        
        
        #make them arrays
        xchunk_corr_up=scipy.array(xchunk_corr_up)
        ychunk_corr_up=scipy.array(ychunk_corr_up)
        
        xchunk_corr_up_nm=xchunk_corr_up*1e9
        ychunk_corr_up_pn=ychunk_corr_up*1e12
    
        
        #STEP 2: actually do the fit
    
        #Find furthest point of chunk and add it a bit; the fit must converge
        #from an excess!
        xchunk_high=max(xchunk_corr_up_nm)
        xchunk_high+=(xchunk_high/10.0)
    
        #Here are the linearized start parameters for the WLC.
        #[Ns , pii=1/P]
        #max number of monomers (all helical)for a contour length xchunk_high
        excessNs=xchunk_high/(Lp) 
        p0=[excessNs,(1.0/(0.7))]
        p0_plfix=[(excessNs)]
    
        def dist(px,py,linex,liney):
            distancesx=scipy.array([(px-x)**2 for x in linex])
            minindex=np.argmin(distancesx)
            return (py-liney[minindex])**2
    
        def deltaG(f):
            dG0=12.4242 #3kt in pN.nm
            dL=0.078 #planar-helical
            return dG0-f*dL
        
        def Lfactor(f,T=T):
            Lp=0.358 #planar, nm
            Lh=0.280 #helical, nm
            Kb=(1.38065e-2)
            therm=Kb*T
            dG=deltaG(f)
            
            return Lp/(np.exp(dG/therm)+1)+Lh/(np.exp(-dG/therm)+1)
        
        def coth(z):
            '''
            hyperbolic cotangent
            '''
            return 1.0/np.tanh(z)
        
        def x_efjc(params,f,T=T,Ks=Ks):
            '''
            efjc function for ODR fitting
            '''
            
            Ns=params[0]
            invkl=params[1]
            Kb=(1.38065e-2)
            therm=Kb*T            
            beta=(f/therm)/invkl
                        
            x=Ns*Lfactor(f)*(coth(beta)-1.0/beta)+Ns*f/Ks
            return x
        
        def x_efjc_plfix(params,f,kl_value=pl_value,T=T,Ks=Ks):
            '''
            efjc function for ODR fitting
            '''
            
            Ns=params
            invkl=1.0/kl_value
            Kb=(1.38065e-2)
            therm=Kb*T
            beta=(f/therm)/invkl
            
            x=Ns*Lfactor(f)*(coth(beta)-1.0/beta)+Ns*f/Ks
            return x
        
        #make the ODR fit
        realdata=scipy.odr.RealData(ychunk_corr_up_pn,xchunk_corr_up_nm)
        if pl_value:
            model=scipy.odr.Model(x_efjc_plfix)
            o = scipy.odr.ODR(realdata, model, p0_plfix)
        else:
            print 'WARNING eFJC fit with free pl sometimes does not converge'
            model=scipy.odr.Model(x_efjc)
            o = scipy.odr.ODR(realdata, model, p0)
        
        o.set_job(fit_type=2)
        out=o.run()
    
        
        Ns=out.beta[0]
        Lc=Ns*Lp*1e-9 
        if len(out.beta)>1:
            kfit=1e-9/out.beta[1]
            kfitnm=1/out.beta[1]
        else:
            kfit=1e-9*pl_value
            kfitnm=pl_value
        
        fit_out=[Lc, kfit]
        
        #Calculate fit errors from output standard deviations.
        fit_errors=[]
        fit_errors.append(out.sd_beta[0]*Lp*1e-9)
        if len(out.beta)>1:
            fit_errors.append(1e9*out.sd_beta[1]*kfit**2)
            
  
        
        def efjc_eval(y,params,pl_value,T=T,Lfactor=Lfactor,Ks=Ks):    
            '''
            Evaluates the eFJC function
            '''
            if not pl_value:
                Ns, invkl = params
            else:
                Ns = params
        
            if pl_value:
                invkl=1.0/pl_value
        
            Kb=(1.38065e-2) #boltzmann constant
            therm=Kb*T #so we have thermal energy
            beta=(y/therm)/invkl

            x= Ns*Lfactor(y)*(coth(beta)-1.0/beta)+Ns*y/Ks
            
            return x
            
        #STEP 3: plotting the fit
        #obtain domain to plot the fit - from contact point to last_index plus 20 points
        thule_index=last_index+10
        if thule_index > len(xvector): #for rare cases in which we fit something at the END of whole curve.
            thule_index = len(xvector)
        #reverse etc. the domain
        ychunk=yvector[clicked_points[0].index:thule_index]

        if len(ychunk)>0:
            y_evalchunk=np.linspace(min(ychunk),max(ychunk),100)
        else:
            #Empty y-chunk. It happens whenever we set the contact point after a recognized peak,
            #or other buggy situations. Kludge to live with it now...
            ychunk=yvector[:thule_index]
            y_evalchunk=np.linspace(min(ychunk),max(ychunk),100)
            
        yfit_down=[-y for y in y_evalchunk]
        yfit_corr_down=[y+clicked_points[0].graph_coords[1] for y in yfit_down]
        yfit_corr_down=scipy.array(yfit_corr_down)
        
        #the fitted curve: reflip, re-uncorrect
        xfit=efjc_eval(1e12*yfit_corr_down, out.beta, pl_value,T)*1e-9
        xfit=list(xfit)
        xfit.reverse()
        xfit_chunk_corr_up=[-(x-clicked_points[0].graph_coords[0]) for x in xfit]
        
        #xfit_chunk_corr_up=scipy.array(xfit_chunk_corr_up)
        #deltay=yfit_down[0]-yvector[clicked_points[0].index]
        
        #This is a terrible, terrible kludge to find the point where it should normalize (and from where it should plot)
        xxxdists=[]
        for index in scipy.arange(1,len(xfit_chunk_corr_up),1):
            xxxdists.append((clicked_points[0].graph_coords[0]-xfit_chunk_corr_up[index])**2)           
        normalize_index=xxxdists.index(min(xxxdists))
        #End of kludge
        
        deltay=yfit_down[normalize_index]-clicked_points[0].graph_coords[1]
        yfit_corr_down=[y-deltay for y in yfit_down]
        
        #calculate fit quality
        #creates dense y vector
        yqeval=np.linspace(np.min(ychunk_corr_up_pn)/2,np.max(ychunk_corr_up_pn)*2,10*len(ychunk_corr_up_pn))
        #corresponding fitted x
        xqeval=efjc_eval(yqeval,out.beta,pl_value)
        
        qsum=0
        for qindex in np.arange(0,len(ychunk_corr_up_pn)):
            qsum+=dist(xchunk_corr_up_nm[qindex],ychunk_corr_up_pn[qindex],xqeval,yqeval)        
        qstd=1e-12*np.sqrt(qsum/len(ychunk_corr_up_pn))
            
        if return_errors:
            return fit_out, yfit_corr_down[normalize_index+1:], xfit_chunk_corr_up[normalize_index+1:], fit_errors, qstd
        else:
            return fit_out, yfit_corr_down[normalize_index+1:], xfit_chunk_corr_up[normalize_index+1:], None, qstd
            
    
   
    
    def do_wlc(self,args):
        '''
        WLC
        (fit.py plugin)

        See the fit command
        '''
        self.do_fit(args)

    def do_fjc(self,args):
        '''
        FJC
        (fit.py plugin)

        See the fit command
        '''
        self.do_fit(args)

    def do_fit(self,args):
        '''
        FIT
        (fit.py plugin)
        Fits an entropic elasticity function to a given chunk of the curve.

        First you have to click a contact point.
        Then you have to click the two edges of the data you want to fit.
        
        Fit quality compares the distance to the fit with the thermal noise (a good fit should be close to 1)
        
        The fit function depends on the fit_function variable. You can set it with the command
        "set fit_function wlc" or  "set fit_function fjc" depending on the function you prefer.

        For WLC, the function is the simple polynomial worm-like chain as proposed by
        C.Bustamante, J.F.Marko, E.D.Siggia and S.Smith (Science. 1994
        Sep 9;265(5178):1599-600.)

        For FJC, ref:
        C.Ray and B.B. Akhremitchev; http://www.chem.duke.edu/~boris/research/force_spectroscopy/fit_efjc.pdf
        
        For eFJC, ref:
        F Oesterhelt, M Rief and H E Gaub, New Journal of Physics 1 (1999) 6.1–6.11 (section 4.2)
        NOTE: use fixed pl for better results.

        Arguments:
        pl=[value] : Use a fixed persistent length (WLC) or Kuhn length (FJC) for the fit. If pl is not given,
                     the fit will be a 2-variable
                     fit. DO NOT put spaces between 'pl', '=' and the value.
                     The value must be in nanometers.

        t=[value] : Use a user-defined temperature. The value must be in
                    kelvins; by default it is 293 K.
                    DO NOT put spaces between 't', '=' and the value.

        noauto : allows for clicking the contact point by
                 hand (otherwise it is automatically estimated) the first time.
                 If subsequent measurements are made, the same contact point
                 clicked is used

        reclick : redefines by hand the contact point, if noauto has been used before
                  but the user is unsatisfied of the previously choosen contact point.
        ---------
        Syntax: fit [pl=(value)] [t=value] [noauto]
        '''
        pl_value=None
        T=self.config['temperature']
        for arg in args.split():
            #look for a persistent length argument.
            if 'pl=' in arg:
                pl_expression=arg.split('=')
                pl_value=float(pl_expression[1]) #actual value
            #look for a T argument. FIXME: spaces are not allowed between 'pl' and value
            if ('t=' in arg[0:2]) or ('T=' in arg[0:2]):
                t_expression=arg.split('=')
                T=float(t_expression[1])

        #use the currently displayed plot for the fit
        displayed_plot=self._get_displayed_plot()

        #handle contact point arguments correctly
        if 'reclick' in args.split():
            print 'Click contact point'
            contact_point=self._measure_N_points(N=1, whatset=1)[0]
            contact_point_index=contact_point.index
            self.wlccontact_point=contact_point
            self.wlccontact_index=contact_point.index
            self.wlccurrent=self.current.path
        elif 'noauto' in args.split():
            if self.wlccontact_index==None or self.wlccurrent != self.current.path:
                print 'Click contact point'
                contact_point=self._measure_N_points(N=1, whatset=1)[0]
                contact_point_index=contact_point.index
                self.wlccontact_point=contact_point
                self.wlccontact_index=contact_point.index
                self.wlccurrent=self.current.path
            else:
                contact_point=self.wlccontact_point
                contact_point_index=self.wlccontact_index
        else:
            cindex=self.find_contact_point()
            contact_point=ClickedPoint()
            contact_point.absolute_coords=displayed_plot.vectors[1][0][cindex], displayed_plot.vectors[1][1][cindex]
            contact_point.find_graph_coords(displayed_plot.vectors[1][0], displayed_plot.vectors[1][1])
            contact_point.is_marker=True

        print 'Click edges of chunk'
        points=self._measure_N_points(N=2, whatset=1)
        points=[contact_point]+points
      
        try:
            if self.config['fit_function']=='wlc':
                params, yfit, xfit, fit_errors,qstd = self.wlc_fit(points, displayed_plot.vectors[1][0], displayed_plot.vectors[1][1],pl_value,T, return_errors=True )
                name_of_charlength='Persistent length'
            elif self.config['fit_function']=='fjc':
                params, yfit, xfit, fit_errors,qstd = self.fjc_fit(points, displayed_plot.vectors[1][0], displayed_plot.vectors[1][1],pl_value,T, return_errors=True )
                name_of_charlength='Kuhn length'
            elif self.config['fit_function']=='efjc':
                params, yfit, xfit, fit_errors,qstd = self.efjc_fit(points, displayed_plot.vectors[1][0], displayed_plot.vectors[1][1],pl_value,T, return_errors=True )
                name_of_charlength='Kuhn length (e)'                    
            else:
                print 'No recognized fit function defined!'
                print 'Set your fit function to wlc, fjc or efjc.'
                return

        except:
            print 'Fit not possible. Probably wrong interval -did you click two *different* points?'
            return

        #FIXME: print "Kuhn length" for FJC
        print 'Fit function:',self.config['fit_function']
        print 'Contour length: ',params[0]*(1.0e+9),' nm'
        to_dump='contour '+self.current.path+' '+str(params[0]*(1.0e+9))+' nm'
        self.outlet.push(to_dump)
        if len(params)==2: #if we did choose 2-value fit
            print name_of_charlength+': ',params[1]*(1.0e+9),' nm'
            to_dump='persistent '+self.current.path+' '+str(params[1]*(1.0e+9))+' nm'
            self.outlet.push(to_dump)

        if fit_errors:
            fit_nm=[i*(10**9) for i in fit_errors]
            print 'Standard deviation (contour length)', fit_nm[0]
            if len(fit_nm)>1:
                print 'Standard deviation ('+name_of_charlength+')', fit_nm[1]
        
        print 'Fit quality: '+str(qstd/np.std(displayed_plot.vectors[1][1][-20:-1]))
            
            
        #add the clicked points in the final PlotObject
        clickvector_x, clickvector_y=[], []
        for item in points:
            clickvector_x.append(item.graph_coords[0])
            clickvector_y.append(item.graph_coords[1])

        #create a custom PlotObject to gracefully plot the fit along the curves

        fitplot=copy.deepcopy(displayed_plot)
        fitplot.add_set(xfit,yfit)
        fitplot.add_set(clickvector_x,clickvector_y)

        #FIXME: this colour/styles stuff must be solved at the root!
        if fitplot.styles==[]:
            fitplot.styles=[None,None,None,'scatter']
        else:
            fitplot.styles+=[None,'scatter']

        if fitplot.colors==[]:
            fitplot.colors=[None,None,None,None]
        else:
            fitplot.colors+=[None,None]

        self._send_plot([fitplot])
