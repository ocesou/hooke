# Copyright (C) 2008-2010 A. Seeholzer
#                         Alberto Gomez-Casado
#                         Richard Naud <richard.naud@epfl.ch>
#                         Rolf Schmidt <rschmidt@alcor.concordia.ca>
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

"""Driver for MFP-3D files.

This driver reads IGOR binary waves.

AUTHORS:
Matlab version: Richard Naud August 2008 (http://lcn.epfl.ch/~naud/)
Python port: A. Seeholzer October 2008
Hooke submission: Rolf Schmidt, Alberto Gomez-Casado 2009
"""

import copy
import os.path
import pprint

import numpy

from .. import curve as curve
from .. import experiment as experiment
from . import Driver as Driver
from .igorbinarywave import loadibw


__version__='0.0.0.20100604'


class MFP3DDriver (Driver):
    """Handle Asylum Research's MFP3D data format.
    """
    def __init__(self):
        super(MFP3DDriver, self).__init__(name='mfp3d')

    def is_me(self, path):
        """Look for identifying fields in the IBW note.
        """
        if os.path.isdir(path):
            return False
        if not path.endswith('.ibw'):
            return False
        targets = ['Version:', 'XOPVersion:', 'ForceNote:']
        found = [False]*len(targets)
        for line in open(path, 'rU'):
            for i,ft in enumerate(zip(found, targets)):
                f,t = ft
                if f == False and line.startswith(t):
                    found[i] = True
        if min(found) == True:
            return True
        return False
    
    def read(self, path, info=None):
        data,bin_info,wave_info = loadibw(path)
        approach,retract = self._translate_ibw(data, bin_info, wave_info)

        info = {'filetype':self.name, 'experiment':experiment.VelocityClamp}
        return ([approach, retract], info)
     
    def _translate_ibw(self, data, bin_info, wave_info):
        if bin_info['version'] != 5:
            raise NotImplementedError('IBW version %d (< 5) not supported'
                                      % bin_info['version'])
            # We need version 5 for multidimensional arrays.

        # Parse the note into a dictionary
        note = {}
        for line in bin_info['note'].split('\r'):
            fields = [x.strip() for x in line.split(':', 1)]
            key = fields[0]
            if len(fields) == 2:
                value = fields[1]
            else:
                value = None
            note[key] = value
        bin_info['note'] = note
        if note['VerDate'] not in ['80501.041', '80501.0207']:
            raise Exception(note['VerDate'])
            raise NotImplementedError(
                '%s file version %s not supported (yet!)\n%s'
                % (self.name, note['VerDate'], pprint.pformat(note)))

        info = {
            'raw info':{'bin':bin_info,
                        'wave':wave_info},
            'time':wave_info['creationDate'],
            'spring constant (N/m)':note['SpringConstant'],
            }
        # MFP3D's native data dimensions match Hooke's (<point>, <column>) layout.
        approach = self._scale_block(data[:wave_info['npnts']/2,:], info, 'approach')
        retract = self._scale_block(data[wave_info['npnts']/2:,:], info, 'retract')
        return (approach, retract)

    def _scale_block(self, data, info, name):
        """Convert the block from its native format to a `numpy.float`
        array in SI units.
        """
        shape = 3
        # raw column indices
        columns = info['raw info']['bin']['dimLabels'][1]
        # Depending on your MFP3D version:
        #   VerDate 80501.0207: ['Raw', 'Defl', 'LVDT', 'Time']
        #   VerDate 80501.041:  ['Raw', 'Defl', 'LVDT']
        if 'Time' in columns:
            n_col = 3
        else:
            n_col = 2
        ret = curve.Data(
            shape=(data.shape[0], n_col),
            dtype=numpy.float,
            info=copy.deepcopy(info)
            )
        ret.info['name'] = name
        ret.info['raw data'] = data # store the raw data

        z_rcol = columns.index('LVDT')
        d_rcol = columns.index('Defl')

        # scaled column indices
        ret.info['columns'] = ['z piezo (m)', 'deflection (m)']
        z_scol = ret.info['columns'].index('z piezo (m)')
        d_scol = ret.info['columns'].index('deflection (m)')

        # Leading '-' because increasing voltage extends the piezo,
        # moving the tip towards the surface (positive indentation),
        # but it makes more sense to me to have it increase away from
        # the surface (positive separation).
        ret[:,z_scol] = -data[:,z_rcol].astype(ret.dtype)

        # Leading '-' because deflection voltage increases as the tip
        # moves away from the surface, but it makes more sense to me
        # to have it increase as it moves toward the surface (positive
        # tension on the protein chain).
        ret[:,d_scol] = -data[:,d_rcol]

        if 'Time' in columns:
            ret.info['columns'].append('time (s)')
            t_rcol = columns.index('Time')
            t_scol = ret.info['columns'].index('time (s)')
            ret[:,t_scol] = data[:,t_rcol]

        return ret
