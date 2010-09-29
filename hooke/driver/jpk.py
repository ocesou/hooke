# Copyright (C) 2008-2010 Massimo Sandal <devicerandom@gmail.com>
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

"""Driver for JPK ForceRobot's velocity clamp data format.

This driver is based on JPK's :file:`JPKForceSpec.txt` version 0.12.
The specs are freely available from JPK, just email support@jpk.com.
"""

import os.path
import pprint
import zipfile

import numpy

from .. import curve as curve
from ..util.util import Closing as Closing
from ..util.si import join_data_label, split_data_label
from . import Driver as Driver


def slash_join(*args):
    r"""Join path components with forward slashes regardless of OS.

    Notes
    -----
    From the `PKZIP Application Note`_, section J (Explanation of fields):

      file name: (Variable)

        ... All slashes should be forward slashes ``/`` as opposed to
        backwards slashes ``\`` for compatibility with Amiga and UNIX
        file systems etc. ...

    .. _PKZIP Application Note:
      http://www.pkware.com/documents/casestudies/APPNOTE.TXT

    Examples
    --------

    >>> sep = os.path.sep
    >>> os.path.sep = '/'
    >>> print slash_join('abc', 'def/ghi', 'jkl\\mno')
    abc/def/ghi/jkl\mno
    >>> os.path.sep = '\\'
    >>> print slash_join('abc', 'def/ghi', 'jkl\\mno')
    abc/def/ghi/jkl\mno
    >>> os.path.sep = sep

    Note that when :const:`os.path.sep` is ``/`` (e.g. UNIX),
    ``def/ghi`` is a compound segment, but when :const:`os.path.sep`
    is ``\`` (e.g. Windows), ``def/ghi`` is a single segment.
    """
    sep = os.path.sep
    try:
        os.path.sep = '/'
        return os.path.join(*args)
    finally:
        os.path.sep = sep


