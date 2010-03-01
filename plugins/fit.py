#!/usr/bin/env python

'''
fit.py

Force spectroscopy curves basic fitting plugin.

Plugin dependencies:
procplots.py (plot processing plugin)

Copyright ???? by ?
with modifications by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

import lib.libhooke as lh
import wxversion
wxversion.select(lh.WX_GOOD)

import copy
from math import exp
import numpy as np
import scipy.stats
import scipy.odr

import lib.clickedpoint

class fitCommands(object):
    '''
    Do not use any of the following commands directly:
    - wlc
    - fjc
    - fjcPEG
    These commands are not implemented properly yet. However, the properties you set for these commands are used for the autopeak command.
    '''

    def _plug_init(self):
        self.wlccurrent=None
        self.wlccontact_point=None
        self.wlccontact_index=None

    def wlc_fit(self, clicked_points, xvector, yvector, pl_value, T=293, return_errors=False):
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

        def wlc_eval(x, params, pl_value, T):
            '''
            Evaluates the WLC function
            '''
            if not pl_value:
                lambd, pii = params
            else:
                lambd = params

            if pl_value:
                pii=1/pl_value

            Kb=(1.38065e-23) #Boltzmann constant
            therm=Kb*T #so we have thermal energy

            return ((therm*pii / 4.0) * (((1 - (x*lambd))**-2.0) - 1 + (4.0*x*lambd)) )

        #STEP 3: plotting the fit

        #obtain domain to plot the fit - from contact point to last_index plus 20 points
        thule_index=last_index + 1
        if thule_index > len(xvector): #for rare cases in which we fit something at the END of whole curve.
            thule_index = len(xvector)
        #reverse etc. the domain
        xfit_chunk=xvector[clicked_points[0].index:thule_index]
        xfit_chunk.reverse()
        xfit_chunk_corr_up=[-(x-clicked_points[0].graph_coords[0]) for x in xfit_chunk]
        xfit_chunk_corr_up=scipy.array(xfit_chunk_corr_up)

        #the fitted curve: reflip, re-uncorrect
        #x_max = xfit_chunk_corr_up[-1]
        #x_min = xfit_chunk_corr_up[0]
        #points_in_fit = 50
        #increment = (x_max - x_min) / (points_in_fit - 1)
        #x_help = [x_min + x * increment for x in range(points_in_fit)]
        #xfit_chunk = [x_min + x * increment for x in range(points_in_fit)]
        #xfit_chunk.reverse()
        #x_help = scipy.array(x_help)

        #yfit = wlc_eval(x_help, out.beta, pl_value, T)

        yfit=wlc_eval(xfit_chunk_corr_up, out.beta, pl_value,T)
        yfit_down=[-y for y in yfit]
        yfit_corr_down=[y+clicked_points[0].graph_coords[1] for y in yfit_down]

        plot = self.GetActivePlot()

        if return_errors:
            return fit_out, yfit_corr_down, xfit_chunk, fit_errors
        else:
            return fit_out, yfit_corr_down, xfit_chunk, None

    def fjc_fit(self, clicked_points, xvector, yvector, pl_value, T=293, return_errors=False):
        '''
        Freely-jointed chain function
        ref: C.Ray and B.B. Akhremitchev; http://www.chem.duke.edu/~boris/research/force_spectroscopy/fit_efjc.pdf
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
        def x_fjc(params,f,T=T):
            '''
            fjc function for ODR fitting
            '''
            lambd,pii=params
            Kb=(1.38065e-23)
            therm=Kb*T

            #x=(therm*pii/4.0) * (((1-(x*lambd))**-2) - 1 + (4*x*lambd))
            x=(1/lambd)*(lh.coth(f*(1/pii)/therm) - (therm*pii)/f)
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
            x=(1/lambd)*(lh.coth(f*(1/pii)/therm) - (therm*pii)/f)
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

        def fjc_eval(y, params, pl_value, T):
            '''
            Evaluates the FJC function
            '''
            if not pl_value:
                lambd, pii = params
            else:
                lambd = params

            if pl_value:
                pii = 1/pl_value

            Kb = (1.38065e-23) #Boltzmann constant
            therm = Kb * T #so we have thermal energy
            #return ( (therm*pii/4.0) * (((1-(x*lambd))**-2.0) - 1 + (4.0*x*lambd)) )
            return (1 / lambd) * (lh.coth(y * (1 / pii) / therm) - (therm * pii) / y)


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

        if return_errors:
            #return fit_out, yfit_corr_down, xfit_chunk_corr_up, fit_errors
            return fit_out, yfit_corr_down[normalize_index+1:], xfit_chunk_corr_up[normalize_index+1:], fit_errors
        else:
            #return fit_out, yfit_corr_down, xfit_chunk_corr_up, None
            return fit_out, yfit_corr_down[normalize_index+1:], xfit_chunk_corr_up[normalize_index+1:], None

    def fjcPEG_fit(self, clicked_points, xvector, yvector, pl_value, T=293, return_errors=False):
        '''
        Freely-jointed chain function for PEG-containing molecules
        ref: C.Ray and B.B. Akhremitchev; http://www.chem.duke.edu/~boris/research/force_spectroscopy/fit_efjc.pdf
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

        L_helical = self.GetFloatFromConfig('fit', 'fjcPEG', 'L_helical') #in nm
        L_planar = self.GetFloatFromConfig('fit', 'fjcPEG', 'L_planar') #in nm
        delta_G = self.GetFloatFromConfig('fit', 'fjcPEG', 'delta_G') #in Kb*T

        p0=[(1/xchunk_high),(1/(3.5e-10))]
        p0_plfix=[(1/xchunk_high)]
        '''
        ODR STUFF
        fixme: remove these comments after testing
        '''
        def x_fjcPEG(params,f,T=T):
            '''
            fjcPEG function for ODR fitting
            '''
            lambd,pii=params
            Kb=(1.38065e-23)
            therm=Kb*T

            #x=(therm*pii/4.0) * (((1-(x*lambd))**-2) - 1 + (4*x*lambd))

            x=(1/lambd)*(1 / (exp(delta_G) + 1) + (L_helical/L_planar) * (1 / (exp(-delta_G) + 1))) * (lh.coth(f*(1/pii)/therm) - (therm*pii)/f)
            return x

        def x_fjcPEG_plfix(params,f,pl_value=pl_value,T=T):
            '''
            fjcPEG function for ODR fitting
            '''
            lambd=params
            pii=1/pl_value
            Kb=(1.38065e-23)
            therm=Kb*T
            #y=(therm*pii/4.0) * (((1-(x*lambd))**-2) - 1 + (4*x*lambd))
            x=(1/lambd)*(1 / (exp(delta_G) + 1) + (L_helical/L_planar) * (1 / (exp(-delta_G) + 1))) * (lh.coth(f*(1/pii)/therm) - (therm*pii)/f)
            return x

        #make the ODR fit
        realdata=scipy.odr.RealData(ychunk_corr_up,xchunk_corr_up)
        if pl_value:
            model=scipy.odr.Model(x_fjcPEG_plfix)
            o = scipy.odr.ODR(realdata, model, p0_plfix)
        else:
            model=scipy.odr.Model(x_fjcPEG)
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

        def fjcPEG_eval(y, params, pl_value, T):
            '''
            Evaluates the fjcPEG function
            '''
            if not pl_value:
                lambd, pii = params
            else:
                lambd = params

            if pl_value:
                pii = 1/pl_value

            Kb = (1.38065e-23) #Boltzmann constant
            therm = Kb * T #so we have thermal energy
            #return ( (therm*pii/4.0) * (((1-(x*lambd))**-2.0) - 1 + (4.0*x*lambd)) )
            return (1/lambd)*(1 / (exp(delta_G) + 1) + (L_helical/L_planar) * (1 / (exp(-delta_G) + 1))) * (lh.coth(y*(1/pii)/therm) - (therm*pii)/y)

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
        xfit=fjcPEG_eval(yfit_corr_down, out.beta, pl_value,T)
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

        if return_errors:
            #return fit_out, yfit_corr_down, xfit_chunk_corr_up, fit_errors
            return fit_out, yfit_corr_down[normalize_index+1:], xfit_chunk_corr_up[normalize_index+1:], fit_errors
        else:
            #return fit_out, yfit_corr_down, xfit_chunk_corr_up, None
            return fit_out, yfit_corr_down[normalize_index+1:], xfit_chunk_corr_up[normalize_index+1:], None

    def do_wlc(self,args):
        '''
        WLC
        (fit.py plugin)

        See the fit command
        '''
        self.fit(args)

    def do_fjc(self,args):
        '''
        FJC
        (fit.py plugin)

        See the fit command
        '''
        self.fit(args)

    def do_fjcPEG(self,args):
        '''
        fjcPEG
        (fit.py plugin)

        default values for PEG
        ----------------------
        delta_G: 3 Kb*T
        L_helical: 0.28 nm
        L_planar: 0.358 nm

        See the fit command for more information
        '''
        self.fit(args)

    def fit(self,args):
        '''
        FIT
        (fit.py plugin)
        Fits an entropic elasticity function to a given chunk of the curve.

        First you have to click a contact point.
        Then you have to click the two edges of the data you want to fit.

        The fit function depends on the fit_function variable. You can set it with the command
        "set fit_function wlc" or  "set fit_function fjc" depending on the function you prefer.

        For WLC, the function is the simple polynomial worm-like chain as proposed by
        C.Bustamante, J.F.Marko, E.D.Siggia and S.Smith (Science. 1994
        Sep 9;265(5178):1599-600.)

        For FJC, ref:
        C.Ray and B.B. Akhremitchev; http://www.chem.duke.edu/~boris/research/force_spectroscopy/fit_efjc.pdf

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
        T = self.config['fit'].as_float['temperature']
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
            contact_point=self._measure_N_points(N=1, whatset=lh.RETRACTION)[0]
            contact_point_index=contact_point.index
            self.wlccontact_point=contact_point
            self.wlccontact_index=contact_point.index
            self.wlccurrent=self.current.path
        elif 'noauto' in args.split():
            if self.wlccontact_index is None or self.wlccurrent != self.current.path:
                print 'Click contact point'
                contact_point=self._measure_N_points(N=1, whatset=lh.RETRACTION)[0]
                contact_point_index=contact_point.index
                self.wlccontact_point=contact_point
                self.wlccontact_index=contact_point.index
                self.wlccurrent=self.current.path
            else:
                contact_point=self.wlccontact_point
                contact_point_index=self.wlccontact_index
        else:
            cindex=self.find_contact_point()
            contact_point = lib.clickedpoint.ClickedPoint()
            contact_point.absolute_coords=displayed_plot.vectors[1][0][cindex], displayed_plot.vectors[1][1][cindex]
            contact_point.find_graph_coords(displayed_plot.vectors[1][0], displayed_plot.vectors[1][1])
            contact_point.is_marker=True

        print 'Click edges of chunk'
        points=self._measure_N_points(N=2, whatset=lh.RETRACTION)
        points=[contact_point]+points
        try:
            if self.config['fit_function']=='wlc':
                params, yfit, xfit, fit_errors = self.wlc_fit(points, displayed_plot.vectors[1][0], displayed_plot.vectors[1][1],pl_value,T, return_errors=True )
                name_of_charlength='Persistent length'
            elif self.config['fit_function']=='fjc':
                params, yfit, xfit, fit_errors = self.fjc_fit(points, displayed_plot.vectors[1][0], displayed_plot.vectors[1][1],pl_value,T, return_errors=True )
                name_of_charlength='Kuhn length'
            elif self.config['fit_function']=='fjcPEG':
                params, yfit, xfit, fit_errors = self.fjcPEG_fit(points, displayed_plot.vectors[1][0], displayed_plot.vectors[1][1],pl_value,T, return_errors=True )
                name_of_charlength='Kuhn length'
            else:
                print 'No recognized fit function defined!'
                print 'Set your fit function to wlc or fjc.'
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

    #TODO: remove 'plot' as parameter
    def find_contact_point(self, plot=None):
        '''
        Finds the contact point on the curve.

        The current algorithm (thanks to Francesco Musiani, francesco.musiani@unibo.it and Massimo Sandal) is:
        - take care of the PicoForce trigger bug - exclude retraction portions with too high standard deviation
        - fit the second half of the retraction curve to a line
        - if the fit is not almost horizontal, take a smaller chunk and repeat
        - otherwise, we have something horizontal
        - so take the average of horizontal points and use it as a baseline

        Then, start from the rise of the retraction curve and look at the first point below the
        baseline.

        FIXME: should be moved, probably to generalvclamp.py
        '''

        #TODO: pickup current curve?
        if plot is None:
            return

        extension = copy.deepcopy(plot.curves[lh.EXTENSION])
        retraction = copy.deepcopy(plot.curves[lh.RETRACTION])
        yext = extension.y
        yret = retraction.y
        extension, retraction = self.subtract_curves(extension, retraction)
        xret = retraction.x
        ydiff = retraction.y
        #taking care of the picoforce trigger bug: we exclude portions of the curve that have too much
        #standard deviation. yes, a lot of magic is here.
        monster=True
        monlength=len(xret)-int(len(xret)/20)
        finalength=len(xret)
        while monster:
            monchunk=scipy.array(ydiff[monlength:finalength])
            #TODO: there is a difference between scipy.stats.std and numpy.std: why?
            #if abs(scipy.stats.std(monchunk)) < 2e-10:
            if abs(np.std(monchunk)) < 2e-10:
                monster=False
            else: #move away from the monster
                monlength-=int(len(xret)/50)
                finalength-=int(len(xret)/50)
        #take half of the thing
        endlength=int(len(xret)/2)
        ok=False
        while not ok:
            xchunk=yext[endlength:monlength]
            ychunk=yext[endlength:monlength]
            regr=scipy.stats.linregress(xchunk,ychunk)[0:2]
            #we stop if we found an almost-horizontal fit or if we're going too short...
            #FIXME: 0.1 and 6 here are "magic numbers" (although reasonable)
            if (abs(regr[1]) > 0.1) and ( endlength < len(xret)-int(len(xret)/6) ) :
                endlength+=10
            else:
                ok=True
        #ymean=scipy.mean(ychunk) #baseline
        ymean = np.mean(ychunk) #baseline

        #TODO: check if this works rather than the thing below
        #for index, point in enumerate(yret):
            #if point < ymean:
                #result = index
        #result = -1

        #find the first point below the calculated baseline
        index=0
        point = ymean+1
        while point > ymean:
            try:
                point=yret[index]
                index+=1
            except IndexError:
                #The algorithm didn't find anything below the baseline! It should NEVER happen
                index=0
                return index

        return index

    def find_contact_point2(self, debug=False):
        '''
        TO BE DEVELOPED IN THE FUTURE
        Finds the contact point on the curve.

        FIXME: should be moved, probably to generalvclamp.py
        '''

        #raw_plot=self.current.curve.default_plots()[0]
        raw_plot=self.plots[0]
        '''xext=self.plots[0].vectors[0][0]
        yext=self.plots[0].vectors[0][1]
        xret2=self.plots[0].vectors[1][0]
        yret=self.plots[0].vectors[1][1]
        '''
        xext=raw_plot.vectors[0][0]
        yext=raw_plot.vectors[0][1]
        xret2=raw_plot.vectors[1][0]
        yret=raw_plot.vectors[1][1]

        first_point=[xext[0], yext[0]]
        last_point=[xext[-1], yext[-1]]

        #regr=scipy.polyfit(first_point, last_point,1)[0:2]
        diffx=abs(first_point[0]-last_point[0])
        diffy=abs(first_point[1]-last_point[1])

        #using polyfit results in numerical errors. good old algebra.
        a=diffy/diffx
        b=first_point[1]-(a*first_point[0])
        baseline=scipy.polyval((a,b), xext)

        ysub=[item-basitem for item,basitem in zip(yext,baseline)]

        contact=ysub.index(min(ysub))

        return xext,ysub,contact

        #now, exploit a ClickedPoint instance to calculate index...
        dummy=lib.clickedpoint.ClickedPoint()
        dummy.absolute_coords=(x_intercept,y_intercept)
        dummy.find_graph_coords(xret2,yret)

        if debug:
            return dummy.index, regr, regr_contact
        else:
            return dummy.index



    #def x_do_contact(self,args):
        #'''
        #DEBUG COMMAND to be activated in the future
        #'''
        #xext,ysub,contact=self.find_contact_point2(debug=True)

        #contact_plot=self.plots[0]
        #contact_plot.add_set(xext,ysub)
        #contact_plot.add_set([xext[contact]],[self.plots[0].vectors[0][1][contact]])
        ##contact_plot.add_set([first_point[0]],[first_point[1]])
        ##contact_plot.add_set([last_point[0]],[last_point[1]])
        #contact_plot.styles=[None,None,None,'scatter']
        #self._send_plot([contact_plot])
        #return

        #index,regr,regr_contact=self.find_contact_point2(debug=True)
        #print regr
        #print regr_contact
        #raw_plot=self.current.curve.default_plots()[0]
        #xret=raw_plot.vectors[0][0]
        ##nc_line=[(item*regr[0])+regr[1] for item in x_nc]
        #nc_line=scipy.polyval(regr,xret)
        #c_line=scipy.polyval(regr_contact,xret)


        #contact_plot=self.current.curve.default_plots()[0]
        #contact_plot.add_set(xret, nc_line)
        #contact_plot.add_set(xret, c_line)
        #contact_plot.styles=[None,None,None,None]
        ##contact_plot.styles.append(None)
        #contact_plot.destination=1
        #self._send_plot([contact_plot])
