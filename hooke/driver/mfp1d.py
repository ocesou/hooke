#!/usr/bin/env python

'''
mfp1d.py

Driver for MFP-1D files.

Copyright 2010 by Dr. Rolf Schmidt (Concordia University, Canada)
This driver is based on the work of R. Naud and A. Seeholzer (see below)
to read Igor binary waves. Code used with permission.

This program is released under the GNU General Public License version 2.
'''

# DEFINITION:
# Reads Igor's (Wavemetric) binary wave format, .ibw, files.
#
# ALGORITHM:
# Parsing proper to version 2, 3, or version 5 (see Technical notes TN003.ifn:
# http://mirror.optus.net.au/pub/wavemetrics/IgorPro/Technical_Notes/) and data
# type 2 or 4 (non complex, single or double precision vector, real values).
#
# AUTHORS:
# Matlab version: R. Naud August 2008 (http://lcn.epfl.ch/~naud/Home.html)
# Python port: A. Seeholzer October 2008
#
# VERSION: 0.1
#
# COMMENTS:
# Only tested for version 2 Igor files for now, testing for 3 and 5 remains to be done.
# More header data could be passed back if wished. For significance of ignored bytes see
# the technical notes linked above.

import numpy
import os.path
import struct

import lib.driver
import lib.curve
import lib.plot

__version__='0.0.0.20100225'

