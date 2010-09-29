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

"""Define :class:`FloatHandler` to handle
:class:`~hooke.interaction.FloatRequest`\s.
"""

from . import Handler


class FloatHandler (object):
    def __init__(self):
        super(FloatHandler, self).__init__(name='float')

    def _float_request_prompt(self, msg):
        return self._string_request_prompt(msg)

    def _float_request_parser(self, msg, resposne):
        return float(response)
