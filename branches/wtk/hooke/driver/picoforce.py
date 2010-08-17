# Copyright (C) 2006-2010 Alberto Gomez-Casado
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

"""Driver for Veeco PicoForce force spectroscopy files.
"""

import os.path
import pprint
import re
import time

import numpy

from .. import curve as curve # this module defines data containers.
from .. import experiment as experiment # this module defines expt. types
from . import Driver as Driver # this is the Driver base class


__version__='0.0.0.20100516'

class PicoForceDriver (Driver):
    """Handle Veeco Picoforce force spectroscopy files.
    """
    def __init__(self):
        super(PicoForceDriver, self).__init__(name='picoforce')

    def is_me(self, path):
        if os.path.isdir(path):
            return False
        f = file(path, 'r')
        header = f.read(30)
        f.close()

        return header[2:17] == 'Force file list'

    def read(self, path, info=None):
        info = self._read_header_path(path)
        self._check_version(info)
        data = self._read_data_path(path, info)
        info['filetype'] = self.name
        info['experiment'] = experiment.VelocityClamp
        return (data, info)

    def _read_header_path(self, path):
        """Read curve information from the PicoForce file at `path`.

        See :meth:`._read_header_file`.
        """
        return self._read_header_file(file(path, 'rb'))

    def _read_header_file(self, file):
        r"""Read curve information from a PicoForce file.

        Return a dict of dicts representing the information.  If a
        field is repeated multiple times, it's value is replaced by a
        list of the values for each occurence.

        Examples
        --------

        >>> import pprint
        >>> import StringIO
        >>> f = StringIO.StringIO('\r\n'.join([
        ...             '\*Force file list',
        ...             '\Version: 0x06120002',
        ...             '\Date: 04:42:34 PM Tue Sep 11 2007',
        ...             '\Start context: FOL2',
        ...             '\Data length: 40960',
        ...             '\Text: ',
        ...             '\*Equipment list',
        ...             '\Description: Extended PicoForce',
        ...             '\Controller: IIIA',
        ...             '\*Ciao force image list',
        ...             '\Data offset: 40960',
        ...             '\Data length: 8192',
        ...             '\*Ciao force image list',
        ...             '\Data offset: 49152',
        ...             '\Data length: 8192',
        ...             '\*Ciao force image list',
        ...             '\Data offset: 57344',
        ...             '\Data length: 8192',
        ...             ]))
        >>> p = PicoForceDriver()
        >>> d = p._read_header_file(f)
        >>> pprint.pprint(d, width=60)
        {'Ciao force image list': [{'Data length': '8192',
                                    'Data offset': '40960'},
                                   {'Data length': '8192',
                                    'Data offset': '49152'},
                                   {'Data length': '8192',
                                    'Data offset': '57344'}],
         'Equipment list': {'Controller': 'IIIA',
                            'Description': 'Extended PicoForce'},
         'Force file list': {'Data length': '40960',
                             'Date': '04:42:34 PM Tue Sep 11 2007',
                             'Start context': 'FOL2',
                             'Text:': None,
                             'Version': '0x06120002'}}
        """
        info = {}
        header_field = None
        for line in file:
            line = line.strip()
            if line.startswith('\*File list end'):
                break
            if line.startswith(r'\*'):
                header_field = line[len(r'\*'):]
                if header_field in info:
                    if isinstance(info[header_field], list):
                        info[header_field].append({}) # >=3rd appearance
                    else: # Second appearance
                        info[header_field] = [info[header_field], {}]
                else: # First appearance
                    info[header_field] = {}
            else:
                assert line.startswith('\\'), line
                fields = line[len('\\'):].split(': ', 1)
                key = fields[0]
                if len(fields) == 1: # fields = [key]
                    value = None
                else: # fields = [key, value]
                    value = fields[1]
                if isinstance(info[header_field], list): # >=2nd header_field
                    target_dict = info[header_field][-1]
                else: # first appearance of header_field
                    target_dict = info[header_field]
                if key in target_dict and target_dict[key] != value:
                    raise NotImplementedError(
                        'Overwriting %s: %s -> %s'
                        % (key, target_dict[key], value))
                target_dict[key] = value
        return (info)

    def _check_version(self, info):
        """Ensure the input file is a version we understand.

        Otherwise, raise `ValueError`.
        """
        version = info['Force file list'].get('Version', None)
        if version not in ['0x06120002', '0x06130001', '0x07200000']:
            raise NotImplementedError(
                '%s file version %s not supported (yet!)\n%s'
                % (self.name, version,
                   pprint.pformat(info['Force file list'])))

    def _read_data_path(self, path, info):
        """Read curve data from the PicoForce file at `path`.

        See :meth:`._read_data_file`.
        """
        f = file(path, 'rb')
        data = self._read_data_file(f, info)
        f.close()
        return data

    def _read_data_file(self, file, info):
        file.seek(0)
        traces = self._extract_traces(buffer(file.read()), info)
        self._validate_traces(
            traces['Z sensor'], traces['Deflection'])
        L = len(traces['Deflection'])
        approach = self._extract_block(
            info, traces['Z sensor'], traces['Deflection'], 0, L/2, 'approach')
        retract = self._extract_block(
            info, traces['Z sensor'], traces['Deflection'], L/2, L, 'retract')
        data = [approach, retract]
        return data

    def _extract_traces(self, buffer, info):
        """Extract each of the three vector blocks in a PicoForce file.

        The blocks are (in variable order):

        * Z piezo sensor input
        * Deflection input
        * Deflection again?

        And their headers are marked with 'Ciao force image list'.
        """
        traces = {}
        version = info['Force file list']['Version']
        type_re = re.compile('S \[(\w*)\] "([\w\s.]*)"')
        for image in info['Ciao force image list']:
            offset = int(image['Data offset'])
            length = int(image['Data length'])
            sample_size = int(image['Bytes/pixel'])
            if sample_size != 2:
                raise NotImplementedError('Size: %s' % sample_size)
            rows = length / sample_size
            d = curve.Data(
                shape=(rows),
                dtype=numpy.int16,
                buffer=buffer,
                offset=offset,
                info=image,
                )
            if version in ['0x06120002', '0x06130001']:
                match = type_re.match(image['@4:Image Data'])
                assert match != None, 'Bad regexp for %s, %s' \
                    % ('@4:Image Data', image['@4:Image Data'])
                if version == '0x06130001' and match.group(1) == 'ZLowVoltage':
                    assert match.group(2) == 'Low Voltage Z', \
                        'Name missmatch: "%s", "%s"' % (match.group(1), match.group(2))
                else:
                    assert match.group(1).lower() == match.group(2).replace(' ','').lower(), \
                        'Name missmatch: "%s", "%s"' % (match.group(1), match.group(2))
                tname = match.group(2)
            else:
                assert version == '0x07200000', version
                match = type_re.match(image['@4:Image Data'])
                assert match != None, 'Bad regexp for %s, %s' \
                    % ('@4:Image Data', image['@4:Image Data'])
                if match.group(1) == 'PulseFreq1':
                    assert match.group(2) == 'Freq. 1', match.group(2)
                else:
                    assert match.group(1).lower() == match.group(2).replace(' ','').lower(), \
                        'Name missmatch: "%s", "%s"' % (match.group(1), match.group(2))
                tname = match.group(2)
                if tname == 'Freq. 1':  # Normalize trace names between versions
                    tname = 'Z sensor'
                elif tname == 'Deflection Error':
                    tname = 'Deflection'
            if tname in traces:
                #d.tofile('%s-2.dat' % tname, sep='\n')
                tname = self._replace_name(tname, d, traces, info)
                if tname == None:
                    continue  # Don't replace anything
            else:
                #d.tofile('%s.dat' % tname, sep='\n')
                pass
            traces[tname] = d
        return traces

    def _validate_traces(self, z_piezo, deflection):
        if len(z_piezo) != len(deflection):
            raise ValueError('Trace length missmatch: %d != %d'
                             % (len(z_piezo), len(deflection)))

    def _extract_block(self, info, z_piezo, deflection, start, stop, name):
        block = curve.Data(
            shape=(stop-start, 2),
            dtype=numpy.float)
        block[:,0] = z_piezo[start:stop]
        block[:,1] = deflection[start:stop]
        block.info = self._translate_block_info(
            info, z_piezo.info, deflection.info, name)
        block.info['columns'] = ['z piezo (m)', 'deflection (m)']
        block = self._scale_block(block)
        return block

    def _replace_name(self, trace_name, trace, traces, info):
        """Determine if a duplicate trace name should replace an earlier trace.

        Return the target trace name if it should be replaced by the
        new trace, or `None` if the new trace should be dropped.
        """
        #msg = []
        #target = traces[trace_name]
        #
        ## Compare the info dictionaries for each trace
        #ik = set(trace.info.keys())
        #ok = set(traces[trace_name].info.keys())
        #if ik != ok:  # Ensure we have the same set of keys for both traces
        #    msg.append('extra keys: %s, missing keys %s' % (ik-ok, ok-ik))
        #else:
        #    # List keys we *require* to change between traces
        #    variable_keys = ['Data offset', 'X data type']  # TODO: What is X data type?
        #    for key in trace.info.keys():
        #        if key in variable_keys:
        #            if target.info[key] == trace.info[key]:
        #                msg.append('constant %s (%s == %s)'
        #                           % (key, target.info[key], trace.info[key]))
        #        else:
        #            if target.info[key] != trace.info[key]:
        #                msg.append('variable %s (%s != %s)'
        #                           % (key, target.info[key], trace.info[key]))
        # Compare the data
        #if not (traces[trace_name] == trace).all():
        #    msg.append('data difference')
        #if len(msg) > 0:
        #    raise NotImplementedError(
        #        'Missmatched duplicate traces for %s: %s'
        #        % (trace_name, ', '.join(msg)))
        import logging
        log = logging.getLogger('hooke')
        for name,t in traces.items():
            if (t == trace).all():
                log.debug('replace %s with %s-2' % (name, trace_name))
                return name  # Replace this identical dataset.
        log.debug('store %s-2 as Other' % (trace_name))
        return 'Other'
        # return None

    def _translate_block_info(self, info, z_piezo_info, deflection_info, name):
        version = info['Force file list']['Version']
        ret = {
            'name': name,
            'raw info': info,
            'raw z piezo info': z_piezo_info,
            'raw deflection info': deflection_info,
            'spring constant (N/m)': float(z_piezo_info['Spring Constant']),
            }

        t = info['Force file list']['Date'] # 04:42:34 PM Tue Sep 11 2007
        ret['time'] = time.strptime(t, '%I:%M:%S %p %a %b %d %Y')

        volt_re = re.compile(
            'V \[Sens. ([\w\s.]*)\] \(([.0-9]*) V/LSB\) (-?[.0-9]*) V')
        hz_re = re.compile(
            'V \[Sens. ([\w\s.]*)\] \(([.0-9]*) kHz/LSB\) (-?[.0-9]*) kHz')
        if version in ['0x06120002', '0x06130001']:
            match = volt_re.match(z_piezo_info['@4:Z scale'])
            assert match != None, 'Bad regexp for %s, %s' \
                % ('@4:Z scale', z_piezo_info['@4:Z scale'])
            assert match.group(1) == 'ZSensorSens', z_piezo_info['@4:Z scale']
        else:
            assert version == '0x07200000', version
            match = hz_re.match(z_piezo_info['@4:Z scale'])
            assert match != None, 'Bad regexp for %s, %s' \
                % ('@4:Z scale', z_piezo_info['@4:Z scale'])
            assert match.group(1) == 'Freq. 1', z_piezo_info['@4:Z scale']
        ret['z piezo sensitivity (V/bit)'] = float(match.group(2))
        ret['z piezo range (V)'] = float(match.group(3))
        ret['z piezo offset (V)'] = 0.0
        # offset assumed if raw data is signed...

        match = volt_re.match(deflection_info['@4:Z scale'])
        assert match != None, 'Bad regexp for %s, %s' \
            % ('@4:Z scale', deflection_info['@4:Z scale'])
        assert match.group(1) == 'DeflSens', z_piezo_info['@4:Z scale']
        ret['deflection sensitivity (V/bit)'] = float(match.group(2))
        ret['deflection range (V)'] = float(match.group(3))
        ret['deflection offset (V)'] = 0.0
        # offset assumed if raw data is signed...

        nm_sens_re = re.compile('V ([.0-9]*) nm/V')
        if version in ['0x06120002', '0x06130001']:        
            match = nm_sens_re.match(info['Ciao scan list']['@Sens. ZSensorSens'])
            assert match != None, 'Bad regexp for %s/%s, %s' \
                % ('Ciao scan list', '@Sens. ZSensorSens',
                   info['Ciao scan list']['@Sens. ZSensorSens'])
        else:
            assert version == '0x07200000', version
            match = nm_sens_re.match(info['Ciao scan list']['@Sens. ZsensSens'])
            assert match != None, 'Bad regexp for %s/%s, %s' \
                % ('Ciao scan list', '@Sens. ZsensSens',
                   info['Ciao scan list']['@Sens. ZsensSens'])
        ret['z piezo sensitivity (m/V)'] = float(match.group(1))*1e-9

        match = nm_sens_re.match(info['Ciao scan list']['@Sens. DeflSens'])
        assert match != None, 'Bad regexp for %s/%s, %s' \
            % ('Ciao scan list', '@Sens. DeflSens', info['Ciao scan list']['@Sens. DeflSens'])
        ret['deflection sensitivity (m/V)'] = float(match.group(1))*1e-9

        match = volt_re.match(info['Ciao force list']['@Z scan start'])
        assert match != None, 'Bad regexp for %s/%s, %s' \
            % ('Ciao force list', '@Z scan start', info['Ciao force list']['@Z scan start'])
        ret['z piezo scan (V/bit)'] = float(match.group(2))
        ret['z piezo scan start (V)'] = float(match.group(3))

        match = volt_re.match(info['Ciao force list']['@Z scan size'])
        assert match != None, 'Bad regexp for %s/%s, %s' \
            % ('Ciao force list', '@Z scan size', info['Ciao force list']['@Z scan size'])
        ret['z piezo scan size (V)'] = float(match.group(3))

        const_re = re.compile('C \[([:\w\s]*)\] ([.0-9]*)')
        match = const_re.match(z_piezo_info['@Z magnify'])
        assert match != None, 'Bad regexp for %s, %s' \
            % ('@Z magnify', info['@Z magnify'])
        assert match.group(1) == '4:Z scale', match.group(1)
        ret['z piezo gain'] = float(match.group(2))

        if version in ['0x06120002', '0x06130001']:        
            match = volt_re.match(z_piezo_info['@4:Z scale'])
            assert match != None, 'Bad regexp for %s, %s' \
                % ('@4:Z scale', info['@4:Z scale'])
            assert match.group(1) == 'ZSensorSens', match.group(1)
            ret['z piezo sensitivity (V/bit)'] = float(match.group(2))
            ret['z piezo range (V)'] = float(match.group(3))
        else:
            assert version == '0x07200000', version
            pass

        match = volt_re.match(z_piezo_info['@4:Ramp size'])
        assert match != None, 'Bad regexp for %s, %s' \
            % ('@4:Ramp size', info['@4:Ramp size'])
        assert match.group(1) == 'Zsens', match.group(1)
        ret['z piezo ramp size (V/bit)'] = float(match.group(2))
        ret['z piezo ramp size (V)'] = float(match.group(3))

        match = volt_re.match(z_piezo_info['@4:Ramp offset'])
        assert match != None, 'Bad regexp for %s, %s' \
            % ('@4:Ramp offset', info['@4:Ramp offset'])
        assert match.group(1) == 'Zsens', match.group(1)
        ret['z piezo ramp offset (V/bit)'] = float(match.group(2))
        ret['z piezo ramp offset (V)'] = float(match.group(3))

        # Unaccounted for:
        #   Samps*

        return ret

    def _scale_block(self, data):
        """Convert the block from its native format to a `numpy.float`
        array in SI units.
        """
        ret = curve.Data(
            shape=data.shape,
            dtype=numpy.float,
            )
        info = data.info
        ret.info = info
        ret.info['raw data'] = data # store the raw data
        data.info = {} # break circular reference info <-> data

        z_col = info['columns'].index('z piezo (m)')
        d_col = info['columns'].index('deflection (m)')

        # Leading '-' because Veeco's z increases towards the surface
        # (positive indentation), but it makes more sense to me to
        # have it increase away from the surface (positive
        # separation).
        ret[:,z_col] = -(
            (data[:,z_col].astype(ret.dtype)
             * info['z piezo sensitivity (V/bit)']
             - info['z piezo offset (V)'])
            * info['z piezo gain']
            * info['z piezo sensitivity (m/V)']
            )

        # Leading '-' because deflection voltage increases as the tip
        # moves away from the surface, but it makes more sense to me
        # to have it increase as it moves toward the surface (positive
        # tension on the protein chain).
        ret[:,d_col] = -(
            (data[:,d_col]
             * info['deflection sensitivity (V/bit)']
             - info['deflection offset (V)'])
            * info['deflection sensitivity (m/V)']
            )

        return ret