class mfp1dDriver(lib.driver.Driver):

    def __init__(self, filename):
        '''
        This is a driver to import Asylum Research MFP-1D data.
        Status: experimental
        '''
        self.data = []
        self.note = []
        self.retract_velocity = None
        self.spring_constant = None
        self.filename = filename

        self.filedata = open(filename,'rU')
        self.lines = list(self.filedata.readlines())
        self.filedata.close()

    def _load_from_file(self, filename, extract_note=False):
        data = None
        f = open(filename, 'rb')
        ####################### ORDERING
        # machine format for IEEE floating point with big-endian
        # byte ordering
        # MacIgor use the Motorola big-endian 'b'
        # WinIgor use Intel little-endian 'l'
        # If the first byte in the file is non-zero, then the file is a WinIgor
        firstbyte = struct.unpack('b', f.read(1))[0]
        if firstbyte == 0:
            format = '>'
        else:
            format = '<'
        #######################  CHECK VERSION
        f.seek(0)
        version = struct.unpack(format+'h', f.read(2))[0]
        #######################  READ DATA AND ACCOMPANYING INFO
        if version == 2 or version == 3:
            # pre header
            wfmSize = struct.unpack(format+'i', f.read(4))[0] # The size of the WaveHeader2 data structure plus the wave data plus 16 bytes of padding.
            noteSize = struct.unpack(format+'i', f.read(4))[0] # The size of the note text.
            if version==3:
                formulaSize = struct.unpack(format+'i', f.read(4))[0]
            pictSize = struct.unpack(format+'i', f.read(4))[0] # Reserved. Write zero. Ignore on read.
            checksum = struct.unpack(format+'H', f.read(2))[0] # Checksum over this header and the wave header.
            # wave header
            dtype = struct.unpack(format+'h', f.read(2))[0]
            if dtype == 2:
                dtype = numpy.float32(.0).dtype
            elif dtype == 4:
                dtype = numpy.double(.0).dtype
            else:
                assert False, "Wave is of type '%i', not supported" % dtype
            dtype = dtype.newbyteorder(format)

            ignore = f.read(4) # 1 uint32
            bname = self._flatten(struct.unpack(format+'20c', f.read(20)))
            ignore = f.read(4) # 2 int16
            ignore = f.read(4) # 1 uint32
            dUnits = self._flatten(struct.unpack(format+'4c', f.read(4)))
            xUnits = self._flatten(struct.unpack(format+'4c', f.read(4)))
            npnts = struct.unpack(format+'i', f.read(4))[0]
            amod = struct.unpack(format+'h', f.read(2))[0]
            dx = struct.unpack(format+'d', f.read(8))[0]
            x0 = struct.unpack(format+'d', f.read(8))[0]
            ignore = f.read(4) # 2 int16
            fsValid = struct.unpack(format+'h', f.read(2))[0]
            topFullScale = struct.unpack(format+'d', f.read(8))[0]
            botFullScale = struct.unpack(format+'d', f.read(8))[0]
            ignore = f.read(16) # 16 int8
            modDate = struct.unpack(format+'I', f.read(4))[0]
            ignore = f.read(4) # 1 uint32
            # Numpy algorithm works a lot faster than struct.unpack
            data = numpy.fromfile(f, dtype, npnts)

        elif version == 5:
            # pre header
            checksum = struct.unpack(format+'H', f.read(2))[0] # Checksum over this header and the wave header.
            wfmSize = struct.unpack(format+'i', f.read(4))[0] # The size of the WaveHeader2 data structure plus the wave data plus 16 bytes of padding.
            formulaSize = struct.unpack(format+'i', f.read(4))[0]
            noteSize = struct.unpack(format+'i', f.read(4))[0] # The size of the note text.
            dataEUnitsSize = struct.unpack(format+'i', f.read(4))[0]
            dimEUnitsSize = struct.unpack(format+'4i', f.read(16))
            dimLabelsSize = struct.unpack(format+'4i', f.read(16))
            sIndicesSize = struct.unpack(format+'i', f.read(4))[0]
            optionSize1 = struct.unpack(format+'i', f.read(4))[0]
            optionSize2 = struct.unpack(format+'i', f.read(4))[0]

            # header
            ignore = f.read(4)
            CreationDate =  struct.unpack(format+'I',f.read(4))[0]
            modData =  struct.unpack(format+'I',f.read(4))[0]
            npnts =  struct.unpack(format+'i',f.read(4))[0]
            # wave header
            dtype = struct.unpack(format+'h',f.read(2))[0]
            if dtype == 2:
                dtype = numpy.float32(.0).dtype
            elif dtype == 4:
                dtype = numpy.double(.0).dtype
            else:
                assert False, "Wave is of type '%i', not supported" % dtype
            dtype = dtype.newbyteorder(format)

            ignore = f.read(2) # 1 int16
            ignore = f.read(6) # 6 schar, SCHAR = SIGNED CHAR?         ignore = fread(fid,6,'schar'); #
            ignore = f.read(2) # 1 int16
            bname = self._flatten(struct.unpack(format+'32c',f.read(32)))
            ignore = f.read(4) # 1 int32
            ignore = f.read(4) # 1 int32
            ndims = struct.unpack(format+'4i',f.read(16)) # Number of of items in a dimension -- 0 means no data.
            sfA = struct.unpack(format+'4d',f.read(32))
            sfB = struct.unpack(format+'4d',f.read(32))
            dUnits = self._flatten(struct.unpack(format+'4c',f.read(4)))
            xUnits = self._flatten(struct.unpack(format+'16c',f.read(16)))
            fsValid = struct.unpack(format+'h',f.read(2))
            whpad3 = struct.unpack(format+'h',f.read(2))
            ignore = f.read(16) # 2 double
            ignore = f.read(40) # 10 int32
            ignore = f.read(64) # 16 int32
            ignore = f.read(6) # 3 int16
            ignore = f.read(2) # 2 char
            ignore = f.read(4) # 1 int32
            ignore = f.read(4) # 2 int16
            ignore = f.read(4) # 1 int32
            ignore = f.read(8) # 2 int32

            data = numpy.fromfile(f, dtype, npnts)
            note_str = f.read(noteSize)
            if extract_note:
                note_lines = note_str.split('\r')
                self.note = {}
                for line in note_lines:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        self.note[key] = value
                self.retract_velocity = float(self.note['RetractVelocity'])
                self.spring_constant = float(self.note['SpringC'])
        else:
            assert False, "Fileversion is of type '%i', not supported" % dtype
            data = []

        f.close()
        if len(data) > 0:
            data_list = data.tolist()
            count = len(data_list) / 2
            return data_list[:count - 1], data_list[count:]
        else:
            return None

    def _flatten(self, tup):
        out = ''
        for ch in tup:
            out += ch
        return out

    def _read_columns(self):
        extension = lib.curve.Data()
        retraction = lib.curve.Data()

        extension.y, retraction.y = self._load_from_file(self.filename, extract_note=True)
        filename = self.filename.replace('deflection', 'LVDT', 1)
        extension.x, retraction.x = self._load_from_file(filename, extract_note=False)
        return [[extension.x, extension.y], [retraction.x, retraction.y]]

    def close_all(self):
        self.filedata.close()

    def is_me(self):
        if os.path.isdir(path):
            return False
        if len(self.lines) < 34:
            return False

        name, extension = os.path.splitext(self.filename)
        #the following only exist in MFP1D files, not MFP-3D
        #PullDist, PullDistSign, FastSamplingFrequency, SlowSamplingFrequency, FastDecimationFactor
        #SlowDecimationFactor, IsDualPull, InitRetDist, RelaxDist, SlowTrigger, RelativeTrigger,
        #EndOfNote
        if extension == '.ibw' and 'deflection' in name:
            #check if the corresponding LVDT file exists
            filename = self.filename.replace('deflection', 'LVDT', 1)
            if os.path.isfile(filename) and 'EndOfNote' in self.lines:
                return True
            else:
                return False
        else:
            return False

    def default_plots(self):
        '''
        loads the curve data
        '''
        defl_ext, defl_ret = self.deflection()

        extension = lib.curve.Curve()
        retraction = lib.curve.Curve()

        extension.color = 'red'
        extension.label = 'extension'
        extension.style = 'plot'
        extension.title = 'Force curve'
        extension.units.x = 'm'
        extension.units.y = 'N'
        extension.x = self.data[0][0]
        extension.y = [i * self.spring_constant for i in defl_ext]
        retraction.color = 'blue'
        retraction.label = 'retraction'
        retraction.style = 'plot'
        retraction.title = 'Force curve'
        retraction.units.x = 'm'
        retraction.units.y = 'N'
        retraction.x = self.data[1][0]
        retraction.y = [i * self.spring_constant for i in defl_ret]

        plot = lib.plot.Plot()
        plot.title = os.path.basename(self.filename)
        plot.curves.append(extension)
        plot.curves.append(retraction)

        plot.normalize()
        return plot

    def deflection(self):
        if not self.data:
            self.data = self._read_columns()
        return self.data[0][1], self.data[1][1]
