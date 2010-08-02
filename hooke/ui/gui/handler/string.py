# Copyright

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

