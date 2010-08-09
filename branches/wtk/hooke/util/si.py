# Copyright (C) 2010 Massimo Sandal <devicerandom@gmail.com>
#                    Rolf Schmidt <rschmidt@alcor.concordia.ca>
#                    W. Trevor King <wking@drexel.edu>
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

"""Define functions for handling numbers in SI notation.

Notes
-----
To output a scale, choose any value on the axis and find the
multiplier and prefix for it.  Use those to format the rest of the
scale.  As values can span several orders of magnitude, you have
to decide what units to use.

>>> xs = (985e-12, 1e-9, 112358e-12)

Get the power from the first (or last, or middle, ...) value

>>> p = get_power(xs[0])
>>> for x in xs:
...     print ppSI(x, decimals=2, power=p)
985.00 p
1000.00 p
112358.00 p
>>> print prefix_from_value(xs[0]) + 'N'
pN
"""

import math
from numpy import isnan
import re


PREFIX = {
    24: 'Y',
    21: 'Z',
    18: 'E',
    15: 'P',
    12: 'T',
    9: 'G',
    6: 'M',
    3: 'k',
    0: '',
    -3: 'm',
    -6: u'\u00B5',
    -9: 'n',
    -12: 'p',
    -15: 'f',
    -18: 'a',
    -21: 'z',
    -24: 'y',
    }
"""A dictionary of SI prefixes from 10**24 to 10**-24.

Examples
--------
>>> PREFIX[0]
''
>>> PREFIX[6]
'M'
>>> PREFIX[-9]
'n'
"""

_DATA_LABEL_REGEXP = re.compile('^([^(]*[^ ]) ?\(([^)]*)\)$')
"""Used by :func:`data_label_unit`.
"""


def ppSI(value, unit='', decimals=None, power=None, pad=False):
    """Pretty-print `value` in SI notation.

    The current implementation ignores `pad` if `decimals` is `None`.

    Examples
    --------
    >>> x = math.pi * 1e-8
    >>> print ppSI(x, 'N')
    31.415927 nN
    >>> print ppSI(x, 'N', 3)
    31.416 nN
    >>> print ppSI(x, 'N', 4, power=-12)
    31415.9265 pN
    >>> print ppSI(x, 'N', 5, pad=True)
       31.41593 nN

    If you want the decimal indented by six spaces with `decimal=2`,
    `pad` should be the sum of

    * 6 (places before the decimal point)
    * 1 (length of the decimal point)
    * 2 (places after the decimal point)

    >>> print ppSI(-x, 'N', 2, pad=(6+1+2))
       -31.42 nN
    """
    if value == 0:
        return '0'
    if isnan(value):
        return 'NaN'

    if power == None:  # auto-detect power
        power = get_power(value)

    if decimals == None:
        format = lambda n: '%f' % n
    else:
        if pad == False:  # no padding
            format = lambda n: '%.*f' % (decimals, n)            
        else:
            if pad == True:  # auto-generate pad
                # 1 for ' ', 1 for '-', 3 for number, 1 for '.', and decimals.
                pad = 6 + decimals
            format = lambda n: '%*.*f' % (pad, decimals, n)
    return '%s %s%s' % (format(value / pow(10,power)), PREFIX[power], unit)


def get_power(value):
    """Return the SI power for which `0 <= |value|/10**pow < 1000`. 
    
    Exampes
    -------
    >>> get_power(0)
    0
    >>> get_power(123)
    0
    >>> get_power(-123)
    0
    >>> get_power(1e8)
    6
    >>> get_power(1e-16)
    -18
    """
    if value != 0 and not isnan(value):
        # get log10(|value|)
        value_temp = math.floor(math.log10(math.fabs(value)))
        # reduce the log10 to a multiple of 3
        return int(value_temp - (value_temp % 3))
    else:
        return 0

def prefix_from_value(value):
    """Determine the SI power of `value` and return its prefix.

    Examples
    --------
    >>> prefix_from_value(0)
    ''
    >>> prefix_from_value(1e10)
    'G'
    """
    return PREFIX[get_power(value)]

def join_data_label(name, unit):
    """Create laels for `curve.data[i].info['columns']`.

    See Also
    --------
    split_data_label

    Examples
    --------
    >>> join_data_label('z piezo', 'm')
    'z piezo (m)'
    >>> join_data_label('deflection', 'N')
    'deflection N'
    """
    return '%s (%s)' % (name, unit)

def split_data_label(label):
    """Split `curve.data[i].info['columns']` labels into `(name, unit)`.

    See Also
    --------
    join_data_label

    Examples
    --------
    >>> split_data_label('z piezo (m)')
    ('z piezo', 'm')
    >>> split_data_label('deflection (N)')
    ('deflection', 'N')
    """
    m = _DATA_LABEL_REGEXP.match(label)
    assert m != None, label
    return m.groups()
