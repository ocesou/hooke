# Copyright (C) 2008-2010 Alberto Gomez-Casado
#                         Fabrizio Benedetti
#                         Marco Brucale
#                         Massimo Sandal <devicerandom@gmail.com>
#                         W. Trevor King <wking@drexel.edu>
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

"""The ``vclamp`` module provides :class:`VelocityClampPlugin` and
several associated :class:`hooke.command.Command`\s for handling
common velocity clamp analysis tasks.
"""

import copy
import logging

import numpy
import scipy

from ..command import Command, Argument, Failure, NullQueue
from ..config import Setting
from ..curve import Data
from ..plugin import Plugin
from ..util.fit import PoorFit, ModelFitter
from ..util.si import join_data_label, split_data_label
from .curve import CurveArgument


def scale(hooke, curve, block=None):
    """Run 'add block force array' on `block`.

    Runs 'zero block surface contact point' first, if necessary.  Does
    not run either command if the columns they add to the block are
    already present.

    If `block` is `None`, scale all blocks in `curve`.
    """
    commands = hooke.commands
    contact = [c for c in hooke.commands
               if c.name == 'zero block surface contact point'][0]
    force = [c for c in hooke.commands if c.name == 'add block force array'][0]
    cant_adjust = [c for c in hooke.commands
               if c.name == 'add block cantilever adjusted extension array'][0]
    inqueue = None
    outqueue = NullQueue()
    if block == None:
        for i in range(len(curve.data)):
            scale(hooke, curve, block=i)
    else:
        params = {'curve':curve, 'block':block}
        b = curve.data[block]
        if ('surface distance (m)' not in b.info['columns']
            or 'surface deflection (m)' not in b.info['columns']):
            try:
                contact.run(hooke, inqueue, outqueue, **params)
            except PoorFit, e:
                raise PoorFit('Could not fit %s %s: %s'
                              % (curve.path, block, str(e)))
        if ('deflection (N)' not in b.info['columns']):
            force.run(hooke, inqueue, outqueue, **params)
        if ('cantilever adjusted extension (m)' not in b.info['columns']):
            cant_adjust.run(hooke, inqueue, outqueue, **params)
    return curve

class SurfacePositionModel (ModelFitter):
    """Bilinear surface position model.

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

class VelocityClampPlugin (Plugin):
    def __init__(self):
        super(VelocityClampPlugin, self).__init__(name='vclamp')
        self._commands = [
            SurfaceContactCommand(self), ForceCommand(self),
            CantileverAdjustedExtensionCommand(self), FlattenCommand(self),
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
                Argument(name='input distance column', type='string',
                         default='z piezo (m)',
                         help="""
Name of the column to use as the surface position input.
""".strip()),
                Argument(name='input deflection column', type='string',
                         default='deflection (m)',
                         help="""
Name of the column to use as the deflection input.
""".strip()),
                Argument(name='output distance column', type='string',
                         default='surface distance',
                         help="""
Name of the column (without units) to use as the surface position output.
""".strip()),
                Argument(name='output deflection column', type='string',
                         default='surface deflection',
                         help="""
Name of the column (without units) to use as the deflection output.
""".strip()),
                Argument(name='distance info name', type='string',
                         default='surface distance offset',
                         help="""
Name (without units) for storing the distance offset in the `.info` dictionary.
""".strip()),
                Argument(name='deflection info name', type='string',
                         default='surface deflection offset',
                         help="""
Name (without units) for storing the deflection offset in the `.info` dictionary.
""".strip()),
                Argument(name='fit parameters info name', type='string',
                         default='surface deflection offset',
                         help="""
