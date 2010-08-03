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

"""The `interaction` module provides :class:`Request`,
:class:`Response`, an related classes for handling user interaction
through the
:class:`hooke.engine.CommandEngine`/:class:`hooke.ui.UserInterface`
connection.
"""


class InList (list):
    """:class:`Request` validator class.

    Examples
    --------

    >>> i = InList(['abc', 'def', 5, True])
    >>> i('abc')
    >>> i(5)
    >>> i(False)
    Traceback (most recent call last):
      ...
    ValueError: False
    """
    def __init__(self, *args, **kwargs):
        list.__init__(self, *args, **kwargs)

    def __call__(self, value):
        """Raises ValueError if a given `value` is not in our internal
        list.
        """
        if value not in self:
            raise ValueError(value)

class Interaction (object):
    """Mid-command inter-process interaction.

    Stores :attr:`type`, a string representing the interaction type
    ('boolean', 'string', ...).
    """
    def __init__(self, type):
        self.type = type

class Request (Interaction):
    """Command engine requests for information from the UI.

    >>> r = Request('test', 'Does response_class work?')
    >>> r.response_class()    
    <class 'hooke.interaction.Response'>
    """
    def __init__(self, type, msg, default=None, validator=None):
        super(Request, self).__init__(type)
        self.msg = msg
        self.default = default
        self.validator = validator

    def response_class(self):
        class_name = self.__class__.__name__.replace('Request', 'Response')
        return globals()[class_name]

    def response(self, value):
        if self.validator != None:
            self.validator(value)
        return self.response_class()(value)

class Response (Interaction):
    """UI response to a :class:`Request`.
    """
    def __init__(self, type, value):
        super(Response, self).__init__(type)
        self.value = value

class BooleanRequest (Request):
    def __init__(self, msg, default=None):
        super(BooleanRequest, self).__init__(
            'boolean', msg, default,
            validator = InList([True, False, default]))

class BooleanResponse (Response):
    def __init__(self, value):
        super(BooleanResponse, self).__init__('boolean', value)

class StringRequest (Request):
    def __init__(self, msg, default=None):
        super(StringRequest, self).__init__('string', msg, default)

class StringResponse (Response):
    def __init__(self, value):
        super(StringResponse, self).__init__('string', value)

class FloatRequest (Request):
    def __init__(self, msg, default=None):
        super(FloatRequest, self).__init__('float', msg, default)

class FloatResponse (Response):
    def __init__(self, value):
        super(FloatResponse, self).__init__('float', value)

class SelectionRequest (Request):
    def __init__(self, msg, default=None, options=[]):
        super(SelectionRequest, self).__init__('selection', msg, default)
        self.options = options

class SelectionResponse (Response):
    def __init__(self, value):
        super(SelectionResponse, self).__init__('selection', value)

class PointRequest (Request):
    def __init__(self, msg, curve, block=0, default=None):
        super(PointRequest, self).__init__('point', msg, default)
        self.curve = curve
        self.block = block

class PointResponse (Response):
    def __init__(self, value):
        super(PointResponse, self).__init__('point', value)


class Notification (object):
    def __init__(self, type):
        self.type = type

class ReloadUserInterfaceConfig (Notification):
    def __init__(self, config):
        super(ReloadUserInterfaceConfig, self).__init__(
            'reload user interface config')
        self.config = config
