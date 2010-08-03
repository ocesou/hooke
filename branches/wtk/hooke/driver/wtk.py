# Copyright (C) 2010 W. Trevor King <wking@drexel.edu>
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

"""Driver for W. Trevor King's velocity clamp data format.

See my related projects:

* http://www.physics.drexel.edu/~wking/code/git/git.php?p=unfold_protein.git
* http://www.physics.drexel.edu/~wking/code/git/git.php?p=calibrate_cantilever.git
* http://www.physics.drexel.edu/~wking/code/git/git.php?p=data_logger.git
* http://www.physics.drexel.edu/~wking/code/git/git.php?p=piezo.git
* http://www.physics.drexel.edu/~wking/code/git/git.php?p=pycomedi.git

And the deprecated projects (which Hooke replaces):

* http://www.physics.drexel.edu/~wking/code/git/git.php?p=scale_unfold.git
* http://www.physics.drexel.edu/~wking/code/git/git.php?p=sawmodel.git
"""

import calendar
import copy
import os
import os.path
import re
import time

import numpy

from .. import curve as curve
from .. import experiment as experiment
from ..config import Setting
from . import Driver as Driver

try:
    import calibcant.config
    calibcant_dir = calibcant.config.LOG_DIR
except ImportError:
    calibcant_dir = None

try:
    import data_logger
except ImportError:
    data_logger = None


