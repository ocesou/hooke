# Copyright (C) 2008-2010 Alberto Gomez-Casado
#                         Fabrizio Benedetti
#                         Marco Brucale
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

"""The ``vclamp`` module provides :class:`VelocityClampPlugin` and
several associated :class:`hooke.command.Command`\s for handling
common velocity clamp analysis tasks.
"""

import copy

import numpy
import scipy

from ..command import Command, Argument, Failure, NullQueue
from ..config import Setting
from ..curve import Data
from ..plugin import Builtin
from ..util.fit import PoorFit, ModelFitter
from .curve import CurveArgument


def scale(hooke, curve):
    commands = hooke.commands
    contact = [c for c in hooke.commands
               if c.name == 'zero block surface contact point'][0]
    force = [c for c in hooke.commands if c.name == 'add block force array'][0]
    inqueue = None
    outqueue = NullQueue()
    for i,block in enumerate(curve.data):
        numpy.savetxt(open('curve.dat', 'w'), block, delimiter='\t')
        params = {'curve':curve, 'block':i}
        try:
            contact._run(hooke, inqueue, outqueue, params)
        except PoorFit, e:
            raise PoorFit('Could not fit %s %s: %s'
                          % (curve.path, i, str(e)))
        force._run(hooke, inqueue, outqueue, params)
    return curve

class SurfacePositionModel (ModelFitter):
    """

    The bilinear model is symmetric, but the parameter guessing and
    sanity checks assume the contact region occurs for lower indicies
    ("left of") the non-contact region.  We also assume that
    tip-surface attractions produce positive deflections.

    Notes
    -----
    Algorithm borrowed from WTK's `piezo package`_, specifically
    from :func:`piezo.z_piezo_utils.analyzeSurfPosData`.

    .. _piezo package:
      http://www.physics.drexel.edu/~wking/code/git/git.php?p=piezo.git

    Fits the data to the bilinear :method:`model`.

    In order for this model to produce a satisfactory fit, there
    should be enough data in the off-surface region that interactions
    due to proteins, etc. will not seriously skew the fit in the
    off-surface region.


    We guess
    """
    def model(self, params):
        """A continuous, bilinear model.

        Notes
        -----
        .. math::
    
          y = \begin{cases}
            p_0 + p_1 x                 & \text{if $x <= p_2$}, \\
            p_0 + p_1 p_2 + p_3 (x-p_2) & \text{if $x >= p_2$}.
              \end{cases}
    
        Where :math:`p_0` is a vertical offset, :math:`p_1` is the slope
        of the first region, :math:`p_2` is the transition location, and
        :math:`p_3` is the slope of the second region.
        """
        p = params  # convenient alias
        if self.info.get('force zero non-contact slope', None) == True:
            p = list(p)
            p.append(0.)  # restore the non-contact slope parameter
        r2 = numpy.round(abs(p[2]))
        if r2 >= 1:
            self._model_data[:r2] = p[0] + p[1] * numpy.arange(r2)
        if r2 < len(self._data)-1:
            self._model_data[r2:] = \
                p[0] + p[1]*p[2] + p[3] * numpy.arange(len(self._data)-r2)
        return self._model_data

    def set_data(self, data, info=None):
        super(SurfacePositionModel, self).set_data(data, info)
        if info == None:
            info = {}
        self.info = info
        self.info['min position'] = 0
        self.info['max position'] = len(data)
        self.info['max deflection'] = data.max()
        self.info['min deflection'] = data.min()
        self.info['position range'] = self.info['max position'] - self.info['min position']
        self.info['deflection range'] = self.info['max deflection'] - self.info['min deflection']

    def guess_initial_params(self, outqueue=None):
        """Guess the initial parameters.

        Notes
        -----
        We guess initial parameters such that the offset (:math:`p_1`)
        matches the minimum deflection, the kink (:math:`p_2`) occurs in
        the middle of the data, the initial (contact) slope (:math:`p_0`)
        produces the maximum deflection at the left-most point, and the
        final (non-contact) slope (:math:`p_3`) is zero.
        """
        left_offset = self.info['min deflection']
        left_slope = 2*(self.info['deflection range']
                        /self.info['position range'])
        kink_position = (self.info['max position']
                         +self.info['min position'])/2.0
        right_slope = 0
        self.info['guessed contact slope'] = left_slope
        params = [left_offset, left_slope, kink_position, right_slope]
        if self.info.get('force zero non-contact slope', None) == True:
            params = params[:-1]
        return params

    def guess_scale(self, params, outqueue=None):
        """Guess the parameter scales.

        Notes
        -----

        We guess offset scale (:math:`p_0`) as one tenth of the total
        deflection range, the kink scale (:math:`p_2`) as one tenth of
        the total index range, the initial (contact) slope scale
        (:math:`p_1`) as one tenth of the contact slope estimation,
        and the final (non-contact) slope scale (:math:`p_3`) is as
        one tenth of the initial slope scale.
        """
        offset_scale = self.info['deflection range']/10.
        left_slope_scale = abs(params[1])/10.
        kink_scale = self.info['position range']/10.
        right_slope_scale = left_slope_scale/10.
        scale = [offset_scale, left_slope_scale, kink_scale, right_slope_scale]
        if self.info.get('force zero non-contact slope', None) == True:
            scale = scale[:-1]
        return scale

    def fit(self, *args, **kwargs):
        self.info['guessed contact slope'] = None
        params = super(SurfacePositionModel, self).fit(*args, **kwargs)
        params[2] = abs(params[2])
        if self.info.get('force zero non-contact slope', None) == True:
            params = list(params)
            params.append(0.)  # restore the non-contact slope parameter

        # check that the fit is reasonable, see the :meth:`model` docstring
        # for parameter descriptions.  HACK: hardcoded cutoffs.
        if abs(params[3]*10) > abs(params[1]) :
            raise PoorFit('Slope in non-contact region, or no slope in contact')
        if params[2] < self.info['min position']+0.02*self.info['position range']:
            raise PoorFit(
                'No kink (kink %g less than %g, need more space to left)'
                % (params[2],
                   self.info['min position']+0.02*self.info['position range']))
        if params[2] > self.info['max position']-0.02*self.info['position range']:
            raise poorFit(
                'No kink (kink %g more than %g, need more space to right)'
                % (params[2],
                   self.info['max position']-0.02*self.info['position range']))
        if (self.info['guessed contact slope'] != None
            and abs(params[1]) < 0.5 * abs(self.info['guessed contact slope'])):
            raise PoorFit('Too far (contact slope %g, but expected ~%g'
                          % (params[3], self.info['guessed contact slope']))
        return params

