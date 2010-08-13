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

"""The ``flatfilt`` module provides :class:`FlatFiltPlugin` and
several associated :class:`~hooke.command.Command`\s for removing flat
(featureless) :mod:`~hooke.curve.Curve`\s from
:class:`~hooke.playlist.Playlist`\s.

See Also
--------
:mod:`~hooke.plugin.convfilt` for a convolution-based filter for
:class:`~hooke.experiment.VelocityClamp` experiments.
"""

import copy
from Queue import Queue

from numpy import absolute, diff
from scipy.signal.signaltools import medfilt

from ..command import Argument, Success, Failure, UncaughtException
from ..config import Setting
from ..curve import Data
from ..experiment import VelocityClamp
from ..util.fit import PoorFit
from ..util.peak import (find_peaks, peaks_to_mask,
                         find_peaks_arguments, Peak, _kwargs)
from ..util.si import join_data_label, split_data_label
from . import Plugin, argument_to_setting
from .curve import ColumnAddingCommand
from .playlist import FilterCommand


class FlatFiltPlugin (Plugin):
    """Standard-devitiation-based peak recognition and filtering.
    """
    def __init__(self):
        super(FlatFiltPlugin, self).__init__(name='flatfilt')
        self._arguments = [ # For Command initialization
            Argument('median window', type='int', default=7, help="""
Median window filter size (in points).
""".strip()),
            Argument('blind window', type='float', default=20e-9, help="""
Meters after the contact point where we do not count peaks to avoid
non-specific surface interaction.
""".strip()),
            Argument('min peaks', type='int', default=4, help="""
Minimum number of peaks for curve acceptance.
""".strip()),
            ] + copy.deepcopy(find_peaks_arguments)
        # Set flat-filter-specific defaults for the fit_peak_arguments.
        for key,value in [('cut side', 'both'),
                          ('stable', 0.005),
                          ('max cut', 0.2),
                          ('min deviations', 9.0),
                          ('min points', 4),
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
        self._commands = [FlatPeaksCommand(self)]
        # append FlatFilterCommand so it can steal arguments from
        # FlatPeaksCommand.
        self._commands.append(FlatFilterCommand(self))

    def dependencies(self):
        return ['vclamp']

    def default_settings(self):
        return self._settings


class FlatPeaksCommand (ColumnAddingCommand):
    """Detect peaks in velocity clamp data using noise statistics.

    Notes
    -----
    Noise analysis on the retraction curve:

    1) A median window filter (using
      :func:`scipy.signal.signaltools.medfilt`) smooths the
      deflection.
    2) The deflection derivative is calculated (using
      :func:`numpy.diff` which uses forward differencing).
    3) Peaks in the derivative curve are extracted with
      :func:`~hooke.plugins.peak.find_peaks`.

    The algorithm was originally Francesco Musiani's idea.
    """
    def __init__(self, plugin):
        plugin_arguments = [a for a in plugin._arguments
                            if a.name != 'min peaks']
        # Drop min peaks, since we're not filtering with this
        # function, just detecting peaks.
        super(FlatPeaksCommand, self).__init__(
            name='flat filter peaks',
            columns=[
                ('distance column', 'surface distance (m)', """
Name of the column to use as the surface position input.
""".strip()),
                ('deflection column', 'surface deflection (m)', """
Name of the column to use as the deflection input.
""".strip()),
                ],
            new_columns=[
                ('output peak column', 'flat filter peaks', """
Name of the column (without units) to use as the peak output.
""".strip()),
                ],
            arguments=[
                Argument(name='peak info name', type='string',
                         default='flat filter peaks',
                         help="""
Name (without units) for storing the list of peaks in the `.info`
dictionary.
""".strip()),
                ] + plugin_arguments,
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        self._add_to_command_stack(params)
        params = self.__setup_params(hooke=hooke, params=params)
        block = self._block(hooke=hooke, params=params)
        dist_data = self._get_column(hooke=hooke, params=params,
                                     column_name='distance column')
        def_data = self._get_column(hooke=hooke, params=params,
                                     column_name='deflection column')
        start_index = absolute(dist_data-params['blind window']).argmin()
        median = medfilt(def_data[start_index:], params['median window'])
        deriv = diff(median)
        peaks = find_peaks(deriv, **_kwargs(params, find_peaks_arguments,
                                            argument_input_keys=True))
        for i,peak in enumerate(peaks):
            peak.name = self._peak_name(params, i)
            peak.index += start_index
        block.info[params['peak info name']] = peaks

        self._set_column(hooke=hooke, params=params,
                         column_name='output peak column',
                         values=peaks_to_mask(def_data, peaks) * def_data)
        outqueue.put(peaks)

    def __setup_params(self, hooke, params):
        """Setup `params` from config and return the z piezo and
        deflection arrays.
        """
        curve = self._curve(hooke=hooke, params=params)
        if curve.info['experiment'] != VelocityClamp:
            raise Failure('%s operates on VelocityClamp experiments, not %s'
                          % (self.name, curve.info['experiment']))
        for key,value in params.items():
            if value == None and key in self.plugin.config:
                # Use configured default value.
                params[key] = self.plugin.config[key]
        # TODO: convert 'see double' from nm to points
        name,def_unit = split_data_label(params['deflection column'])
        params['output peak column'] = join_data_label(
            params['output peak column'], def_unit)
        params['peak info name'] = join_data_label(
            params['peak info name'], def_unit)
        return params

    def _peak_name(self, params, index):
        d_name,d_unit = split_data_label(params['deflection column'])
        return 'flat filter peak %d of %s' % (index, d_name)


class FlatFilterCommand (FilterCommand):
    u"""Create a subset playlist of curves with enough flat peaks.

    Notes
    -----
    This type of filter is of course very raw, and requires relatively
    conservative settings to safely avoid false negatives (that is, to
    avoid discarding interesting curves).  Using it on the protein
    unfolding experiments described by Sandal [#sandal2008] it has
    been found to reduce the data set to analyze by hand by 60-80%.

    .. [#sandal2008] M. Sandal, F. Valle, I. Tessari, S. Mammi, E. Bergantino,
      F. Musiani, M. Brucale, L. Bubacco, B. Samorì.
      "Conformational equilibria in monomeric α-Synuclein at the
      single molecule level."
      PLOS Biology, 2009.
      doi: `10.1371/journal.pbio.0060006 <http://dx.doi.org/10.1371/journal.pbio.0060006>`_

    See Also
    --------
    FlatPeaksCommand : Underlying flat-based peak detection.
    """
    def __init__(self, plugin):
        flat_peaks = [c for c in plugin._commands
                      if c.name == 'flat filter peaks'][0]
        flat_peaks_arg_names = [a.name for a in flat_peaks.arguments]
        plugin_arguments = [a for a in plugin._arguments
                            if a.name not in flat_peaks_arg_names]
        arguments = flat_peaks.arguments + plugin_arguments
        super(FlatFilterCommand, self).__init__(
            plugin, name='flat filter playlist')
        self.arguments.extend(arguments)

    def filter(self, curve, hooke, inqueue, outqueue, params):
        params['curve'] = curve
        inq = Queue()
        outq = Queue()
        filt_command = [c for c in hooke.commands
                        if c.name=='flat filter peaks'][0]
        filt_command.run(hooke, inq, outq, **params)
        peaks = outq.get()
        if isinstance(peaks, UncaughtException) \
                and isinstance(peaks.exception, PoorFit):
            return False
        if not (isinstance(peaks, list) and (len(peaks) == 0
                                             or isinstance(peaks[0], Peak))):
            raise Failure('Expected a list of Peaks, not %s: %s'
                          % (type(peaks), peaks))
        ret = outq.get()
        if not isinstance(ret, Success):
            raise ret
        if params['min peaks'] == None: # Use configured default value.
            params['min peaks'] = self.plugin.config['min peaks']
        return len(peaks) >= int(params['min peaks'])