class WTKDriver (Driver):
    """Handle W. Trevor King's data_logger data format.
    """
    def __init__(self):
        super(WTKDriver, self).__init__(name='wtk')

    def default_settings(self):
        return [
            Setting(section=self.setting_section, help=self.__doc__),
            Setting(section=self.setting_section,
                    option='cantilever calibration directory',
                    value=calibcant_dir,
                    help='Set the directory where cantilever calibration data is stored'),
            ]

    def is_me(self, path):
        if not path.endswith('_unfold'):
            return False
        for p in self._paths(path):
            if not os.path.isfile(p):
                return False
        return True

    def read(self, path, info=None):
        approach_path,retract_path,param_path = self._paths(path)

        unlabeled_approach_data = numpy.loadtxt(
            approach_path, dtype=numpy.uint16)
        unlabeled_retract_data = numpy.loadtxt(
            retract_path, dtype=numpy.uint16)
        params = self._read_params(param_path)
        params = self._translate_params(params)

        # move data into Data blocks.
        approach = self._scale_block(
            unlabeled_approach_data, params, 'approach')
        retract = self._scale_block(
            unlabeled_retract_data, params, 'retract')
        info = {'filetype':self.name, 'experiment':experiment.VelocityClamp}
        return ([approach, retract], info)

    def _paths(self, path):
        return (path+'_approach', path, path+'_param')

    def _read_params(self, param_path):
        params = {}
        for line in file(param_path):
            ldata = [x.strip() for x in line.split(':', 1)]
            if ldata[0] == 'Data fields':
                params['columns'] = ldata[1].split()
            elif len(ldata) == 2:
                argwords = ldata[1].split()
                if ldata[0] == 'Time' or len(argwords) != 1:
                    params[ldata[0]] = ldata[1]
                else:  # single word probably a number
                    params[ldata[0]] = float(ldata[1])
            else:
                pass  # ignore comment lines
        return params

    def _translate_params(self, params):
        ret = {'raw info':params,}

        t = params['Time'] # 20100504135849
        ret['time'] = self._time_from_localtime_string(t)

        assert params['columns'] == ['Z_piezo_out', 'Deflection_in', 'Z_piezo_in'], \
            'Unexpected columns: %s' % ret['columns']
        ret['columns'] = ['z piezo (m)', 'deflection (m)', ]

        calibcant_file = self._find_previous_cantilever_calibration_file(
            ret['time'])
        calibcant_info = self._read_cantilever_calibration_file(calibcant_file)
        ret['raw spring constant'] = calibcant_info
        ret['spring constant (N/m)'] = calibcant_info['Cantilever k (N/m)']
        ret['deflection sensitivity (m/V)'] = \
            1.0/numpy.sqrt(calibcant_info['photoSensitivity**2 (V/nm)**2'])

        # (32768 bits = 2**15 bits = 10 Volts)
        ret['deflection sensitivity (V/bit)'] = 1.0/3276.8
        ret['deflection range (V)'] = 20.0
        ret['deflection offset (V)'] = 10.0  # assumes raw data is unsigned

        ret['z piezo sensitivity (V/bit)'] = 1.0/3276.8  # output volts / bit
        ret['z piezo range (V)'] = 20.0                  # output volts
        ret['z piezo offset (V)'] = 10.0  # output volts, assumes unsigned
        ret['z piezo gain'] = \
            params['Z piezo gain (Vp/Vo)']  # piezo volts / output volt
        ret['z piezo sensitivity (m/V)'] = \
            params['Z piezo sensitivity (nm/Vp)'] * 1e-9  # m / piezo volts
        
        return ret

    def _scale_block(self, data, info, name):
        """Convert the block from its native format to a `numpy.float`
        array in SI units.
        """
        ret = curve.Data(
            shape=(data.shape[0], 2),
            dtype=numpy.float,
            info=copy.deepcopy(info)
            )
        ret.info['name'] = name
        ret.info['raw data'] = data # store the raw data
        ret.info['columns'] = ['z piezo (m)', 'deflection (m)']

        # raw column indices
        # approach data does not have a Z_piezo_in column as of unfold v0.0.
        z_rcol = info['raw info']['columns'].index('Z_piezo_out')
        d_rcol = info['raw info']['columns'].index('Deflection_in')

        # scaled column indices
        z_scol = ret.info['columns'].index('z piezo (m)')
        d_scol = ret.info['columns'].index('deflection (m)')

        # Leading '-' because increasing voltage extends the piezo,
        # moving the tip towards the surface (positive indentation),
        # but it makes more sense to me to have it increase away from
        # the surface (positive separation).
        ret[:,z_scol] = -(
            (data[:,z_rcol].astype(ret.dtype)
             * info['z piezo sensitivity (V/bit)']
             - info['z piezo offset (V)'])
            * info['z piezo gain']
            * info['z piezo sensitivity (m/V)']
            )

        # Leading '-' because deflection voltage increases as the tip
        # moves away from the surface, but it makes more sense to me
        # to have it increase as it moves toward the surface (positive
        # tension on the protein chain).
        ret[:,d_scol] = -(
            (data[:,d_rcol]
             * info['deflection sensitivity (V/bit)']
             - info['deflection offset (V)'])
            * info['deflection sensitivity (m/V)']
            )

        return ret

    def _list_re_search(self, list, regexp):
        "Return list entries matching re"
        reg = re.compile(regexp)
        ret = []
        for item in list:
            if reg.match(item):
                ret.append(item)
        return ret

    def _list_cantilever_calibration_files(self, timestamp=None, basedir=None):
        if timestamp == None:
            timestamp = time.time()
        if basedir == None:
            basedir = self.config['cantilever calibration directory']
        YYYYMMDD = time.strftime("%Y%m%d", time.localtime(timestamp))
        dir = os.path.join(data_logger.normalize_logdir(basedir), YYYYMMDD)
        if not os.path.exists(dir):
            return []
        all_calibfiles = os.listdir(dir) # everything in the directory
        #regexp = "%s.*_analysis_text " % (YYYYMMDD)
        regexp = ".*_analysis_text"
        calibfiles = self._list_re_search(all_calibfiles, regexp)
        paths = [os.path.join(dir, cf) for cf in calibfiles]
        return paths

    def _calibfile_timestamp(self, path):
        filename = os.path.basename(path)
        YYYYMMDDHHMMSS = filename[0:14]
        return self._time_from_localtime_string(YYYYMMDDHHMMSS)

    def _find_previous_cantilever_calibration_file(
        self, timestamp=None, basedir=None, previous_days=1):
        """
        If timestamp == None, uses current time.
        Warning : brittle! depends on the default data_logger.py save filesystem.
        Renaming files or moving directories will break me.
        """
        #if FORCED_CANTILEVER_CALIBRATION_FILE != None:
        #    return FORCED_CANTILEVER_CALIBRATION_FILE
        calibfiles = []
        for i in range(previous_days+1):
            calibfiles.extend(self._list_cantilever_calibration_files(
                    timestamp-24*3600*i,basedir=basedir))
        assert len(calibfiles) > 0 , \
            "No calibration files in that day range in directory '%s'" % basedir
        calibfiles.sort()
        for i in range(len(calibfiles)):
            if self._calibfile_timestamp(calibfiles[i]) > timestamp:
                i -= 1
                break
        return calibfiles[i]

    def _read_cantilever_calibration_file(self, filename):
        ret = {'file': filename}
        line_re = re.compile('(.*) *: (.*) [+]/- (.*) \((.*)\)\n')
        for line in file(filename):
            match = line_re.match(line)
            if match == None:
                raise ValueError(
                    'Invalid cantilever calibration line in %s: %s'
                    % (filename, line))
            key,value,std_dev,rel_err = [
                x.strip() for x in match.group(*range(1,5))]
            if key == 'Variable (units)':
                continue # ignore the header line
            value = float(value)
            std_dev = float(std_dev)
            # Handle older calibcant output.
            if key == 'k (N/m)':
                key = 'Cantilever k (N/m)'
            elif key == 'a**2 (V/nm)**2':
                key = 'photoSensitivity**2 (V/nm)**2'
            ret[key] = value
            ret[key + ' (std. dev.)'] = std_dev
        return ret

    def _time_from_localtime_string(self, timestring, format="%Y%m%d%H%M%S"):
        """
        >>> print time.tzname
        ('EST', 'EDT')
        >>> d = WTKDriver()
        >>> d._time_from_localtime_string("19700101", format="%Y%m%d")/3600.0
        5.0
        >>> d._time_from_localtime_string("20081231", format="%Y%m%d")
        1230699600
        >>> d._time_from_localtime_string("20090101", format="%Y%m%d")
        1230786000
        """
        timestruct = time.strptime(timestring, format)
        timestamp = calendar.timegm(timestruct)
        # Date strings are in localtime, so what we really want is
        # .timelocale, but that doesn't exist.  Workaround to convert
        # timestamp to UTC.
        timestamp += time.timezone # assume no Daylight Savings Time (DST)
        if bool(time.localtime(timestamp).tm_isdst) == True:
            timestamp -= time.timezone - time.altzone # correct if DST
        assert time.strftime(format, time.localtime(timestamp)) == timestring, "error in time_from_localtime_string, %s != %s" % (time.strftime(format, time.localtime(timestamp)), timestring)
        return timestamp
