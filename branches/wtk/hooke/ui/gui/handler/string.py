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

"""Define :class:`StringHandler` to handle
:class:`~hooke.interaction.StringRequest`\s.
"""

import wx

from . import Handler


class StringHandler (Handler):
    def __init__(self):
        super(StringHandler, self).__init__(name='string')

    def run(self, hooke_frame, msg):
        pass

    def _string_request_prompt(self, msg):
        if msg.default == None:
            d = ' '
        else:
            d = ' [%s] ' % msg.default
        return msg.msg + d

    def _string_request_parser(self, msg, response):
        return response.strip()
