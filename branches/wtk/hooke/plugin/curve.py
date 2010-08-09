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

"""The ``curve`` module provides :class:`CurvePlugin` and several
associated :class:`hooke.command.Command`\s for handling
:mod:`hooke.curve` classes.
"""

import copy

import numpy

from ..command import Command, Argument, Failure
from ..curve import Data
from ..plugin import Builtin
from ..plugin.playlist import current_playlist_callback
from ..util.calculus import derivative
from ..util.fft import unitary_avg_power_spectrum
from ..util.si import ppSI, join_data_label, split_data_label



class CurvePlugin (Builtin):
    def __init__(self):
        super(CurvePlugin, self).__init__(name='curve')
        self._commands = [
            GetCommand(self), InfoCommand(self), DeltaCommand(self),
            ExportCommand(self), DifferenceCommand(self),
            DerivativeCommand(self), PowerSpectrumCommand(self)]


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


class DeltaCommand (Command):
    """Get distance information between two points.

    With two points A and B, the returned distances are A-B.
    """
    def __init__(self, plugin):
        super(DeltaCommand, self).__init__(
            name='delta',
            arguments=[
                CurveArgument,
                Argument(name='block', type='int', default=0,
                    help="""
Data block that points are selected from.  For an approach/retract
force curve, `0` selects the approaching curve and `1` selects the
retracting curve.
""".strip()),
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
        data = params['curve'].data[params['block']]
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
                Argument(name='block', type='int', default=0,
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
        data = params['curve'].data[params['block']]

        f = open(params['output'], 'w')
        if params['header'] == True:
            f.write('# %s \n' % ('\t'.join(data.info['columns'])))
        numpy.savetxt(f, data, delimiter='\t')
        f.close()

class DifferenceCommand (Command):
    """Calculate the difference between two columns of data.

    The difference is added to block A as a new column.

    Note that the command will fail if the columns have different
    lengths, so be careful when differencing columns from different
    blocks.
    """
    def __init__(self, plugin):
        super(DifferenceCommand, self).__init__(
            name='difference',
            arguments=[
                CurveArgument,
                Argument(name='block A', type='int',
                         help="""
Block A in A-B.  For an approach/retract force curve, `0` selects the
approaching curve and `1` selects the retracting curve.  Defaults to
the first block.
""".strip()),
                Argument(name='block B', type='int',
                         help="""
Block B in A-B.  Defaults to matching `block A`.
""".strip()),
                Argument(name='column A', type='string',
                         help="""
Column of data from block A to difference.  Defaults to the first column.
""".strip()),
                Argument(name='column B', type='string', default=1,
                         help="""
Column of data from block B to difference.  Defaults to matching `column A`.
""".strip()),
                Argument(name='output column name', type='string',
                         help="""
Name of the new column for storing the difference (without units, defaults to
`difference of <block A> <column A> and <block B> <column B>`).
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        data_A = params['curve'].data[params['block A']]
        data_B = params['curve'].data[params['block B']]
        # HACK? rely on params['curve'] being bound to the local hooke
        # playlist (i.e. not a copy, as you would get by passing a
        # curve through the queue).  Ugh.  Stupid queues.  As an
        # alternative, we could pass lookup information through the
        # queue...
        new = Data((data_A.shape[0], data_A.shape[1]+1), dtype=data_A.dtype)
        new.info = copy.deepcopy(data.info)
        new[:,:-1] = data_A

        a_col = data_A.info['columns'].index(params['column A'])
        b_col = data_A.info['columns'].index(params['column A'])
        out = data_A[:,a_col] - data_B[:,b_col]

        a_name,a_units = split_data_label(params['column A'])
        b_name,b_units = split_data_label(params['column B'])
        assert a_units == b_units, (
            'Unit missmatch: %s != %s' % (a_units, b_units))
        if params['output column name'] == None:
            params['output column name'] = (
                'difference of %s %s and %s %s' % (
                    block_A.info['name'], params['column A'],
                    block_B.info['name'], params['column B']))
        new.info['columns'].append(
            join_data_label(params['output distance column'], a_units))
        new[:,-1] = out
        params['curve'].data[params['block A']] = new


class DerivativeCommand (Command):
    """Calculate the derivative (actually, the discrete differentiation)
    of a curve data block.

    See :func:`hooke.util.calculus.derivative` for implementation
    details.
    """
    def __init__(self, plugin):
        super(DerivativeCommand, self).__init__(
            name='derivative',
            arguments=[
                CurveArgument,
                Argument(name='block', type='int', default=0,
                         help="""
Data block to differentiate.  For an approach/retract force curve, `0`
selects the approaching curve and `1` selects the retracting curve.
""".strip()),
                Argument(name='x column', type='string',
                         help="""
Column of data block to differentiate with respect to.
""".strip()),
                Argument(name='f column', type='string',
                         help="""
Column of data block to differentiate.
""".strip()),
                Argument(name='weights', type='dict', default={-1:-0.5, 1:0.5},
                         help="""
Weighting scheme dictionary for finite differencing.  Defaults to
central differencing.
""".strip()),
                Argument(name='output column name', type='string',
                         help="""
Name of the new column for storing the derivative (without units, defaults to
`derivative of <f column name> with respect to <x column name>`).
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
        new = Data((data.shape[0], data.shape[1]+1), dtype=data.dtype)
        new.info = copy.deepcopy(data.info)
        new[:,:-1] = data

        x_col = data.info['columns'].index(params['x column'])
        f_col = data.info['columns'].index(params['f column'])
        d = derivative(
            block, x_col=x_col, f_col=f_col, weights=params['weights'])

        x_name,x_units = split_data_label(params['x column'])
        f_name,f_units = split_data_label(params['f column'])
        if params['output column name'] == None:
            params['output column name'] = (
                'derivative of %s with respect to %s' % (
                    params['f column'], params['x column']))

        new.info['columns'].append(
            join_data_label(params['output distance column'],
                            '%s/%s' % (f_units/x_units)))
        new[:,-1] = d[:,1]
        params['curve'].data[params['block']] = new


class PowerSpectrumCommand (Command):
    """Calculate the power spectrum of a data block.
    """
    def __init__(self, plugin):
        super(PowerSpectrumCommand, self).__init__(
            name='power spectrum',
            arguments=[
                CurveArgument,
                Argument(name='block', type='int', default=0,
                         help="""
Data block to act on.  For an approach/retract force curve, `0`
selects the approaching curve and `1` selects the retracting curve.
""".strip()),
                Argument(name='column', type='string', optional=False,
                         help="""
Name of the data block column containing to-be-transformed data.
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
                Argument(name='output block name', type='string',
                         help="""
Name of the new data block for storing the power spectrum (defaults to
`power spectrum of <source block name> <source column name>`).
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        data = params['curve'].data[params['block']]
        col = data.info['columns'].index(params['column'])
        d = data[:,col]
        if bounds != None:
            d = d[params['bounds'][0]:params['bounds'][1]]
        freq_axis,power = unitary_avg_power_spectrum(
            d, freq=params['freq'],
            chunk_size=params['chunk size'],
            overlap=params['overlap'])

        name,data_units = split_data_label(params['column'])
        b = Data((len(freq_axis),2), dtype=data.dtype)
        if params['output block name'] == None:
            params['output block name'] = 'power spectrum of %s %s' % (
              params['output block name'], data.info['name'], params['column'])
        b.info['name'] = params['output block name']
        b.info['columns'] = [
            join_data_label('frequency axis', params['freq units']),
            join_data_label('power density',
                            '%s^2/%s' % (data_units, params['freq units'])),
            ]
        b[:,0] = freq_axis
        b[:,1] = power
        params['curve'].data.append(b)
        outqueue.put(b)


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
