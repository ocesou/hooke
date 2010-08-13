# Copyright (C) 2009-2010 Fabrizio Benedetti
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

"""The `cut` module provides :class:`CutPlugin` and
:class:`CutCommand`.
"""

import numpy

from ..command import Command, Argument, Failure
from . import Plugin


class CutPlugin (Plugin):
    def __init__(self):
        super(CutPlugin, self).__init__(name='cut')
        self._commands = [CutCommand(self)]


# Define common or complicated arguments

def current_curve_callback(hooke, command, argument, value):
    playlist = hooke.playlists.current()
    if playlist == None:
        raise Failure('No playlists loaded')
    curve = playlist.current()
    if curve == None:
        raise Failure('No curves in playlist %s' % playlist.name)
    return curve

CurveArgument = Argument(
    name='curve', type='curve', callback=current_curve_callback,
    help="""
:class:`hooke.curve.Curve` to cut from.  Defaults to the current curve.
""".strip())


# Define commands

class CutCommand (Command):
    """Cut the selected signal between two points and write it to a file.

    The data is saved in TAB-delimited ASCII text.  A "#" prefixed
    header will optionally appear at the beginning of the file naming
    the columns.
    """
    def __init__(self, plugin):
        super(CutCommand, self).__init__(
            name='cut',
            arguments=[
                CurveArgument,
                Argument(name='block', aliases=['set'], type='int', default=0,
                    help="""
Data block to save.  For an approach/retract force curve, `0` selects
the approaching curve and `1` selects the retracting curve.
""".strip()),
                Argument(name='bounds', type='point', optional=False, count=2,
                         help="""
Indicies of points bounding the selected data.
""".strip()),
                Argument(name='output', type='file', default='cut.dat',
                         help="""
File name for the output data.
""".strip()),
                Argument(name='header', type='bool', default=True,
                         help="""
True if you want the column-naming header line.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        if params['curve'] == None:
            params['curve'] = hooke.playlists.current().current()

	i_min = min([p.index for p in params['points']])
	i_max = max([p.index for p in params['points']])

	data = params['curve'][params['bound']]
        cut_data = data[i_min:i_max+1,:] # slice rows from row-major data
        # +1 to include data[i_max] row

        f = open(params['output'], 'w')
        if params['header'] == True:
            f.write('# %s \n' % ('\t'.join(cut_data.info['columns'])))
        numpy.savetxt(f, cut_data, delimiter='\t')
        f.close()
