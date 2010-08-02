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

"""Driver for JPK ForceRobot's velocity clamp data format.
"""

import os.path
import pprint
import zipfile

import numpy

from .. import curve as curve
from .. import experiment as experiment
from ..util.util import Closing as Closing
from . import Driver as Driver


class JPKDriver (Driver):
    """Handle JPK ForceRobot's data format.
    """
    def __init__(self):
        super(JPKDriver, self).__init__(name='jpk')

    def is_me(self, path):
        if zipfile.is_zipfile(path):  # JPK file versions since at least 0.5
            with Closing(zipfile.ZipFile(path, 'r')) as f:
                if 'header.properties' not in f.namelist():
                    return False
                with Closing(f.open('header.properties')) as h:
                    if 'jpk-data-file' in h.read():
                        return True
        else:
            with Closing(open(path, 'r')) as f:
                headlines = []
                for i in range(3):
                    headlines.append(f.readline())
            if headlines[0].startswith('# xPosition') \
                    and headlines[1].startswith('# yPosition'):
                return True
        return False

    def read(self, path, info=None):
        if info == None:
            info = {}
        if zipfile.is_zipfile(path):  # JPK file versions since at least 0.5
            return self._read_zip(path, info)
        else:
            return self._read_old(path, info)

    def _read_zip(self, path, info):
        with Closing(zipfile.ZipFile(path, 'r')) as f:
            f.path = path
            zip_info = self._zip_info(f)
            segments = []
            for i in range(len([p for p in f.namelist()
                                if p.endswith('segment-header.properties')])):
                segments.append(self._zip_segment(f, path, info, zip_info, i))
            for name in ['approach', 'retract']:
                if len([s for s in segments if s.info['name'] == name]) == 0:
                    raise ValueError(
                        'No segment for %s in %s, only %s'
                        % (name, path, [s.info['name'] for s in segments]))
            return (segments,
                    self._zip_translate_params(zip_info,
                                               segments[0].info['raw info']))

    def _zip_info(self, zipfile):
        with Closing(zipfile.open('header.properties')) as f:
            info = self._parse_params(f.readlines())
            return info

    def _zip_segment(self, zipfile, path, info, zip_info, index):
        prop_file = zipfile.open(os.path.join(
                'segments', str(index), 'segment-header.properties'))
        prop = self._parse_params(prop_file.readlines())
        prop_file.close()
        expected_shape = (int(prop['force-segment-header']['num-points']),)
        channels = []
        for chan in prop['channels']['list']:
            chan_info = prop['channel'][chan]
            channels.append(self._zip_channel(zipfile, index, chan, chan_info))
            if channels[-1].shape != expected_shape:
                    raise NotImplementedError(
                        'Channel %d:%s in %s has strange shape %s != %s'
                        % (index, chan, zipfile.path,
                           channels[-1].shape, expected_shape))
        d = curve.Data(
            shape=(len(channels[0]), len(channels)),
            dtype=channels[0].dtype,
            info=self._zip_translate_segment_params(prop))
        for i,chan in enumerate(channels):
            d[:,i] = chan
        return self._zip_scale_segment(d, path, info)

    def _zip_channel(self, zipfile, segment_index, channel_name, chan_info):
        f = zipfile.open(os.path.join(
                'segments', str(segment_index),
                chan_info['data']['file']['name']), 'r')
        assert chan_info['data']['file']['format'] == 'raw', \
            'Non-raw data format:\n%s' % pprint.pformat(chan_info)
        assert chan_info['data']['type'] == 'float-data', \
            'Non-float data format:\n%s' % pprint.pformat(chan_info)
        data = numpy.frombuffer(
            buffer(f.read()),
            dtype=numpy.dtype(numpy.float32).newbyteorder('>'),
            # Is JPK data always big endian?  I can't find a config
            # setting.  The ForceRobot brochure
            #   http://www.jpk.com/forcerobot300-1.download.6d694150f14773dc76bc0c3a8a6dd0e8.pdf
            # lists a PowerPC chip on page 4, under Control
            # electronics, and PPCs are usually big endian.
            #   http://en.wikipedia.org/wiki/PowerPC#Endian_modes
            )
        f.close()
        return data

    def _zip_translate_params(self, params, chan_info):
        info = {
            'raw info':params,
            #'time':self._time_from_TODO(raw_info[]),
            }
        force_unit = chan_info['channel']['vDeflection']['conversion-set']['conversion']['force']['scaling']['unit']['unit']
        assert force_unit == 'N', force_unit
        force_base = chan_info['channel']['vDeflection']['conversion-set']['conversion']['force']['base-calibration-slot']
        assert force_base == 'distance', force_base
        dist_unit = chan_info['channel']['vDeflection']['conversion-set']['conversion']['distance']['scaling']['unit']['unit']
        assert dist_unit == 'm', dist_unit
        force_mult = float(
            chan_info['channel']['vDeflection']['conversion-set']['conversion']['force']['scaling']['multiplier'])
        info['spring constant (N/m)'] = force_mult
        return info

    def _zip_translate_segment_params(self, params):
        info = {
            'raw info':params,
            'columns':list(params['channels']['list']),
            'name':params['force-segment-header']['name']['name'],
            }
        if info['name'] in ['extend-spm', 'retract-spm', 'pause-at-end-spm']:
            info['name'] = info['name'][:-len('-spm')]
            if info['name'] == 'extend':
                info['name'] = 'approach'
        else:
            raise NotImplementedError(
                'Unrecognized segment type %s' % info['name'])
        return info

    def _zip_scale_segment(self, segment, path, info):
        data = curve.Data(
            shape=segment.shape,
            dtype=segment.dtype,
            info={})
        data[:,:] = segment
        segment.info['raw data'] = data

        # raw column indices
        channels = segment.info['raw info']['channels']['list']
        z_col = channels.index('height')
        d_col = channels.index('vDeflection')
        
        segment = self._zip_scale_channel(
            segment, z_col, 'calibrated', path, info)
        segment = self._zip_scale_channel(
            segment, d_col, 'distance', path, info)

        assert segment.info['columns'][z_col] == 'height (m)', \
            segment.info['columns'][z_col]
        assert segment.info['columns'][d_col] == 'vDeflection (m)', \
            segment.info['columns'][d_col]

        # scaled column indices same as raw column indices,
        # because columns is a copy of channels.list
        segment.info['columns'][z_col] = 'z piezo (m)'
        segment.info['columns'][d_col] = 'deflection (m)'
        return segment

    def _zip_scale_channel(self, segment, channel, conversion, path, info):
        channel_name = segment.info['raw info']['channels']['list'][channel]
        conversion_set = segment.info['raw info']['channel'][channel_name]['conversion-set']
        conversion_info = conversion_set['conversion'][conversion]
        if conversion_info['base-calibration-slot'] \
                != conversion_set['conversions']['base']:
            # Our conversion is stacked on a previous conversion.  Do
            # the previous conversion first.
            segment = self._zip_scale_channel(
                segment, channel, conversion_info['base-calibration-slot'],
                info, path)
        if conversion_info['type'] == 'file':
            key = ('%s_%s_to_%s_calibration_file'
                   % (channel_name,
                      conversion_info['base-calibration-slot'],
                      conversion))
            calib_path = conversion_info['file']
            if key in info:
                calib_path = os.path.join(os.path.dirname(path), info[key])
                self.logger().debug(
                    'Overriding %s -> %s calibration for %s channel: %s'
                    % (conversion_info['base-calibration-slot'],
                       conversion, channel_name, calib_path))
            if os.path.exists(calib_path):
                with file(calib_path, 'r') as f:
                    lines = [x.strip() for x in f.readlines()]
                    f.close()
                calib = {  # I've emailed JPK to confirm this file format.
                    'title':lines[0],
                    'multiplier':float(lines[1]),
                    'offset':float(lines[2]),
                    'unit':lines[3],
                    'note':'\n'.join(lines[4:]),
                    }
                segment[:,channel] = (segment[:,channel] * calib['multiplier']
                                      + calib['offset'])
                segment.info['columns'][channel] = (
                    '%s (%s)' % (channel_name, calib['unit']))
                return segment
            else:
                self.logger().warn(
                    'Skipping %s -> %s calibration for %s channel.  Calibration file %s not found'
                    % (conversion_info['base-calibration-slot'],
                       conversion, channel_name, calib_path))
        else:
            assert conversion_info['type'] == 'simple', conversion_info['type']
        assert conversion_info['scaling']['type'] == 'linear', \
            conversion_info['scaling']['type']
        assert conversion_info['scaling']['style'] == 'offsetmultiplier', \
            conversion_info['scaling']['style']
        multiplier = float(conversion_info['scaling']['multiplier'])
        offset = float(conversion_info['scaling']['offset'])
        unit = conversion_info['scaling']['unit']['unit']
        segment[:,channel] = segment[:,channel] * multiplier + offset
        segment.info['columns'][channel] = '%s (%s)' % (channel_name, unit)
        return segment

    def _parse_params(self, lines):
        info = {}
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                continue
            else:
                # e.g.: force-segment-header.type=xy-position-segment-header
                fields = line.split('=', 1)
                assert len(fields) == 2, line
                setting = fields[0].split('.')
                sub_info = info  # drill down, e.g. info['force-s..']['type']
                for s in setting[:-1]:
                    if s not in sub_info:
                        sub_info[s] = {}
                    sub_info = sub_info[s]
                if setting[-1] == 'list':  # split a space-delimited list
                    sub_info[setting[-1]] = fields[1].split(' ')
                else:
                    sub_info[setting[-1]] = fields[1]
        return info

    def _read_old(self, path, info):
        raise NotImplementedError('No old-style JPK files were available for testing, please send us yours: %s' % path)
