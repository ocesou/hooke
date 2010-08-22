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

"""The `command` module provides :class:`Command`\s and
:class:`Argument`\s for defining commands.

It also provides :class:`CommandExit` and subclasses for communicating
command completion information between
:class:`hooke.engine.CommandEngine`\s and
:class:`hooke.ui.UserInterface`\s.
"""

import Queue as queue
import sys
import textwrap
import traceback


class CommandExit (Exception):
    pass

class Success (CommandExit):
    pass

class Exit (Success):
    """The command requests an end to the interpreter session.
    """
    pass

class Failure (CommandExit):
    pass

class UncaughtException (Failure):
    def __init__(self, exception, traceback_string=None):
        super(UncaughtException, self).__init__()
        if traceback_string == None:
            traceback_string = traceback.format_exc()
            sys.exc_clear()
        self.exception = exception
        self.traceback = traceback_string
        self.__setstate__(self.__getstate__())

    def __getstate__(self):
        """Return a picklable representation of the objects state.

        :mod:`pickle`'s doesn't call a :meth:`__init__` when
        rebuilding a class instance.  To preserve :attr:`args` through
        a pickle cycle, we use :meth:`__getstate__` and
        :meth:`__setstate__`.

        See `pickling class instances`_ and `pickling examples`_.

        .. _pickling class instances:
          http://docs.python.org/library/pickle.html#pickling-and-unpickling-normal-class-instances
        .. _pickling examples:
          http://docs.python.org/library/pickle.html#example
        """
        return {'exception':self.exception, 'traceback':self.traceback}

    def __setstate__(self, state):
        """Apply the picklable state from :meth:`__getstate__` to
        reconstruct the instance.
        """
        for key,value in state.items():
            setattr(self, key, value)
        self.args = (self.traceback + str(self.exception),)


class Command (object):
    """One-line command description here.

    >>> c = Command(name='test', help='An example Command.')
    >>> hooke = None
    >>> status = c.run(hooke, NullQueue(), PrintQueue(),
    ...                help=True) # doctest: +REPORT_UDIFF
    ITEM:
    Command: test
    <BLANKLINE>
    Arguments:
    <BLANKLINE>
    help BOOL (bool) Print a help message.
    stack BOOL (bool) Add this command to appropriate command stacks.
    <BLANKLINE>
    An example Command.
    ITEM:
    <BLANKLINE>
    """
    def __init__(self, name, aliases=None, arguments=[], help='',
                 plugin=None):
        # TODO: see_also=[other,command,instances,...]
        self.name = name
        if aliases == None:
            aliases = []
        self.aliases = aliases
        self.arguments = [
            Argument(name='help', type='bool', default=False, count=1,
                     help='Print a help message.'),
            Argument(name='stack', type='bool', default=True, count=1,
                     help='Add this command to appropriate command stacks.'),
            ] + arguments
        self._help = help
        self.plugin = plugin

    def run(self, hooke, inqueue=None, outqueue=None, **kwargs):
        """`Normalize inputs and handle <Argument help> before punting
        to :meth:`_run`.
        """
        if inqueue == None:
            inqueue = NullQueue()
        if outqueue == None:
            outqueue = NullQueue()
        try:
            params = self.handle_arguments(hooke, inqueue, outqueue, kwargs)
            if params['help'] == True:
                outqueue.put(self.help())
                raise(Success())
            self._run(hooke, inqueue, outqueue, params)
        except CommandExit, e:
            if isinstance(e, Failure):
                outqueue.put(e)
                return 1
            # other CommandExit subclasses fall through to the end
        except Exception, e:
            x = UncaughtException(e)
            outqueue.put(x)
            return 1
        else:
            e = Success()
        outqueue.put(e)
        return 0

    def _run(self, hooke, inqueue, outqueue, params):
        """This is where the command-specific magic will happen.
        """
        pass

    def handle_arguments(self, hooke, inqueue, outqueue, params):
        """Normalize and validate input parameters (:class:`Argument` values).
        """
        for argument in self.arguments:
            names = [argument.name] + argument.aliases
            settings = [(name,v) for name,v in params.items() if name in names]
            num_provided = len(settings)
            if num_provided == 0:
                if argument.optional == True or argument.count == 0:
                    settings = [(argument.name, argument.default)]
                else:
                    raise Failure('Required argument %s not set.'
                                  % argument.name)
            if num_provided > 1:
                raise Failure('Multiple settings for %s:\n  %s'
                    % (argument.name,
                       '\n  '.join(['%s: %s' % (name,value)
                                    for name,value in sorted(settings)])))
            name,value = settings[0]
            if num_provided == 0:
                params[argument.name] = value
            else:
                if name != argument.name:
                    params.remove(name)
                    params[argument.name] = value
            if argument.callback != None:
                value = argument.callback(hooke, self, argument, value)
                params[argument.name] = value
            argument.validate(value)
        return params

    def help(self, name_fn=lambda name:name):
        """Return a help message describing the `Command`.

        `name_fn(internal_name) -> external_name` gives calling
        :class:`hooke.ui.UserInterface`\s a means of changing the
        display names if it wants (e.g. to remove spaces from command
        line tokens).
        """
        name_part = 'Command: %s' % name_fn(self.name)
        if len(self.aliases) > 0:
            name_part += ' (%s)' % ', '.join(
                [name_fn(n) for n in self.aliases])
        parts = [name_part]
        if len(self.arguments) > 0:
            argument_part = ['Arguments:', '']
            for a in self.arguments:
                argument_part.append(textwrap.fill(
                        a.help(name_fn),
                        initial_indent="",
                        subsequent_indent="    "))
            argument_part = '\n'.join(argument_part)
            parts.append(argument_part)
        parts.append(self._help) # help part
        return '\n\n'.join(parts)

