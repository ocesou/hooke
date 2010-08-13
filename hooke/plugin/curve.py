# Copyright (C) 2008-2010 Alberto Gomez-Kasai
#                         Fabiano's Benedetti
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

"""The ``curve`` module provides :class:`CurvePlugin` and several
associated :class:`hooke.command.Command`\s for handling
:mod:`hooke.curve` classes.
"""

import copy

import numpy

from ..command import Command, Argument, Failure
from ..curve import Data
from ..engine import CommandMessage
from ..util.calculus import derivative
from ..util.fft import unitary_avg_power_spectrum
from ..util.si import ppSI, join_data_label, split_data_label
from . import Builtin
from .playlist import current_playlist_callback


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

def _name_argument(name, default, help):
    """TODO
    """
    return Argument(name=name, type='string', default=default, help=help)

def block_argument(*args, **kwargs):
    """TODO
    """
    return _name_argument(*args, **kwargs)

def column_argument(*args, **kwargs):
    """TODO
    """
    return _name_argument(*args, **kwargs)


# Define useful command subclasses

class CurveCommand (Command):
    """A :class:`~hooke.command.Command` operating on a
    :class:`~hooke.curve.Curve`.
    """
    def __init__(self, **kwargs):
        if 'arguments' in kwargs:
            kwargs['arguments'].insert(0, CurveArgument)
        else:
            kwargs['arguments'] = [CurveArgument]
        super(CurveCommand, self).__init__(**kwargs)

    def _curve(self, hooke, params):
        """Get the selected curve.

        Notes
        -----
        `hooke` is intended to attach the selected curve to the local
        playlist; the returned curve should not be effected by the
        state of `hooke`.  This is important for reliable
        :class:`~hooke.command_stack.CommandStack`\s.
        """
        # HACK? rely on params['curve'] being bound to the local hooke
        # playlist (i.e. not a copy, as you would get by passing a
        # curve through the queue).  Ugh.  Stupid queues.  As an
        # alternative, we could pass lookup information through the
        # queue...
        return params['curve']

    def _add_to_command_stack(self, params):
        """Store the command name and current `params` values in the
        curve's `.command_stack`.

        If this would duplicate the command currently on top of the
        stack, no action is taken.  Call early on, or watch out for
        repeated param processing.

        Recommended practice is to *not* lock in argument values that
        are loaded from the plugin's :attr:`.config`.

        Notes
        -----
        Perhaps we should subclass :meth:`_run` and use :func:`super`,
        or embed this in :meth:`run` to avoid subclasses calling this
        method explicitly, with all the tedium and brittality that
        implies.  On the other hand, the current implemtnation allows
        CurveCommands that don't effect the curve itself
        (e.g. :class:`GetCommand`) to avoid adding themselves to the
        stack entirely.
        """
        curve = self._curve(hooke=None, params=params)
        if (len(curve.command_stack) > 0
            and curve.command_stack[-1].command == self.name
            and curve.command_stack[-1].arguments == params):
            pass  # no need to place duplicate calls on the stack.
        else:
            curve.command_stack.append(CommandMessage(
                    self.name, params))


class BlockCommand (CurveCommand):
    """A :class:`CurveCommand` operating on a :class:`~hooke.curve.Data` block.
    """
    def __init__(self, blocks=None, **kwargs):
        if blocks == None:
            blocks = [('block', None, 'Name of the data block to act on.')]
        block_args = []
        for name,default,help in blocks:
            block_args.append(block_argument(name, default, help))
        self._block_arguments = block_args
        if 'arguments' not in kwargs:
            kwargs['arguments'] = []
        kwargs['arguments'] = block_args + kwargs['arguments']
        super(BlockCommand, self).__init__(**kwargs)

    def _block_names(self, hooke, params):
        curve = self._curve(hooke, params)
        return [b.info['name'] for b in curve.data]

    def _block_index(self, hooke, params, name=None):
        if name == None:
            name = self._block_arguments[0].name
        block_name = params[name]
        if block_name == None:
            curve = self._curve(hooke=hooke, params=params)
            if len(curve.data) == 0:
                raise Failure('no blocks in %s' % curve)
            block_name = curve.data[0].info['name']
        names = self._block_names(hooke=hooke, params=params)
        try:
            return names.index(block_name)
        except ValueError, e:
            curve = self._curve(hooke, params)
            raise Failure('no block named %s in %s (%s): %s'
                          % (block_name, curve, names, e))

    def _block(self, hooke, params, name=None):
        # HACK? rely on params['block'] being bound to the local hooke
        # playlist (i.e. not a copy, as you would get by passing a
        # block through the queue).  Ugh.  Stupid queues.  As an
        # alternative, we could pass lookup information through the
        # queue...
        curve = self._curve(hooke, params)
        index = self._block_index(hooke, params, name)
        return curve.data[index]