Name (without units) for storing fit parameters in the `.info` dictionary.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        data = params['curve'].data[params['block']]
        # HACK? rely on params['curve'] being bound to the local hooke
        # playlist (i.e. not a copy, as you would get by passing a
        # curve through the queue).  Ugh.  Stupid queues.  As an
        # alternative, we could pass lookup information through the
        # queue...
        new = Data((data.shape[0], data.shape[1]+2), dtype=data.dtype)
        new.info = copy.deepcopy(data.info)
        new[:,:-2] = data
        name,dist_units = split_data_label(params['input distance column'])
        name,def_units = split_data_label(params['input deflection column'])
        new.info['columns'].extend([
                join_data_label(params['output distance column'], dist_units),
                join_data_label(params['output deflection column'], def_units),
                ])
        dist_data = data[:,data.info['columns'].index(
                params['input distance column'])]
        def_data = data[:,data.info['columns'].index(
                params['input deflection column'])]
        i,def_offset,ps = self.find_contact_point(
            params['curve'], dist_data, def_data, outqueue)
        dist_offset = dist_data[i]
        new.info[join_data_label(params['distance info name'], dist_units
                                 )] = dist_offset
        new.info[join_data_label(params['deflection info name'], def_units
                                 )] = def_offset
        new.info[params['fit parameters info name']] = ps
        new[:,-2] = dist_data - dist_offset
        new[:,-1] = def_data - def_offset
        params['curve'].data[params['block']] = new

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
    """Convert a deflection column from meters to newtons.
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
                Argument(name='input deflection column', type='string',
                         default='surface deflection (m)',
                         help="""
Name of the column to use as the deflection input.
""".strip()),
                Argument(name='output deflection column', type='string',
                         default='deflection',
                         help="""
Name of the column (without units) to use as the deflection output.
""".strip()),
                Argument(name='spring constant info name', type='string',
                         default='spring constant (N/m)',
                         help="""
Name of the spring constant in the `.info` dictionary.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        data = params['curve'].data[params['block']]
        # HACK? rely on params['curve'] being bound to the local hooke
        # playlist (i.e. not a copy, as you would get by passing a
        # curve through the queue).  Ugh.  Stupid queues.  As an
        # alternative, we could pass lookup information through the
        # queue.
        new = Data((data.shape[0], data.shape[1]+1), dtype=data.dtype)
        new.info = copy.deepcopy(data.info)
        new[:,:-1] = data
        new.info['columns'].append(
            join_data_label(params['output deflection column'], 'N'))
        d_data = data[:,data.info['columns'].index(
                params['input deflection column'])]
        new[:,-1] = d_data * data.info[params['spring constant info name']]
        params['curve'].data[params['block']] = new


