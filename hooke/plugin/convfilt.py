# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2010 Alberto Gomez-Casado
#                         Fabrizio Benedetti
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

"""The ``convfilt`` module provides :class:`ConvFiltPlugin` and
for convolution-based filtering of :mod:`hooke.curve.Curve`\s.

See Also
--------
:mod:`~hooke.plugin.flatfilt` for a collection of additional filters.

:class:`ConfFiltPlugin` was broken out of
:class:`~hooke.plugin.flatfilt` to separate its large number of
configuration settings.
"""

import copy
from multiprocessing import Queue

import numpy

from ..command import Command, Argument, Success, Failure
from ..config import Setting
from ..util.fit import PoorFit
from ..util.peak import find_peaks, find_peaks_arguments, Peak, _kwargs
from . import Plugin, argument_to_setting
from .curve import CurveArgument
from .playlist import FilterCommand


class ConvFiltPlugin (Plugin):
    """Convolution-based peak recognition and filtering.
    """
    def __init__(self):
        super(ConvFiltPlugin, self).__init__(name='convfilt')
        self._arguments = [ # for Command initialization
            Argument('convolution', type='float', count=-1,
                     default=[11.0]+[-1.0]*11, help="""
Convolution vector roughly matching post-peak cantilever rebound.
This should roughly match the shape of the feature you're looking for.
""".strip()), # TODO: per-curve convolution vector + interpolation, to
              # take advantage of the known spring constant.
            Argument('blind window', type='float', default=20e-9, help="""
Meters after the contact point where we do not count peaks to avoid
non-specific surface interaction.
""".strip()),
            Argument('min peaks', type='int', default=5, help="""
Minimum number of peaks for curve acceptance.
""".strip()),
            ] + copy.deepcopy(find_peaks_arguments)
        # Set convolution-specific defaults for the fit_peak_arguments.
        for key,value in [('cut side', 'positive'),
                          ('stable', 0.005),
                          ('max cut', 0.2),
                          ('min deviations', 5.0),
                          ('min points', 1),
                          ('see double', 10), # TODO: points vs. meters. 10e-9),
                          ]:
            argument = [a for a in self._arguments if a.name == key][0]
            argument.default = value
        self._settings = [
            Setting(section=self.setting_section, help=self.__doc__)]
        for argument in self._arguments:
            self._settings.append(argument_to_setting(
                    self.setting_section, argument))
            argument.default = None # if argument isn't given, use the config.
        self._commands = [ConvolutionPeaksCommand(self),
                          ConvolutionFilterCommand(self)]

    def dependencies(self):
        return ['vclamp']

    def default_settings(self):
        return self._settings


class ConvolutionPeaksCommand (Command):
    """Detect peaks in velocity clamp data with a convolution.

    Notes
    -----
    A simplified version of Kasas' filter [#kasas2000].
    For any given retracting curve:

    1) The contact point is found.
    2) The off-surface data is convolved (using :func:`numpy.convolve`)
      with a vector that encodes the approximate shape of the target
      feature.
    3) Peaks in the convolved curve are extracted with
      :func:`~hooke.plugins.peak.find_peaks`.

    The convolution algorithm, with appropriate thresholds, usually
    recognizes peaks well more than 95% of the time.
      
    .. [#kasas2000] S. Kasas, B.M. Riederer, S. Catsicas, B. Cappella,
      G. Dietler.
      "Fuzzy logic algorithm to extract specific interaction forces
      from atomic force microscopy data"
      Rev. Sci. Instrum., 2000.
      doi: `10.1063/1.1150583 <http://dx.doi.org/10.1063/1.1150583>`_
    """
    def __init__(self, plugin):
        config_arguments = [a for a in plugin._arguments
                            if a.name != 'min peaks']
        # Drop min peaks, since we're not filtering with this
        # function, just detecting peaks.
        super(ConvolutionPeaksCommand, self).__init__(
            name='convolution peaks',
            arguments=[CurveArgument] + config_arguments,
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        z_data,d_data,params = self._setup(hooke, params)
        start_index = 0
        while z_data[start_index] < params['bind window']:
            start_index += 1
        conv = numpy.convolve(d_data[start_index:], params['convolution'],
                              mode='valid')
        peaks = find_peaks(conv, **_kwargs(params, find_peaks_arguments,
                                            argument_input_keys=True))
        for peak in peaks:
            peak.name = 'convolution of %s with %s' \
                % (params['deflection column name'], params['convolution'])
            peak.index += start_index
        outqueue.put(peaks)

    def _setup(self, hooke, params):
        """Setup `params` from config and return the z piezo and
        deflection arrays.
        """
        curve = params['curve']
        data = None
        for block in curve.data:
            if block.info['name'].startswith('retract'):
                data = block
                break
        if data == None:
            raise Failure('No retraction blocks in %s.' % curve)
        z_data = data[:,data.info['columns'].index('surface distance (m)')]
        if 'flattened deflection (N)' in data.info['columns']:
            params['deflection column name'] = 'flattened deflection (N)'
        else:
            params['deflection column name'] = 'deflection (N)'
        d_data = data[:,data.info['columns'].index(
                params['deflection column name'])]
        for key,value in params.items():
            if value == None: # Use configured default value.
                params[key] = self.plugin.config[key]
        return z_data,d_data,params


class ConvolutionFilterCommand (FilterCommand):
    u"""Create a subset playlist of curves with enough convolution peaks.

    Notes
    -----
    This filter can reduce a dataset like the one in [#brucale2009] to
    analyze by hand by about 80-90% (depending on the overall
    cleanliness of the data set). Thousands of curves can be
    automatically filtered this way in a few minutes on a standard PC,
    but the algorithm could still be optimized.

    .. [#brucale2009] M. Brucale, M. Sandal, S. Di Maio, A. Rampioni,
      I. Tessari, L. Tosatto, M. Bisaglia, L. Bubacco, B. Samorì.
      "Pathogenic mutations shift the equilibria of
      α-Synuclein single molecules towards structured
      conformers."
      Chembiochem., 2009.
      doi: `10.1002/cbic.200800581 <http://dx.doi.org/10.1002/cbic.200800581>`_

    See Also
    --------
    ConvolutionCommand : Underlying convolution-based peak detection.
    """
    def __init__(self, plugin):
        super(ConvolutionFilterCommand, self).__init__(
            plugin, name='convolution filter playlist')
        self.arguments.extend(plugin._arguments)

    def filter(self, curve, hooke, inqueue, outqueue, params):
        params['curve'] = curve
        inq = Queue()
        outq = Queue()
        conv_command = [c for c in self.hooke.commands
                        if c.name=='convolution peaks'][0]
        conv_command.run(hooke, inq, outq, **params)
        peaks = outq.get()
        if isinstance(peaks, UncaughtException) \
                and isinstance(peaks.exception, PoorFit):
            return False
        if not (isinstance(peaks, list) and (len(peaks) == 0
                                             or isinstance(peaks[0], Peak))):
            raise Failure('Expected a list of Peaks, not %s' % peaks)
        ret = outq.get()
        if not isinstance(ret, Success):
            raise ret
        if params['min peaks'] == None: # Use configured default value.
            params['min peaks'] = self.plugin.config['min peaks']
        return len(peaks) >= params['min peaks']
