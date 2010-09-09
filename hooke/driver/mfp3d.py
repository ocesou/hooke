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
from ..util.igorbinarywave import loadibw
from . import Driver as Driver


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
        blocks,info = self._translate_ibw(data, bin_info, wave_info)
        return (blocks, info)
     
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

        # Ensure a valid MFP3D file version.
        if note['VerDate'] not in ['80501.041', '80501.0207']:
            raise Exception(note['VerDate'])
            raise NotImplementedError(
                '%s file version %s not supported (yet!)\n%s'
                % (self.name, note['VerDate'], pprint.pformat(note)))

        # Parse known parameters into standard Hooke format.
        info = {
            'raw info':{'bin':bin_info,
                        'wave':wave_info},
            'time':note['Seconds'],
            'spring constant (N/m)':float(note['SpringConstant']),
            'temperature (K)':self._temperature(note),
            }

        # Extract data blocks
        blocks = []
        indexes = [int(i) for i in note['Indexes'].split(',')]
        assert indexes[0] == 0, indexes
        for i,start in enumerate(indexes[:-1]):
            stop = indexes[i+1]
            blocks.append(self._scale_block(data[start:stop+1,:], info, i))

        return (blocks, info)

    def _scale_block(self, data, info, index):
        """Convert the block from its native format to a `numpy.float`
        array in SI units.
        """
        # MFP3D's native data dimensions match Hooke's (<point>, <column>) layout.
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

        version = info['raw info']['bin']['note']['VerDate']
        if version == '80501.041':
            name = ['approach', 'retract', 'pause'][index]
        elif version == '80501.0207':
            name = ['approach', 'pause', 'retract'][index]
        else:
            raise NotImplementedError()
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

    def _temperature(self, note):
        # I'm not sure which field we should be using here.  Options are:
        #   StartHeadTemp
        #   StartScannerTemp
        #   StartBioHeaterTemp
        #   EndScannerTemp
        #   EndHeadTemp
        # I imagine the 'Start*Temp' fields were measured at
        # 'StartTempSeconds' at the beginning of a series of curves,
        # while our particular curve was initiated at 'Seconds'.
        #   python -c "from hooke.hooke import Hooke;
        #              h=Hooke();
        #              h.run_command('load playlist',
        #                  {'input':'test/data/vclamp_mfp3d/playlist'});
        #              x = [(int(c.info['raw info']['bin']['note']['Seconds'])
        #                    - int(c.info['raw info']['bin']['note']['StartTempSeconds']))
        #                   for c in h.playlists.current().items()];
        #              print 'average', float(sum(x))/len(x);
        #              print 'range', min(x), max(x);
        #              print x"
        # For the Line*Point*.ibw series, the difference increases slowly
        #   46, 46, 47, 47, 48, 49, 49, 50, 50, 51, 51, 52, 52, 53, 53, 54,...
        # However, for the Image*.ibw series, the difference increase
        # is much faster:
        #   21, 38, 145, 150, 171, 181
        # This makes the 'Start*Temp' fields less and less relevant as
        # the experiment continues.  Still, I suppose it's better than
        # nothing.
        #
        # The 'Thermal' fields seem to be related to cantilever calibration.
        celsius = unicode(note['StartHeadTemp'], 'latin-1')
        if celsius.endswith(u' \u00b0C'):
            number = celsius.split(None, 1)[0]
            return float(number) + 273.15  # Convert to Kelvin.
        else:
            raise NotImplementedError(
                'unkown temperature format: %s' % repr(celsius))