class CantileverAdjustedExtensionCommand (Command):
    """Remove cantilever extension from a total extension column.
    """
    def __init__(self, plugin):
        super(CantileverAdjustedExtensionCommand, self).__init__(
            name='add block cantilever adjusted extension array',
            arguments=[
                CurveArgument,
                Argument(name='block', aliases=['set'], type='int', default=0,
                         help="""
Data block for which the adjusted extension should be calculated.  For
an approach/retract force curve, `0` selects the approaching curve and
`1` selects the retracting curve.
""".strip()),
                Argument(name='input distance column', type='string',
                         default='surface distance (m)',
                         help="""
Name of the column to use as the distance input.
""".strip()),
                Argument(name='input deflection column', type='string',
                         default='deflection (N)',
                         help="""
Name of the column to use as the deflection input.
""".strip()),
                Argument(name='output distance column', type='string',
                         default='cantilever adjusted extension',
                         help="""
Name of the column (without units) to use as the deflection output.
""".strip()),
                Argument(name='spring constant info name', type='string',
                         default='spring constant (N/m)',
                         help="""
Name of the spring constant in the `.info` dictionary.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        data = params['curve'].data[params['block']]
        # HACK? rely on params['curve'] being bound to the local hooke
        # playlist (i.e. not a copy, as you would get by passing a
        # curve through the queue).  Ugh.  Stupid queues.  As an
        # alternative, we could pass lookup information through the
        # queue.
        new = Data((data.shape[0], data.shape[1]+1), dtype=data.dtype)
        new.info = copy.deepcopy(data.info)
        new[:,:-1] = data
        new.info['columns'].append(
            join_data_label(params['output distance column'], 'm'))
        z_data = data[:,data.info['columns'].index(
                params['input distance column'])]
        d_data = data[:,data.info['columns'].index(
                params['input deflection column'])]
        k = data.info[params['spring constant info name']]

        z_name,z_unit = split_data_label(params['input distance column'])
        assert z_unit == 'm', params['input distance column']
        d_name,d_unit = split_data_label(params['input deflection column'])
        assert d_unit == 'N', params['input deflection column']
        k_name,k_unit = split_data_label(params['spring constant info name'])
        assert k_unit == 'N/m', params['spring constant info name']

        new[:,-1] = z_data - d_data / k
        params['curve'].data[params['block']] = new


class FlattenCommand (Command):
    """Flatten a deflection column.

    Subtracts a polynomial fit from the non-contact part of the curve
    to flatten it.  The best polynomial fit is chosen among
    polynomials of degree 1 to `max degree`.

    .. todo:  Why does flattening use a polynomial fit and not a sinusoid?
      Isn't most of the oscillation due to laser interference?
      See Jaschke 1995 ( 10.1063/1.1146018 )
      and the figure 4 caption of Weisenhorn 1992 ( 10.1103/PhysRevB.45.11226 )
    """
    def __init__(self, plugin):
        super(FlattenCommand, self).__init__(
            name='add flattened extension array',
            arguments=[
                CurveArgument,
                Argument(name='block', aliases=['set'], type='int', default=0,
                         help="""
Data block for which the adjusted extension should be calculated.  For
an approach/retract force curve, `0` selects the approaching curve and
`1` selects the retracting curve.
""".strip()),
                Argument(name='max degree', type='int',
                         default=1,
                         help="""
Highest order polynomial to consider for flattening.  Using values
greater than one usually doesn't help and can give artifacts.
However, it could be useful too.  (TODO: Back this up with some
theory...)
""".strip()),
                Argument(name='input distance column', type='string',
                         default='surface distance (m)',
                         help="""
Name of the column to use as the distance input.
""".strip()),
                Argument(name='input deflection column', type='string',
                         default='deflection (N)',
                         help="""
Name of the column to use as the deflection input.
""".strip()),
                Argument(name='output deflection column', type='string',
                         default='flattened deflection',
                         help="""
Name of the column (without units) to use as the deflection output.
""".strip()),
                Argument(name='fit info name', type='string',
                         default='flatten fit',
                         help="""
Name of the flattening information in the `.info` dictionary.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        data = params['curve'].data[params['block']]
        # HACK? rely on params['curve'] being bound to the local hooke
        # playlist (i.e. not a copy, as you would get by passing a
        # curve through the queue).  Ugh.  Stupid queues.  As an
        # alternative, we could pass lookup information through the
        # queue.
        new = Data((data.shape[0], data.shape[1]+1), dtype=data.dtype)
        new.info = copy.deepcopy(data.info)
        new[:,:-1] = data
        z_data = data[:,data.info['columns'].index(
                params['input distance column'])]
        d_data = data[:,data.info['columns'].index(
                params['input deflection column'])]

        d_name,d_unit = split_data_label(params['input deflection column'])
        new.info['columns'].append(
            join_data_label(params['output deflection column'], d_unit))

        contact_index = numpy.absolute(z_data).argmin()
        mask = z_data > 0
        indices = numpy.argwhere(mask)
        z_nc = z_data[indices].flatten()
        d_nc = d_data[indices].flatten()

        min_err = numpy.inf
        degree = poly_values = None
        log = logging.getLogger('hooke')
        for deg in range(params['max degree']):
            try:
                pv = scipy.polyfit(z_nc, d_nc, deg)
                df = scipy.polyval(pv, z_nc)
                err = numpy.sqrt((df-d_nc)**2).sum()
            except Exception,e:
                log.warn('failed to flatten with a degree %d polynomial: %s'
                         % (deg, e))
                continue
            if err < min_err:  # new best fit
                min_err = err
                degree = deg
                poly_values = pv

        if degree == None:
            raise Failure('failed to flatten with all degrees')
        new.info[params['fit info name']] = {
            'error':min_err/len(z_nc),
            'degree':degree,
            'max degree':params['max degree'],
            'polynomial values':poly_values,
            }
        new[:,-1] = d_data - mask*scipy.polyval(poly_values, z_data)
        params['curve'].data[params['block']] = new
