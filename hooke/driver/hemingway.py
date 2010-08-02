# Copyright (C) 2008-2010 Massimo Sandal <devicerandom@gmail.com>
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

"""Library for interpreting Hemingway force spectroscopy files.
"""

import numpy

from .. import curve as curve
from .. import experiment as experiment
from ..config import Setting
from ..util.util import Closing as Closing
from . import Driver as Driver


class HemingwayDriver (Driver):
    """Handle Hemingway force spectroscopy files.
    """
    def __init__(self):
        super(HemingwayDriver, self).__init__(name='hemingway')

    def is_me(self, path):
        headlines = []
        with Closing(file(path, 'r')) as f:
            for i in range(2):
                headlines.append(f.readline())
        return (headlines[0].startswith('#Hemingway')
                and headlines[1].startswith('#Experiment: FClamp'))

    def read(self, path, info=None):
        file_info = {}
        with Closing(file(path, 'r')) as f:
            while True:
                line = f.readline().strip()
                if line == '#END':
                    break
                fields = line.split(':', 1)
                if len(fields) == 2:
                    file_info[fields[0]] = fields[1]
            data = numpy.loadtxt(f, dtype=numpy.float)
        ret = curve.Data(
            shape=data.shape,
            dtype=data.dtype,
            buffer=data,
            info=file_info,
            )
        ret.info['columns'] = [
            'time (s)',  # first data column in file just increasing index
            'phase (m?rad)',
            'z piezo (m)',
            'deflection (N)',
            'imposed (N)',
            ]
        # assume 1 ms timestep
        ret[:,0] = numpy.arange(0, 1e-3*data.shape[0], 1e-3, dtype=ret.dtype)
        
        file_info['filetype'] = self.name
        file_info['experiment'] = experiment.ForceClamp
        return ([ret,], file_info)