class Argument (object):
    """Structured user input for :class:`Command`\s.
    
    TODO: ranges for `count`?
    """
    def __init__(self, name, aliases=None, type='string', metavar=None,
                 default=None, optional=True, count=1,
                 completion_callback=None, callback=None, help=''):
        self.name = name
        if aliases == None:
            aliases = []
        self.aliases = aliases
        self.type = type
        if metavar == None:
            metavar = type.upper()
        self.metavar = metavar
        self.default = default
        self.optional = optional
        self.count = count
        self.completion_callback = completion_callback
        self.callback = callback
        self._help = help

    def __str__(self):
        return '<%s %s>' % (self.__class__.__name__, self.name)

    def __repr__(self):
        return self.__str__()

    def help(self, name_fn=lambda name:name):
        """Return a help message describing the `Argument`.

        `name_fn(internal_name) -> external_name` gives calling
        :class:`hooke.ui.UserInterface`\s a means of changing the
        display names if it wants (e.g. to remove spaces from command
        line tokens).
        """        
        parts = ['%s ' % name_fn(self.name)]
        if self.metavar != None:
            parts.append('%s ' % self.metavar)
        parts.extend(['(%s) ' % self.type, self._help])
        return ''.join(parts)

    def validate(self, value):
        """If `value` is not appropriate, raise `ValueError`.
        """
        pass # TODO: validation


# Useful callbacks

class StoreValue (object):
    def __init__(self, value):
        self.value = value
    def __call__(self, hooke, command, argument, fragment=None):
        return self.value

class NullQueue (queue.Queue):
    """The :class:`queue.Queue` equivalent of `/dev/null`.

    This is a bottomless pit.  Items go in, but never come out.
    """
    def get(self, block=True, timeout=None):
        """Raise queue.Empty.
        
        There's really no need to override the base Queue.get, but I
        want to know if someone tries to read from a NullQueue.  With
        the default implementation they would just block silently
        forever :(.
        """
        raise queue.Empty

    def put(self, item, block=True, timeout=None):
        """Dump an item into the void.

        Block and timeout are meaningless, because there is always a
        free slot available in a bottomless pit.
        """
        pass

class PrintQueue (NullQueue):
    """Debugging :class:`NullQueue` that prints items before dropping
    them.
    """
    def put(self, item, block=True, timeout=None):
        """Print `item` and then dump it into the void.
        """
        print 'ITEM:\n%s' % item