class JPKDriver (Driver):
    """Handle JPK ForceRobot's data format.
    """
    def __init__(self):
        super(JPKDriver, self).__init__(name='jpk')

    def is_me(self, path):
        if os.path.isdir(path):
            return False
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
            version = zip_info['file-format-version']
            if zip_info['jpk-data-file'] == 'jpk-data1D-file':
                return self._zip_read_1d(
                    f, path, info, zip_info, version)
            elif zip_info['jpk-data-file'] != 'spm-forcefile':
                raise ValueError('unrecognized JPK file type "%s"'
                                 % zip_info['jpk-data-file'])
            segments = []
            for i in range(len([p for p in f.namelist()
                                if p.endswith('segment-header.properties')])):
                segments.append(self._zip_segment(
                        f, path, info, zip_info, i, version))
        if version not in ['0.%d' % i for i in range(13)]:
            raise NotImplementedError(
                'JPK file version %s not supported (yet).' % version)
        curve_info = self._zip_translate_params(
            zip_info, segments[0].info['raw info'], version)
        for segment in segments:  # HACK, should use curve-level spring constant
            for key in ['spring constant (N/m)',
                        'z piezo sensitivity (m/V)']:
                if key in curve_info:
                    segment.info['spring constant (N/m)'] = \
                        curve_info['spring constant (N/m)']
        names = [segment.info['name'] for segment in segments]
        for name in set(names):  # ensure unique names
            count = names.count(name)
            if count > 1:
                i = 0
                for j,n in enumerate(names):
                    if n == name:
                        segments[j].info['name'] += '-%d' % i
                        i += 1
        return (segments, curve_info)

    def _zip_info(self, zipfile):
        with Closing(zipfile.open('header.properties')) as f:
            info = self._parse_params(f.readlines())
            return info

    def _zip_segment(self, zipfile, path, info, zip_info, index, version):
        with Closing(zipfile.open(slash_join(
                    'segments', str(index), 'segment-header.properties'))
                     ) as f:
            prop = self._parse_params(f.readlines())
        expected_shape = (int(prop['force-segment-header']['num-points']),)
        channels = []
        if 'list' not in prop['channels']:
            prop['channels'] = {'list': prop['channels'].split()}
        for chan in prop['channels']['list']:
            chan_info = prop['channel'][chan]
            channels.append(self._zip_channel(
                    zipfile, index, chan, chan_info))
            if channels[-1].shape != expected_shape:
                raise NotImplementedError(
                    'channel %d:%s in %s has strange shape %s != %s'
                    % (index, chan, zipfile.path,
                       channels[-1].shape, expected_shape))
        if len(channels) > 0:
            shape = (len(channels[0]), len(channels))
            dtype = channels[0].dtype
        else:  # no channels for this data block
            shape = (0,0)
            dtype = numpy.float32
        d = curve.Data(
            shape=shape,
            dtype=dtype,
            info=self._zip_translate_segment_params(prop))
        for i,chan in enumerate(channels):
            d[:,i] = chan
        return self._zip_scale_segment(d, path, info, version)

    def _zip_channel(self, zipfile, segment_index, channel_name, chan_info):
        if chan_info['data']['type'] in ['constant-data', 'raster-data']:
            return self._zip_calculate_channel(chan_info)
        with Closing(zipfile.open(slash_join(
                    'segments', str(segment_index),
                    chan_info['data']['file']['name']), 'r')) as f:
            assert chan_info['data']['file']['format'] == 'raw', \
                'non-raw data format:\n%s' % pprint.pformat(chan_info)
            dtype = self._zip_channel_dtype(chan_info)
            data = numpy.frombuffer(
                buffer(f.read()),
                dtype=dtype,)
        if dtype.kind in ['i', 'u']:
            data = self._zip_channel_decode(data, chan_info)
        return data

    def _zip_calculate_channel(self, chan_info):
        type_ = chan_info['data']['type']
        n = int(chan_info['data']['num-points'])
        if type_ == 'constant-data':
            return float(chan_info['data']['value'])*numpy.ones(
                shape=(n,),
                dtype=numpy.float32)
        elif type_ == 'raster-data':
            start = float(chan_info['data']['start'])
            step = float(chan_info['data']['step'])
            return numpy.arange(
                start=start,
                stop=start + step*(n-0.5),
                step=step,
                dtype=numpy.float32)
        else:
            raise ValueError('unrecognized data format "%s"' % type_)

    def _zip_channel_dtype(self, chan_info):
        type_ = chan_info['data']['type']
        if type_ in ['float-data', 'float']:
            dtype = numpy.dtype(numpy.float32)
        elif type_ in ['integer-data', 'memory-integer-data']:
            encoder = chan_info['data']['encoder']['type']
            if encoder in ['signedinteger', 'signedinteger-limited']:
                dtype = numpy.dtype(numpy.int32)
            elif encoder in ['unsignedinteger', 'unsignedinteger-limited']:
                dtype = numpy.dtype(numpy.uint32)
            else:
                raise ValueError('unrecognized encoder type "%s" for "%s" data'
                                 % (encoder, type_))
        elif type_ in ['short-data', 'short', 'memory-short-data']:
            encoder = chan_info['data']['encoder']['type']
            if encoder in ['signedshort', 'signedshort-limited']:
                dtype = numpy.dtype(numpy.int16)
            elif encoder in ['unsignedshort', 'unsignedshort-limited']:
                dtype = numpy.dtype(numpy.uint16)
            else:
                raise ValueError('unrecognized encoder type "%s" for "%s" data'
                                 % (encoder, type_))
        else:
            raise ValueError('unrecognized data format "%s"' % type_)
        byte_order = '>'
        # '>' (big endian) byte order.
        # From version 0.3 of JPKForceSpec.txt in the "Binary data" section:
        #    All forms of raw data are stored in chronological order
        #    (the order in which they were collected), and the
        #    individual values are stored in network byte order
        #    (big-endian). The data type used to store the data is
        #    specified by the "channel.*.data.type" property, and is
        #    either short (2 bytes per value), integer (4 bytes), or
        #    float (4 bytes, IEEE format).
        return dtype.newbyteorder(byte_order)

    def _zip_channel_decode(self, data, encoder_info):
        return self._zip_apply_channel_scaling(
            data, encoder_info['data']['encoder'])

    def _zip_translate_params(self, params, chan_info, version):
        info = {
            'raw info':params,
            #'time':self._time_from_TODO(raw_info[]),
            }
        if len(chan_info['channels']['list']) == 0:
            return info
        force_unit = self._zip_unit(
            chan_info['channel']['vDeflection']['conversion-set']['conversion']['force']['scaling'],
            version)
        assert force_unit == 'N', force_unit
        force_base = chan_info['channel']['vDeflection']['conversion-set']['conversion']['force']['base-calibration-slot']
        assert force_base == 'distance', force_base
        dist_unit = self._zip_unit(
            chan_info['channel']['vDeflection']['conversion-set']['conversion']['distance']['scaling'],
            version)
        assert dist_unit == 'm', dist_unit
        distance_base = chan_info['channel']['vDeflection']['conversion-set']['conversion']['distance']['base-calibration-slot']
        assert distance_base == 'volts', distance_base
        base_conversion = chan_info['channel']['vDeflection']['conversion-set']['conversions']['base']
        assert base_conversion == distance_base, base_conversion
        if 'encoder' in chan_info['channel']['vDeflection']['data']:
            distance_base_unit = self._zip_unit(
                chan_info['channel']['vDeflection']['data']['encoder']['scaling'],
                version)
        else:
            distance_base_unit = self._zip_unit(
                chan_info['channel']['vDeflection']['data'],
                version)
        assert distance_base_unit == 'V', distance_base_unit
        force_mult = float(
            chan_info['channel']['vDeflection']['conversion-set']['conversion']['force']['scaling']['multiplier'])
        sens_mult = float(
            chan_info['channel']['vDeflection']['conversion-set']['conversion']['distance']['scaling']['multiplier'])
        info['spring constant (N/m)'] = force_mult
        info['z piezo sensitivity (m/V)'] = sens_mult
        return info

    def _zip_translate_segment_params(self, params):
        info = {
            'raw info': params,
            'columns': list(params['channels']['list']),
            'name': self._zip_segment_name(params),
            }
        return info

    def _zip_segment_name(self, params):
        name = params['force-segment-header']['name']['name']
        if name.endswith('-spm'):
            name = name[:-len('-spm')]
        if name == 'extend':
            name = 'approach'
        elif name.startswith('pause-at-'):
            name = 'pause'
        return name

    def _zip_scale_segment(self, segment, path, info, version):
        data = curve.Data(
            shape=segment.shape,
            dtype=segment.dtype,
            info={})
        data[:,:] = segment
        segment.info['raw data'] = data

        # raw column indices
        channels = segment.info['raw info']['channels']['list']
        for i,channel in enumerate(channels):
            conversion = None
            if channel == 'vDeflection':
                conversion = 'distance'
            segment = self._zip_scale_channel(
                segment, channel, conversion=conversion,
                path=path, info=info, version=version)
            name,unit = split_data_label(segment.info['columns'][i])
            if name == 'vDeflection':
                assert unit == 'm', segment.info['columns'][i]
                segment.info['columns'][i] = join_data_label('deflection', 'm')
                # Invert because deflection voltage increases as the
                # tip moves away from the surface, but it makes more
                # sense to me to have it increase as it moves toward
                # the surface (positive tension on the protein chain).
                segment[:,i] *= -1
            elif name == 'height':
                assert unit == 'm', segment.info['columns'][i]
                segment.info['columns'][i] = join_data_label('z piezo', 'm')
        return segment

    def _zip_scale_channel(self, segment, channel_name,
                           conversion=None, path=None, info={}, version=None):
        channel = segment.info['raw info']['channels']['list'].index(
            channel_name)
        conversion_set = segment.info['raw info']['channel'][channel_name]['conversion-set']
        if conversion == None:
            conversion = conversion_set['conversions']['default']
        if conversion == conversion_set['conversions']['base']:
            segment.info['columns'][channel] = join_data_label(
                channel_name,
                self._zip_unit(
                    segment.info['raw info']['channel'][channel_name]['data'],
                    version))
            return segment
        conversion_info = conversion_set['conversion'][conversion]
        if conversion_info['base-calibration-slot'] \
                != conversion_set['conversions']['base']:
            # Our conversion is stacked on a previous conversion.  Do
            # the previous conversion first.
            segment = self._zip_scale_channel(
                segment, channel_name,
                conversion_info['base-calibration-slot'],
                path=path, info=info, version=version)
        if conversion_info['type'] == 'file':
            # Michael Haggerty at JPK points out that the conversion
            # information stored in the external file is reproduced in
            # the force curve file.  So there is no need to actually
            # read `conversion_info['file']`.  In fact, the data there
            # may have changed with future calibrations, while the
            # information stored directly in conversion_info retains
            # the calibration information as it was when the experiment
            # was performed.
            pass  # Fall through to 'simple' conversion processing.
        else:
            assert conversion_info['type'] == 'simple', conversion_info['type']
        segment[:,channel] = self._zip_apply_channel_scaling(
            segment[:,channel], conversion_info)
        unit = self._zip_unit(conversion_info['scaling'], version)
        segment.info['columns'][channel] = join_data_label(channel_name, unit)
        return segment

    def _zip_apply_channel_scaling(self, channel_data, conversion_info):
        assert conversion_info['scaling']['type'] == 'linear', \
            conversion_info['scaling']['type']
        assert conversion_info['scaling']['style'] == 'offsetmultiplier', \
            conversion_info['scaling']['style']
        multiplier = float(conversion_info['scaling']['multiplier'])
        offset = float(conversion_info['scaling']['offset'])
        return channel_data * multiplier + offset

    def _zip_unit(self, conversion_info, version):
        if version in ['0.%d' % i for i in range(3)]:
            return conversion_info['unit']
        else:
            return conversion_info['unit']['unit']

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
                    if fields[1]:
                        sub_info[setting[-1]] = fields[1].split(' ')
                    else:
                        sub_info[setting[-1]] = []
                else:
                    sub_info[setting[-1]] = fields[1]
        return info

    def _zip_read_1d(self, zipfile, path, info, zip_info, version):
        expected_shape = (int(zip_info['data']['num-points']),)
        if zip_info['data']['type'] in ['constant-data', 'raster-data']:
            return self._zip_calculate_channel(zip_info)
        with Closing(zipfile.open(
                zip_info['data']['file']['name'], 'r')) as f:
            assert zip_info['data']['file']['format'] == 'raw', \
                'non-raw data format:\n%s' % pprint.pformat(chan_info)
            dtype = self._zip_channel_dtype(zip_info)
            data = numpy.frombuffer(
                buffer(f.read()),
                dtype=dtype,)
            if dtype.kind in ['i', 'u']:
                data = self._zip_channel_decode(data, zip_info)
        if data.shape != expected_shape:
            raise NotImplementedError(
                'channel %s has strange shape %s != %s'
                % (path, data.shape, expected_shape))
        d = curve.Data(
            shape=data.shape,
            dtype=data.dtype,
            info=zip_info)
        d[:] = data
        return d

    def _read_old(self, path, info):
        raise NotImplementedError(
            "Early JPK files (pre-zip) are not supported by Hooke.  Please "
            "use JPK's `out2jpk-force` script to convert your old files "
            "(%s) to a more recent format before loading them with Hooke."
            % path)
