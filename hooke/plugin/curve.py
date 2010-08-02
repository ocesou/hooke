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

"""The ``curve`` module provides :class:`CurvePlugin` and several
associated :class:`hooke.command.Command`\s for handling
:mod:`hooke.curve` classes.
"""

import numpy

from ..command import Command, Argument, Failure
from ..curve import Data
from ..plugin import Builtin
from ..plugin.playlist import current_playlist_callback
from ..util.calculus import derivative
from ..util.fft import unitary_avg_power_spectrum


class CurvePlugin (Builtin):
    def __init__(self):
        super(CurvePlugin, self).__init__(name='curve')
        self._commands = [
            GetCommand(self), InfoCommand(self), ExportCommand(self),
            DifferenceCommand(self), DerivativeCommand(self),
            PowerSpectrumCommand(self)]


# Define common or complicated arguments

def current_curve_callback(hooke, command, argument, value):
    if value != None:
        return value
    playlist = current_playlist_callback(hooke, command, argument, value)
    curve = playlist.current()
    if curve == None:
        raise Failure('No curves in %s' % playlist)
    return curve

CurveArgument = Argument(
    name='curve', type='curve', callback=current_curve_callback,
    help="""
:class:`hooke.curve.Curve` to act on.  Defaults to the current curve
of the current playlist.
""".strip())


# Define commands

