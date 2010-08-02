# Copyright (C) 2010 W. Trevor King <wking@drexel.edu>
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

"""Define useful encoding-extraction functions.
"""

import locale
import sys


def get_encoding():
    """Guess a useful input/output/filesystem encoding.

    Maybe we need seperate encodings for input/output and filesystem?
    Hmm.
    """
    encoding = locale.getpreferredencoding() or sys.getdefaultencoding()
    if sys.platform != 'win32' or sys.version_info[:2] > (2, 3):
        encoding = locale.getlocale(locale.LC_TIME)[1] or encoding
        # Python 2.3 on windows doesn't know about 'XYZ' alias for 'cpXYZ'
    return encoding

def get_input_encoding():
    "Guess the input encoding."
    return get_encoding()

def get_output_encoding():
    "Guess the output encoding."
    return get_encoding()

def get_filesystem_encoding():
    "Guess the filesystem encoding."
    return get_encoding()
