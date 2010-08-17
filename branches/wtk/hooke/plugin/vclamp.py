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

from ..command import Argument, Failure, NullQueue
from ..config import Setting
from ..curve import Data
from ..util.fit import PoorFit, ModelFitter
from ..util.si import join_data_label, split_data_label
from . import Plugin
from .curve import ColumnAddingCommand


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
    off-surface region.  If you don't have much of a tail, you can set
    the `info` dict's `ignore non-contact before index` parameter to
    the index of the last surface- or protein-related feature.
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
        rNC_ignore = self.info['ignore non-contact before index']
        if self.info['force zero non-contact slope'] == True:
            p = list(p)
            p.append(0.)  # restore the non-contact slope parameter
        r2 = numpy.round(abs(p[2]))
        if r2 >= 1:
            self._model_data[:r2] = p[0] + p[1] * numpy.arange(r2)
        if r2 < len(self._data)-1:
            self._model_data[r2:] = \
                p[0] + p[1]*p[2] + p[3] * numpy.arange(len(self._data)-r2)
            if r2 < rNC_ignore:
                self._model_data[r2:rNC_ignore] = self._data[r2:rNC_ignore]
        return self._model_data

    def set_data(self, data, info=None, *args, **kwargs):
        super(SurfacePositionModel, self).set_data(data, info, *args, **kwargs)
        if self.info == None:
            self.info = {}
        for key,value in [
            ('force zero non-contact slope', False),
            ('ignore non-contact before index', -1),
            ('min position', 0),  # Store postions etc. to avoid recalculating.
            ('max position', len(data)),
            ('max deflection', data.max()),
            ('min deflection', data.min()),
            ]:
            if key not in self.info:
                self.info[key] = value
        for key,value in [
            ('position range',
             self.info['max position'] - self.info['min position']),
            ('deflection range',
             self.info['max deflection'] - self.info['min deflection']),
            ]:
            if key not in self.info:
                self.info[key] = value

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
        if self.info['force zero non-contact slope'] == True:
            params = params[:-1]
        return params

    def fit(self, *args, **kwargs):
        """Fit the model to the data.

        Notes
        -----
        We change the `epsfcn` default from :func:`scipy.optimize.leastsq`'s
        `0` to `1e-3`, so the initial Jacobian estimate takes larger steps,
        which helps avoid being trapped in noise-generated local minima.
        """
        self.info['guessed contact slope'] = None
        if 'epsfcn' not in kwargs:
            kwargs['epsfcn'] = 1e-3  # take big steps to estimate the Jacobian
        params = super(SurfacePositionModel, self).fit(*args, **kwargs)
        params[2] = abs(params[2])
        if self.info['force zero non-contact slope'] == True:
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