class VelocityClampPlugin (Builtin):
    def __init__(self):
        super(VelocityClampPlugin, self).__init__(name='vclamp')
        self._commands = [
            SurfaceContactCommand(self), ForceCommand(self),
            ]

    def default_settings(self):
        return [
            Setting(section=self.setting_section, help=self.__doc__),
            Setting(section=self.setting_section,
                    option='surface contact point algorithm',
                    value='wtk',
                    help='Select the surface contact point algorithm.  See the documentation for descriptions of available algorithms.')
            ]


class SurfaceContactCommand (Command):
    """Automatically determine a block's surface contact point.

    Uses the block's `z piezo (m)` and `deflection (m)` arrays.
    Stores the contact parameters in `block.info`'s `surface distance
    offset (m)` and `surface deflection offset (m)`.  Model-specific
    fitting information is stored in `surface detection parameters`.

    The adjusted data columns `surface distance (m)` and `surface
    adjusted deflection (m)` are also added to the block.

    You can select the contact point algorithm with the creatively
    named `surface contact point algorithm` configuration setting.
    Currently available options are:

    * fmms (:meth:`find_contact_point_fmms`)
    * ms (:meth:`find_contact_point_ms`)
    * wtk (:meth:`find_contact_point_wtk`)
    """
    def __init__(self, plugin):
        super(SurfaceContactCommand, self).__init__(
            name='zero block surface contact point',
            arguments=[
                CurveArgument,
                Argument(name='block', aliases=['set'], type='int', default=0,
                         help="""
Data block for which the force should be calculated.  For an
approach/retract force curve, `0` selects the approaching curve and `1`
selects the retracting curve.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        data = params['curve'].data[int(params['block'])] # HACK, int() should be handled by ui
        # HACK? rely on params['curve'] being bound to the local hooke
        # playlist (i.e. not a copy, as you would get by passing a
        # curve through the queue).  Ugh.  Stupid queues.  As an
        # alternative, we could pass lookup information through the
        # queue...
        new = Data((data.shape[0], data.shape[1]+2), dtype=data.dtype)
        new.info = copy.deepcopy(data.info)
        new[:,:-2] = data
        new.info['columns'].extend(
            ['surface distance (m)', 'surface adjusted deflection (m)'])
        z_data = data[:,data.info['columns'].index('z piezo (m)')]
        d_data = data[:,data.info['columns'].index('deflection (m)')]
        i,deflection_offset,ps = self.find_contact_point(
            params['curve'], z_data, d_data, outqueue)
        surface_offset = z_data[i]
        new.info['surface distance offset (m)'] = surface_offset
        new.info['surface deflection offset (m)'] = deflection_offset
        new.info['surface detection parameters'] = ps
        new[:,-2] = z_data - surface_offset
        new[:,-1] = d_data - deflection_offset
        data = params['curve'].data[int(params['block'])] # HACK, int() should be handled by ui
        params['curve'].data[int(params['block'])] = new # HACK, int() should be handled by ui

    def find_contact_point(self, curve, z_data, d_data, outqueue=None):
        """Railyard for the `find_contact_point_*` family.

        Uses the `surface contact point algorithm` configuration
        setting to call the appropriate backend algorithm.
        """
        fn = getattr(self, 'find_contact_point_%s'
                     % self.plugin.config['surface contact point algorithm'])
        return fn(curve, z_data, d_data, outqueue)

    def find_contact_point_fmms(self, curve, z_data, d_data, outqueue=None):
        """Algorithm by Francesco Musiani and Massimo Sandal.

        Notes
        -----
        Algorithm:

        0) Driver-specific workarounds, e.g. deal with the PicoForce
          trigger bug by excluding retraction portions with excessive
          deviation.
        1) Select the second half (non-contact side) of the retraction
          curve.
        2) Fit the selection to a line.
        3) If the fit is not almost horizontal, halve the selection
          and retrun to (2).
        4) Average the selection and use it as a baseline.
        5) Slide in from the start (contact side) of the retraction
        curve, until you find a point with greater than baseline
        deflection.  That point is the contact point.
        """
        if curve.info['filetype'] == 'picoforce':
            # Take care of the picoforce trigger bug (TODO: example
            # data file demonstrating the bug).  We exclude portions
            # of the curve that have too much standard deviation.
            # Yes, a lot of magic is here.
            check_start = len(d_data)-len(d_data)/20
            monster_start = len(d_data)
            while True:
                # look at the non-contact tail
                non_monster = d_data[check_start:monster_start]
                if non_monster.std() < 2e-10: # HACK: hardcoded cutoff
                    break
                else: # move further away from the monster
                    check_start -= len(d_data)/50
                    monster_start -= len(d_data)/50
            z_data = z_data[:monster_start]
            d_data = d_data[:monster_start]

        # take half of the thing to start
        selection_start = len(d_data)/2
        while True:
            z_chunk = z_data[selection_start:]
            d_chunk = d_data[selection_start:]
            slope,intercept,r,two_tailed_prob,stderr_of_the_estimate = \
                scipy.stats.linregress(z_chunk, d_chunk)
            # We stop if we found an almost-horizontal fit or if we're
            # getting to small a selection.  FIXME: 0.1 and 5./6 here
            # are "magic numbers" (although reasonable)
            if (abs(slope) < 0.1  # deflection (m) / surface (m)
                or selection_start > 5./6*len(d_data)):
                break
            selection_start += 10

        d_baseline = d_chunk.mean()

        # find the first point above the calculated baseline
        i = 0
        while i < len(d_data) and d_data[i] < ymean:
            i += 1
        return (i, d_baseline, {})

    def find_contact_point_ms(self, curve, z_data, d_data, outqueue=None):
        """Algorithm by Massimo Sandal.

        Notes
        -----
        WTK: At least the commits are by Massimo, and I see no notes
        attributing the algorithm to anyone else.

        Algorithm:

        * ?
        """
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
        dummy=ClickedPoint()
        dummy.absolute_coords=(x_intercept,y_intercept)
        dummy.find_graph_coords(xret2,yret)

        if debug:
            return dummy.index, regr, regr_contact
        else:
            return dummy.index

    def find_contact_point_wtk(self, curve, z_data, d_data, outqueue=None):
        """Algorithm by W. Trevor King.

        Notes
        -----
        Uses :func:`analyze_surf_pos_data_wtk` internally.
        """
        reverse = z_data[0] > z_data[-1]
        if reverse == True:    # approaching, contact region on the right
            d_data = d_data[::-1]
        s = SurfacePositionModel(d_data)
        s.info['force zero non-contact slope'] = True
        offset,contact_slope,surface_index,non_contact_slope = s.fit(
            outqueue=outqueue)
        info = {
            'offset': offset,
            'contact slope': contact_slope,
            'surface index': surface_index,
            'non-contact slope': non_contact_slope,
            'reversed': reverse,
            }
        deflection_offset = offset + contact_slope*surface_index,
        if reverse == True:
            surface_index = len(d_data)-1-surface_index
        return (numpy.round(surface_index), deflection_offset, info)

class ForceCommand (Command):
    """Calculate a block's `deflection (N)` array.

    Uses the block's `deflection (m)` array and `spring constant
    (N/m)`.
    """
    def __init__(self, plugin):
        super(ForceCommand, self).__init__(
            name='add block force array',
            arguments=[
                CurveArgument,
                Argument(name='block', aliases=['set'], type='int', default=0,
                         help="""
Data block for which the force should be calculated.  For an
approach/retract force curve, `0` selects the approaching curve and `1`
selects the retracting curve.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        data = params['curve'].data[int(params['block'])] # HACK, int() should be handled by ui
        # HACK? rely on params['curve'] being bound to the local hooke
        # playlist (i.e. not a copy, as you would get by passing a
        # curve through the queue).  Ugh.  Stupid queues.  As an
        # alternative, we could pass lookup information through the
        # queue.
        new = Data((data.shape[0], data.shape[1]+1), dtype=data.dtype)
        new.info = copy.deepcopy(data.info)
        new[:,:-1] = data
        new.info['columns'].append('deflection (N)')
        d_data = data[:,data.info['columns'].index('surface adjusted deflection (m)')]
        new[:,-1] = d_data * data.info['spring constant (N/m)']
        params['curve'].data[int(params['block'])] = new # HACK, int() should be handled by ui


class generalvclampCommands(object):

    def do_subtplot(self, args):
        '''
        SUBTPLOT
        (procplots.py plugin)
        Plots the difference between ret and ext current curve
        -------
        Syntax: subtplot
        '''
        #FIXME: sub_filter and sub_order must be args

        if len(self.plots[0].vectors) != 2:
            print 'This command only works on a curve with two different plots.'
            pass

        outplot=self.subtract_curves(sub_order=1)

        plot_graph=self.list_of_events['plot_graph']
        wx.PostEvent(self.frame,plot_graph(plots=[outplot]))

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

    def plotmanip_multiplier(self, plot, current):
        '''
        Multiplies all the Y values of an SMFS curve by a value stored in the 'force_multiplier'
        configuration variable. Useful for calibrations and other stuff.
        '''

        #not a smfs curve...
        if current.curve.experiment != 'smfs':
            return plot

        #only one set is present...
        if len(self.plots[0].vectors) != 2:
            return plot

        #multiplier is 1...
        if (self.config['force_multiplier']==1):
            return plot

        for i in range(len(plot.vectors[0][1])):
            plot.vectors[0][1][i]=plot.vectors[0][1][i]*self.config['force_multiplier']        

        for i in range(len(plot.vectors[1][1])):
            plot.vectors[1][1][i]=plot.vectors[1][1][i]*self.config['force_multiplier']

        return plot            
   
    
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
        
        #Check if we have a proper numerical value
        try:
            zzz=int(max_cycles)
        except:
            #Loudly and annoyingly complain if it's not a number, then fallback to zero
            print '''Warning: flatten value is not a number!
            Use "set flatten" or edit hooke.conf to set it properly
            Using zero.'''
            max_cycles=0
        
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
            points=self._measure_N_points(N=2,whatset=1)
        else:
            print 'Click once on the leftmost point of the chunk (i.e.usually the peak)'
            points=self._measure_N_points(N=1,whatset=1)
            
        slope=self._slope(points,fitspan)

        # Outputs the relevant slope parameter
        print 'Slope:'
        print str(slope)
        to_dump='slope '+self.current.path+' '+str(slope)
        self.outlet.push(to_dump)

    def _slope(self,points,fitspan):
        # Calls the function linefit_between
        parameters=[0,0,[],[]]
        try:
            clickedpoints=[points[0].index,points[1].index]
            clickedpoints.sort()
        except:
            clickedpoints=[points[0].index-fitspan,points[0].index]        

        try:
            parameters=self.linefit_between(clickedpoints[0],clickedpoints[1])
        except:
            print 'Cannot fit. Did you click twice the same point?'
            return
             
        # Outputs the relevant slope parameter
        print 'Slope:'
        print str(parameters[0])
        to_dump='slope '+self.curve.path+' '+str(parameters[0])
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
        if lineplot.colors==[]:
            lineplot.colors=[None,None,'black',None]
        else:
            lineplot.colors+=['black',None]
        
        
        self._send_plot([lineplot])

        return parameters[0]


    def linefit_between(self,index1,index2,whatset=1):
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
        xtofit=self.plots[0].vectors[whatset][0][index1:index2]
        ytofit=self.plots[0].vectors[whatset][1][index1:index2]

        # Does the actual linear fitting (simple least squares with numpy.polyfit)
        linefit=[]
        linefit=np.polyfit(xtofit,ytofit,1)

        return (linefit[0],linefit[1],xtofit,ytofit)


    def fit_interval_nm(self,start_index,plot,nm,backwards):
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



    def find_current_peaks(self,noflatten, a=True, maxpeak=True):
            #Find peaks.
            if a==True:
                  a=self.convfilt_config['mindeviation']
            try:
                  abs_devs=float(a)
            except:
                  print "Bad input, using default."
                  abs_devs=self.convfilt_config['mindeviation']

            defplot=self.current.curve.default_plots()[0]
            if not noflatten:
                flatten=self._find_plotmanip('flatten') #Extract flatten plotmanip
                defplot=flatten(defplot, self.current, customvalue=1) #Flatten curve before feeding it to has_peaks
            pk_location,peak_size=self.has_peaks(defplot, abs_devs, maxpeak)
            return pk_location, peak_size


    def pickup_contact_point(self,N=1,whatset=1):
        '''macro to pick up the contact point by clicking'''
        contact_point=self._measure_N_points(N=1, whatset=1)[0]
        contact_point_index=contact_point.index
        self.wlccontact_point=contact_point
        self.wlccontact_index=contact_point.index
        self.wlccurrent=self.current.path
        return contact_point, contact_point_index


    def baseline_points(self,peak_location, displayed_plot):
        clicks=self.config['baseline_clicks']
        if clicks==0:
            self.basepoints=[]
            base_index_0=peak_location[-1]+self.fit_interval_nm(peak_location[-1], displayed_plot, self.config['auto_right_baseline'],False)
            self.basepoints.append(self._clickize(displayed_plot.vectors[1][0],displayed_plot.vectors[1][1],base_index_0))
            base_index_1=self.basepoints[0].index+self.fit_interval_nm(self.basepoints[0].index, displayed_plot, self.config['auto_left_baseline'],False)
            self.basepoints.append(self._clickize(displayed_plot.vectors[1][0],displayed_plot.vectors[1][1],base_index_1))
        elif clicks>0:
            print 'Select baseline'
            if clicks==1:
                self.basepoints=self._measure_N_points(N=1, whatset=1)
                base_index_1=self.basepoints[0].index+self.fit_interval_nm(self.basepoints[0].index, displayed_plot, self.config['auto_left_baseline'], False)
                self.basepoints.append(self._clickize(displayed_plot.vectors[1][0],displayed_plot.vectors[1][1],base_index_1))
            else:
                self.basepoints=self._measure_N_points(N=2, whatset=1)
            
        self.basecurrent=self.current.path
        return self.basepoints