class GetCommand (Command):
    """Return a :class:`hooke.curve.Curve`.
    """
    def __init__(self, plugin):
        super(GetCommand, self).__init__(
            name='get curve', arguments=[CurveArgument],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        outqueue.put(params['curve'])

class InfoCommand (Command):
    """Get selected information about a :class:`hooke.curve.Curve`.
    """
    def __init__(self, plugin):
        args = [
            CurveArgument,                    
            Argument(name='all', type='bool', default=False, count=1,
                     help='Get all curve information.'),
            ]
        self.fields = ['name', 'path', 'experiment', 'driver', 'filetype', 'note',
                       'blocks', 'block sizes']
        for field in self.fields:
            args.append(Argument(
                    name=field, type='bool', default=False, count=1,
                    help='Get curve %s' % field))
        super(InfoCommand, self).__init__(
            name='curve info', arguments=args,
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        fields = {}
        for key in self.fields:
            fields[key] = params[key]
        if reduce(lambda x,y: x and y, fields.values()) == False:
            params['all'] = True # No specific fields set, default to 'all'
        if params['all'] == True:
            for key in self.fields:
                fields[key] = True
        lines = []
        for key in self.fields:
            if fields[key] == True:
                get = getattr(self, '_get_%s' % key.replace(' ', '_'))
                lines.append('%s: %s' % (key, get(params['curve'])))
        outqueue.put('\n'.join(lines))

    def _get_name(self, curve):
        return curve.name

    def _get_path(self, curve):
        return curve.path

    def _get_experiment(self, curve):
        return curve.info.get('experiment', None)

    def _get_driver(self, curve):
        return curve.driver

    def _get_filetype(self, curve):
        return curve.info.get('filetype', None)

    def _get_note(self, curve):
        return curve.info.get('note', None)
                              
    def _get_blocks(self, curve):
        return len(curve.data)

    def _get_block_sizes(self, curve):
        return [block.shape for block in curve.data]

class ExportCommand (Command):
    """Export a :class:`hooke.curve.Curve` data block as TAB-delimeted
    ASCII text.

    A "#" prefixed header will optionally appear at the beginning of
    the file naming the columns.
    """
    def __init__(self, plugin):
        super(ExportCommand, self).__init__(
            name='export block',
            arguments=[
                CurveArgument,
                Argument(name='block', aliases=['set'], type='int', default=0,
                         help="""
Data block to save.  For an approach/retract force curve, `0` selects
the approaching curve and `1` selects the retracting curve.
""".strip()),
                Argument(name='output', type='file', default='curve.dat',
                         help="""
File name for the output data.  Defaults to 'curve.dat'
""".strip()),
                Argument(name='header', type='bool', default=True,
                         help="""
True if you want the column-naming header line.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        data = params['curve'].data[int(params['block'])] # HACK, int() should be handled by ui

        f = open(params['output'], 'w')
        if params['header'] == True:
            f.write('# %s \n' % ('\t'.join(data.info['columns'])))
        numpy.savetxt(f, data, delimiter='\t')
        f.close()

class DifferenceCommand (Command):
    """Calculate the derivative (actually, the discrete differentiation)
    of a curve data block.

    See :func:`hooke.util.calculus.derivative` for implementation
    details.
    """
    def __init__(self, plugin):
        super(DifferenceCommand, self).__init__(
            name='block difference',
            arguments=[
                CurveArgument,
                Argument(name='block one', aliases=['set one'], type='int',
                         default=1,
                         help="""
Block A in A-B.  For an approach/retract force curve, `0` selects the
approaching curve and `1` selects the retracting curve.
""".strip()),
                Argument(name='block two', aliases=['set two'], type='int',
                         default=0,
                         help='Block B in A-B.'),
                Argument(name='x column', type='int', default=0,
                         help="""
Column of data block to differentiate with respect to.
""".strip()),
                Argument(name='f column', type='int', default=1,
                         help="""
Column of data block to differentiate.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        a = params['curve'].data[params['block one']]
        b = params['curve'].data[params['block two']]
        assert a[:,params['x column']] == b[:,params['x column']]
        out = Data((a.shape[0],2), dtype=a.dtype)
        out[:,0] = a[:,params['x column']]
        out[:,1] = a[:,params['f column']] - b[:,params['f column']]
        outqueue.put(out)

class DerivativeCommand (Command):
    """Calculate the difference between two blocks of data.
    """
    def __init__(self, plugin):
        super(DerivativeCommand, self).__init__(
            name='block derivative',
            arguments=[
                CurveArgument,
                Argument(name='block', aliases=['set'], type='int', default=0,
                         help="""
Data block to differentiate.  For an approach/retract force curve, `0`
selects the approaching curve and `1` selects the retracting curve.
""".strip()),
                Argument(name='x column', type='int', default=0,
                         help="""
Column of data block to differentiate with respect to.
""".strip()),
                Argument(name='f column', type='int', default=1,
                         help="""
Column of data block to differentiate.
""".strip()),
                Argument(name='weights', type='dict', default={-1:-0.5, 1:0.5},
                         help="""
Weighting scheme dictionary for finite differencing.  Defaults to
central differencing.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        data = params['curve'].data[params['block']]
        outqueue.put(derivative(
                block, x_col=params['x column'], f_col=params['f column'],
                weights=params['weights']))

class PowerSpectrumCommand (Command):
    """Calculate the power spectrum of a data block.
    """
    def __init__(self, plugin):
        super(PowerSpectrumCommand, self).__init__(
            name='block power spectrum',
            arguments=[
                CurveArgument,
                Argument(name='block', aliases=['set'], type='int', default=0,
                         help="""
Data block to act on.  For an approach/retract force curve, `0`
selects the approaching curve and `1` selects the retracting curve.
""".strip()),
                Argument(name='f column', type='int', default=1,
                         help="""
Column of data block to differentiate with respect to.
""".strip()),
                Argument(name='freq', type='float', default=1.0,
                         help="""
Sampling frequency.
""".strip()),
                Argument(name='chunk size', type='int', default=2048,
                         help="""
Number of samples per chunk.  Use a power of two.
""".strip()),
                Argument(name='overlap', type='bool', default=False,
                         help="""
If `True`, each chunk overlaps the previous chunk by half its length.
Otherwise, the chunks are end-to-end, and not overlapping.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        data = params['curve'].data[params['block']]
        outqueue.put(unitary_avg_power_spectrum(
                data[:,params['f column']], freq=params['freq'],
                chunk_size=params['chunk size'],
                overlap=params['overlap']))