class ColumnAccessCommand (BlockCommand):
    """A :class:`BlockCommand` accessing a :class:`~hooke.curve.Data`
    block column.
    """
    def __init__(self, columns=None, **kwargs):
        if columns == None:
            columns = [('column', None, 'Name of the data column to act on.')]
        column_args = []
        for name,default,help in columns:
            column_args.append(column_argument(name, default, help))
        self._column_arguments = column_args
        if 'arguments' not in kwargs:
            kwargs['arguments'] = []
        kwargs['arguments'] = column_args + kwargs['arguments']
        super(ColumnAccessCommand, self).__init__(**kwargs)

    def _get_column(self, hooke, params, block_name=None, column_name=None):
        if column_name == None:
            column_name = self._column_arguments[0].name
        column_name = params[column_name]
        block = self._block(hooke, params, block_name)
        columns = block.info['columns']
        try:
            column_index = columns.index(column_name)
        except ValueError, e:
            raise Failure('%s not in %s (%s): %s'
                          % (column_name, block.info['name'], columns, e))
        return block[:,column_index]


class ColumnAddingCommand (ColumnAccessCommand):
    """A :class:`ColumnAccessCommand` that also adds columns.
    """
    def __init__(self, new_columns=None, **kwargs):
        if new_columns == None:
            new_columns = []
        column_args = []
        for name,default,help in new_columns:
            column_args.append(column_argument(name, default, help))
        self._new_column_arguments = column_args
        if 'arguments' not in kwargs:
            kwargs['arguments'] = []
        kwargs['arguments'] = column_args + kwargs['arguments']
        super(ColumnAddingCommand, self).__init__(**kwargs)

    def _get_column(self, hooke, params, block_name=None, column_name=None):
        if column_name == None and len(self._column_arguments) == 0:
            column_name = self._new_column_arguments[0].name
        return super(ColumnAddingCommand, self)._get_column(
            hooke=hooke, params=params, block_name=block_name,
            column_name=column_name)

    def _set_column(self, hooke, params, block_name=None, column_name=None,
                    values=None):
        if column_name == None:
            column_name = self._column_arguments[0].name
        column_name = params[column_name]
        block = self._block(hooke=hooke, params=params, name=block_name)
        if column_name not in block.info['columns']:
            new = Data((block.shape[0], block.shape[1]+1), dtype=block.dtype)
            new.info = copy.deepcopy(block.info)
            new[:,:-1] = block
            new.info['columns'].append(column_name)
            block = new
            block_index = self._block_index(hooke, params, name=block_name)
            self._curve(hooke, params).data[block_index] = block
        column_index = block.info['columns'].index(column_name)
        block[:,column_index] = values


# The plugin itself

class CurvePlugin (Builtin):
    def __init__(self):
        super(CurvePlugin, self).__init__(name='curve')
        self._commands = [
            GetCommand(self), InfoCommand(self), DeltaCommand(self),
            ExportCommand(self), DifferenceCommand(self),
            DerivativeCommand(self), PowerSpectrumCommand(self)]


# Define commands