class SurfaceContactCommand (ColumnAddingCommand):
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
            name='zero surface contact point',
            columns=[
                ('distance column', 'z piezo (m)', """
Name of the column to use as the surface position input.
""".strip()),
                ('deflection column', 'deflection (m)', """
Name of the column to use as the deflection input.
""".strip()),
                ],
            new_columns=[
                ('output distance column', 'surface distance', """
Name of the column (without units) to use as the surface position output.
""".strip()),
                ('output deflection column', 'surface deflection', """
Name of the column (without units) to use as the deflection output.
""".strip()),
                ],
            arguments=[
                Argument(name='ignore index', type='int', default=None,
                         help="""
Ignore the residual from the non-contact region before the indexed
point (for the `wtk` algorithm).
""".strip()),
                Argument(name='ignore after last peak info name',
                         type='string', default=None,
                         help="""
As an alternative to 'ignore index', ignore after the last peak in the
peak list stored in the `.info` dictionary.
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
        self._add_to_command_stack(params)
        params = self.__setup_params(hooke=hooke, params=params)
        block = self._block(hooke=hooke, params=params)
        dist_data = self._get_column(hooke=hooke, params=params,
                                     column_name='distance column')
        def_data = self._get_column(hooke=hooke, params=params,
                                    column_name='deflection column')
        i,def_offset,ps = self.find_contact_point(
            params, dist_data, def_data, outqueue)
        dist_offset = dist_data[i]
        block.info[params['distance info name']] = dist_offset
        block.info[params['deflection info name']] = def_offset
        block.info[params['fit parameters info name']] = ps
        self._set_column(hooke=hooke, params=params,
                         column_name='output distance column',
                         values=dist_data - dist_offset)
        self._set_column(hooke=hooke, params=params,
                         column_name='output deflection column',
                         values=def_data - def_offset)

    def __setup_params(self, hooke, params):
        name,dist_unit = split_data_label(params['distance column'])
        name,def_unit = split_data_label(params['deflection column'])
        params['output distance column'] = join_data_label(
            params['output distance column'], dist_unit)
        params['output deflection column'] = join_data_label(
            params['output deflection column'], def_unit)
        params['distance info name'] = join_data_label(
            params['distance info name'], dist_unit)
        params['deflection info name'] = join_data_label(
            params['deflection info name'], def_unit)
        return params

    def find_contact_point(self, params, z_data, d_data, outqueue=None):
        """Railyard for the `find_contact_point_*` family.

        Uses the `surface contact point algorithm` configuration
        setting to call the appropriate backend algorithm.
        """
        fn = getattr(self, 'find_contact_point_%s'
                     % self.plugin.config['surface contact point algorithm'])
        return fn(params, z_data, d_data, outqueue)

    def find_contact_point_fmms(self, params, z_data, d_data, outqueue=None):
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
        if params['curve'].info['filetype'] == 'picoforce':
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

    def find_contact_point_ms(self, params, z_data, d_data, outqueue=None):
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

    def find_contact_point_wtk(self, params, z_data, d_data, outqueue=None):
        """Algorithm by W. Trevor King.

        Notes
        -----
        Uses :class:`SurfacePositionModel` internally.
        """
        reverse = z_data[0] > z_data[-1]
        if reverse == True:    # approaching, contact region on the right
            d_data = d_data[::-1]
        s = SurfacePositionModel(d_data, info={
                'force zero non-contact slope':True},
                                 rescale=True)
        ignore_index = None
        if params['ignore index'] != None:
            ignore_index = params['ignore index']
        elif params['ignore after last peak info name'] != None:
            peaks = z_data.info[params['ignore after last peak info name']]
            if not len(peaks) > 0:
                raise Failure('Need at least one peak in %s, not %s'
                              % (params['ignore after last peak info name'],
                                 peaks))
            ignore_index = peaks[-1].post_index()
        if ignore_index != None:
            s.info['ignore non-contact before index'] = ignore_index
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


class ForceCommand (ColumnAddingCommand):
    """Convert a deflection column from meters to newtons.
    """
    def __init__(self, plugin):
        super(ForceCommand, self).__init__(
            name='convert distance to force',
            columns=[
                ('deflection column', 'surface deflection (m)', """
Name of the column to use as the deflection input.
""".strip()),
                ],
            new_columns=[
                ('output deflection column', 'deflection', """
Name of the column (without units) to use as the deflection output.
""".strip()),
                ],
            arguments=[
                Argument(name='spring constant info name', type='string',
                         default='spring constant (N/m)',
                         help="""
Name of the spring constant in the `.info` dictionary.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        self._add_to_command_stack(params)
        params = self.__setup_params(hooke=hooke, params=params)
        def_data = self._get_column(hooke=hooke, params=params,
                                    column_name='deflection column')
        out = def_data * def_data.info[params['spring constant info name']]
        self._set_column(hooke=hooke, params=params,
                         column_name='output deflection column',
                         values=out)

    def __setup_params(self, hooke, params):
        name,in_unit = split_data_label(params['deflection column'])
        out_unit = 'N'  # HACK: extract target units from k_unit.
        params['output deflection column'] = join_data_label(
            params['output deflection column'], out_unit)
        name,k_unit = split_data_label(params['spring constant info name'])
        expected_k_unit = '%s/%s' % (out_unit, in_unit)
        if k_unit != expected_k_unit:
            raise Failure('Cannot convert from %s to %s with %s'
                          % (params['deflection column'],
                             params['output deflection column'],
                             params['spring constant info name']))
        return params


class CantileverAdjustedExtensionCommand (ColumnAddingCommand):
    """Remove cantilever extension from a total extension column.

    If `distance column` and `deflection column` have the same units
    (e.g. `z piezo (m)` and `deflection (m)`), `spring constant info
    name` is ignored and a deflection/distance conversion factor of
    one is used.
    """
    def __init__(self, plugin):
        super(CantileverAdjustedExtensionCommand, self).__init__(
            name='remove cantilever from extension',
            columns=[
                ('distance column', 'surface distance (m)', """
Name of the column to use as the surface position input.
""".strip()),
                ('deflection column', 'deflection (N)', """
Name of the column to use as the deflection input.
""".strip()),
                ],
            new_columns=[
                ('output distance column', 'cantilever adjusted extension', """
Name of the column (without units) to use as the surface position output.
""".strip()),
                ],
            arguments=[
                Argument(name='spring constant info name', type='string',
                         default='spring constant (N/m)',
                         help="""
Name of the spring constant in the `.info` dictionary.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        self._add_to_command_stack(params)
        params = self.__setup_params(hooke=hooke, params=params)
        def_data = self._get_column(hooke=hooke, params=params,
                                    column_name='deflection column')
        dist_data = self._get_column(hooke=hooke, params=params,
                                     column_name='distance column')
        if params['spring constant info name'] == None:
            k = 1.0  # distance and deflection in the same units
        else:
            k = def_data.info[params['spring constant info name']]
        self._set_column(hooke=hooke, params=params,
                         column_name='output distance column',
                         values=dist_data - def_data / k)

    def __setup_params(self, hooke, params):
        name,dist_unit = split_data_label(params['distance column'])
        name,def_unit = split_data_label(params['deflection column'])
        params['output distance column'] = join_data_label(
            params['output distance column'], dist_unit)
        if dist_unit == def_unit:
            params['spring constant info name'] == None
        else:
            name,k_unit = split_data_label(params['spring constant info name'])
            expected_k_unit = '%s/%s' % (def_unit, dist_unit)
            if k_unit != expected_k_unit:
                raise Failure('Cannot convert from %s to %s with %s'
                              % (params['deflection column'],
                                 params['output distance column'],
                                 params['spring constant info name']))
        return params


class FlattenCommand (ColumnAddingCommand):
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
            name='polynomial flatten',
            columns=[
                ('distance column', 'surface distance (m)', """
Name of the column to use as the surface position input.
""".strip()),
                ('deflection column', 'deflection (N)', """
Name of the column to use as the deflection input.
""".strip()),
                ],
            new_columns=[
                ('output deflection column', 'flattened deflection', """
Name of the column (without units) to use as the deflection output.
""".strip()),
                ],
            arguments=[
                Argument(name='degree', type='int',
                         default=1,
                         help="""
Order of the polynomial used for flattening.  Using values greater
than one usually doesn't help and can give artifacts.  However, it
could be useful too.  (TODO: Back this up with some theory...)
""".strip()),
                Argument(name='fit info name', type='string',
                         default='flatten fit',
                         help="""
Name of the flattening information in the `.info` dictionary.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        self._add_to_command_stack(params)
        params = self.__setup_params(hooke=hooke, params=params)
        block = self._block(hooke=hooke, params=params)
        dist_data = self._get_column(hooke=hooke, params=params,
                                     column_name='distance column')
        def_data = self._get_column(hooke=hooke, params=params,
                                    column_name='deflection column')
        degree = params['degree']
        mask = dist_data > 0
        indices = numpy.argwhere(mask)
        if len(indices) == 0:
            raise Failure('no positive distance values in %s'
                          % params['distance column'])
        dist_nc = dist_data[indices].flatten()
        def_nc = def_data[indices].flatten()

        try:
            poly_values = scipy.polyfit(dist_nc, def_nc, degree)
            def_nc_fit = scipy.polyval(poly_values, dist_nc)
        except Exception, e:
            raise Failure('failed to flatten with a degree %d polynomial: %s'
                          % (degree, e))
        error = numpy.sqrt((def_nc_fit-def_nc)**2).sum() / len(def_nc)
        block.info[params['fit info name']] = {
            'error':error,
            'degree':degree,
            'polynomial values':poly_values,
            }
        out = (def_data
               - numpy.invert(mask)*scipy.polyval(poly_values[-1:], dist_data)
               - mask*scipy.polyval(poly_values, dist_data))
        self._set_column(hooke=hooke, params=params,
                         column_name='output deflection column',
                         values=out)

    def __setup_params(self, hooke, params):
        d_name,d_unit = split_data_label(params['deflection column'])
        params['output deflection column'] = join_data_label(
            params['output deflection column'], d_unit)
        return params
