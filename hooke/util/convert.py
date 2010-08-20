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

"""Type conversion utilities.
"""


ANALOGS = {
    'file': 'string',
    'path': 'string',
    'point': 'int',
    }
"""Types that may be treated as other types.

These types may have optional special handling on the UI end
(e.g. file picker dialogs), but it is not required.
"""

RAW_TYPES = [
    'curve',
    'dict',
    'driver',
    'function',
    'object',
    'playlist',
    ]
"""List of types that should not be converted.
"""

def to_string(value, type, count=1):
    """Convert `value` from `type` to a unicode string.
    """
    type = ANALOGS.get(type, type)
    if type in RAW_TYPES:
        return value
    if count != 1:
        values = [to_string(v, type) for v in value]
        return '[%s]' % ', '.join(values)
    return unicode(value)

def from_string(value, type, count=1):
    """Convert `value` from a string to `type`.

    Examples
    --------
    >>> from_string('abcde', type='string')
    u'abcde'
    >>> from_string('None', type='string')
    >>> from_string(None, type='string')
    >>> from_string('true', type='bool')
    True
    >>> from_string('false', type='bool')
    False
    >>> from_string(None, type='bool')
    False
    >>> from_string('123', type='int')
    123
    >>> from_string('123', type='float')
    123.0
    """
    type = ANALOGS.get(type, type)
    if type in RAW_TYPES:
        return value
    fn = globals()['_string_to_%s' % type]
    if count != 1:
        assert value.startswith('[') and value.endswith(']'), value
        value = value[1:-1]  # strip off brackets
        values = [from_string(v, type) for v in value.split(', ')]
        assert count == -1 or len(values) == count, (
            'array with %d != %d values: %s'
            % (len(values), count, values))
        return values
    return fn(value)

def _string_to_string(value):
    if value in [None, 'None'] or len(value) == 0:
        return None
    return unicode(value)

def _string_to_bool(value):
    return hasattr(value, 'lower') and value.lower() == 'true'

def _string_to_int(value):
    if value in [None, 'None']:
        return None
    return int(value)

def _string_to_float(value):
    if value in [None, 'None']:
        return None
    return float(value)