class GetCommand (CurveCommand):
    """Return a :class:`hooke.curve.Curve`.
    """
    def __init__(self, plugin):
        super(GetCommand, self).__init__(
            name='get curve', help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        outqueue.put(self._curve(hooke, params))


class InfoCommand (CurveCommand):
    """Get selected information about a :class:`hooke.curve.Curve`.
    """
    def __init__(self, plugin):
        args = [
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
        curve = self._curve(hooke, params)
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
                lines.append('%s: %s' % (key, get(curve)))
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


class DeltaCommand (BlockCommand):
    """Get distance information between two points.

    With two points A and B, the returned distances are A-B.
    """
    def __init__(self, plugin):
        super(DeltaCommand, self).__init__(
            name='delta',
            arguments=[
                Argument(name='point', type='point', optional=False, count=2,
                         help="""
Indicies of points bounding the selected data.
""".strip()),
                Argument(name='SI', type='bool', default=False,
                         help="""
Return distances in SI notation.
""".strip())
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        data = self._block(hooke, params)
        As = data[params['point'][0],:]
        Bs = data[params['point'][1],:]
        ds = [A-B for A,B in zip(As, Bs)]
        if params['SI'] == False:
            out = [(name, d) for name,d in zip(data.info['columns'], ds)]
        else:
            out = []
            for name,d in zip(data.info['columns'], ds):
                n,units = split_data_label(name)
                out.append(
                  (n, ppSI(value=d, unit=units, decimals=2)))
        outqueue.put(out)


class ExportCommand (BlockCommand):
    """Export a :class:`hooke.curve.Curve` data block as TAB-delimeted
    ASCII text.

    A "#" prefixed header will optionally appear at the beginning of
    the file naming the columns.
    """
    def __init__(self, plugin):
        super(ExportCommand, self).__init__(
            name='export block',
            arguments=[
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
        data = self._block(hooke, params)

        with open(params['output'], 'w') as f:
            if params['header'] == True:
                f.write('# %s \n' % ('\t'.join(data.info['columns'])))
            numpy.savetxt(f, data, delimiter='\t')


class DifferenceCommand (ColumnAddingCommand):
    """Calculate the difference between two columns of data.

    The difference is added to block A as a new column.

    Note that the command will fail if the columns have different
    lengths, so be careful when differencing columns from different
    blocks.
    """
    def __init__(self, plugin):
        super(DifferenceCommand, self).__init__(
            name='difference',
            blocks=[
                ('block A', None,
                 'Name of block A in A-B.  Defaults to the first block'),
                ('block B', None,
                 'Name of block B in A-B.  Defaults to matching `block A`.'),
                ],
            columns=[
                ('column A', None,
                 """
Column of data from block A to difference.  Defaults to the first column.
""".strip()),
                ('column B', None,
                 """
Column of data from block B to difference.  Defaults to matching `column A`.
""".strip()),
                ],
            new_columns=[
                ('output column', None,
                 """
Name of the new column for storing the difference (without units, defaults to
`difference of <block A> <column A> and <block B> <column B>`).
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        self._add_to_command_stack(params)
        params = self.__setup_params(hooke=hooke, params=params)
        data_A = self._get_column(hooke=hooke, params=params,
                                  block_name='block A',
                                  column_name='column A')
        data_B = self._get_column(hooke=hooke, params=params,
                                  block_name='block B',
                                  column_name='column B')
        out = data_A - data_B
        self._set_column(hooke=hooke, params=params,
                         block_name='block A',
                         column_name='output column',
                         values=out)

    def __setup_params(self, hooke, params):
        curve = self._curve(hooke, params)
        if params['block A'] == None:
            params['block A'] = curve.data[0].info['name']
        if params['block B'] == None:
            params['block B'] = params['block A']
        block_A = self._block(hooke, params=params, name='block A')
        block_B = self._block(hooke, params=params, name='block B')
        if params['column A'] == None:
            params['column A'] = block.info['columns'][0]
        if params['column B'] == None:
            params['column B'] = params['column A']
        a_name,a_unit = split_data_label(params['column A'])
        b_name,b_unit = split_data_label(params['column B'])
        if a_unit != b_unit:
            raise Failure('Unit missmatch: %s != %s' % (a_unit, b_unit))
        if params['output column'] == None:
            params['output column'] = join_data_label(
                'difference of %s %s and %s %s' % (
                    block_A.info['name'], a_name,
                    block_B.info['name'], b_name),
                a_unit)
        else:
            params['output column'] = join_data_label(
                params['output column'], a_unit)
        return params


class DerivativeCommand (ColumnAddingCommand):
    """Calculate the derivative (actually, the discrete differentiation)
    of a data column.

    See :func:`hooke.util.calculus.derivative` for implementation
    details.
    """
    def __init__(self, plugin):
        super(DerivativeCommand, self).__init__(
            name='derivative',
            columns=[
                ('x column', None,
                 'Column of data block to differentiate with respect to.'),
                ('f column', None,
                 'Column of data block to differentiate.'),
                ],
            new_columns=[
                ('output column', None,
                 """
Name of the new column for storing the derivative (without units, defaults to
`derivative of <f column> with respect to <x column>`).
""".strip()),
                ],
            arguments=[
                Argument(name='weights', type='dict', default={-1:-0.5, 1:0.5},
                         help="""
Weighting scheme dictionary for finite differencing.  Defaults to
central differencing.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        self._add_to_command_stack(params)
        params = self.__setup_params(hooke=hooke, params=params)
        x_data = self._get_column(hooke=hooke, params=params,
                                  column_name='x column')
        f_data = self._get_column(hooke=hooke, params=params,
                                  column_name='f column')
        d = derivative(
            x_data=x_data, f_data=f_data, weights=params['weights'])
        self._set_column(hooke=hooke, params=params,
                         column_name='output column',
                         values=d)

    def __setup_params(self, hooke, params):
        curve = self._curve(hooke, params)
        x_name,x_unit = split_data_label(params['x column'])
        f_name,f_unit = split_data_label(params['f column'])
        d_unit = '%s/%s' % (f_unit, x_unit)
        if params['output column'] == None:
            params['output column'] = join_data_label(
                'derivative of %s with respect to %s' % (
                    f_name, x_name),
                d_unit)
        else:
            params['output column'] = join_data_label(
                params['output column'], d_unit)
        return params


class PowerSpectrumCommand (ColumnAddingCommand):
    """Calculate the power spectrum of a data column.
    """
    def __init__(self, plugin):
        super(PowerSpectrumCommand, self).__init__(
            name='power spectrum',
            arguments=[
                Argument(name='output block', type='string',
                         help="""
Name of the new data block for storing the power spectrum (defaults to
`power spectrum of <source block name> <source column name>`).
""".strip()),
                Argument(name='bounds', type='point', optional=True, count=2,
                         help="""
Indicies of points bounding the selected data.
""".strip()),
                Argument(name='freq', type='float', default=1.0,
                         help="""
Sampling frequency.
""".strip()),
                Argument(name='freq units', type='string', default='Hz',
                         help="""
Units for the sampling frequency.
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
        self._add_to_command_stack(params)
        params = self.__setup_params(hooke=hooke, params=params)
        data = self._get_column(hooke=hooke, params=params)
        bounds = params['bounds']
        if bounds != None:
            data = data[bounds[0]:bounds[1]]
        freq_axis,power = unitary_avg_power_spectrum(
            data, freq=params['freq'],
            chunk_size=params['chunk size'],
            overlap=params['overlap'])
        b = Data((len(freq_axis),2), dtype=data.dtype)
        b.info['name'] = params['output block']
        b.info['columns'] = [
            params['output freq column'],
            params['output power column'],
            ]
        self._curve(hooke, params).data.append(b)
        self._set_column(hooke, params, block_name='output block',
                         column_name='output freq column',
                         values=freq_axis)
        self._set_column(hooke, params, block_name='output block',
                         column_name='output power column',
                         values=power)
        outqueue.put(b)

    def __setup_params(self, hooke, params):
        if params['output block'] in self._block_names(hooke, params):
            raise Failure('output block %s already exists in %s.'
                          % (params['output block'],
                             self._curve(hooke, params)))
        data = self._get_column(hooke=hooke, params=params)
        d_name,d_unit = split_data_label(data.info['name'])
        if params['output block'] == None:
            params['output block'] = 'power spectrum of %s %s' % (
                data.info['name'], params['column'])
        self.params['output freq column'] = join_data_label(
            'frequency axis', params['freq units'])
        self.params['output power column'] = join_data_label(
            'power density', '%s^2/%s' % (data_units, params['freq units']))
        return params


class OldCruft (object):

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
