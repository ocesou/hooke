# Copyright (C) 2008-2010 Alberto Gomez-Casado
#                         Massimo Sandal <devicerandom@gmail.com>
#                         W. Trevor King <wking@drexel.edu>
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

"""The ``command_stack`` module provides :class:`CommandStackPlugin`
and several associated :class:`~hooke.command.Command`\s exposing
:mod`hooke.command_stack`'s functionality.
"""

import logging
import os.path
from Queue import Queue

from ..command import Command, Argument, Success, Failure
from ..command_stack import FileCommandStack
from ..config import Setting
from ..engine import CloseEngine, CommandMessage
from . import Builtin


# Define useful command subclasses

class CommandStackCommand (Command):
    """Subclass to avoid pushing control commands to the stack.
    """
    def __init__(self, *args, **kwargs):
        super(CommandStackCommand, self).__init__(*args, **kwargs)
        stack = [a for a in self.arguments if a.name == 'stack'][0]
        stack.default = False

    def _set_state(self, state):
        try:
            self.plugin.set_state(state)
        except ValueError, e:
            self.plugin.log('raising error: %s' % e)
            raise Failure('invalid state change: %s' % e.state_change)


class CaptureCommand (CommandStackCommand):
    """Run a mock-engine and save the incoming commands.

    Notes
    -----
    Due to limitations in the --script and --command option
    implementations in ./bin/hooke, capture sessions will die at the
    end of the script and command execution before entering
    --persist's interactive session.
    """
    def __init__(self, name, plugin):
        super(CaptureCommand, self).__init__(
            name=name, help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        # TODO: possibly merge code with CommandEngine.run()

        # Fake successful completion so UI continues sending commands.
        outqueue.put(Success())

        while True:
            msg = inqueue.get()
            if isinstance(msg, CloseEngine):
                outqueue.put('CloseEngine')
                inqueue.put(msg)  # Put CloseEngine back for CommandEngine.
                self._set_state('inactive')
                return
            assert isinstance(msg, CommandMessage), type(msg)
            cmd = hooke.command_by_name[msg.command]
            if (msg.explicit_user_call == False
                or isinstance(cmd, CommandStackCommand)):
                if isinstance(cmd, StopCaptureCommand):
                    outqueue = Queue()  # Grab StopCaptureCommand's completion.
                cmd.run(hooke, inqueue, outqueue, **msg.arguments)
                if isinstance(cmd, StopCaptureCommand):
                    assert self.plugin.state == 'inactive', self.plugin.state
                    # Return the stolen completion as our own.
                    raise outqueue.get(block=False)
            else:
                self.plugin.log('appending %s' % msg)
                self.plugin.command_stack.append(msg)
                # Fake successful completion so UI continues sending commands.
                outqueue.put(Success())


# The plugin itself

class CommandStackPlugin (Builtin):
    """Commands for managing a command stack (similar to macros).
    """
    def __init__(self):
        super(CommandStackPlugin, self).__init__(name='command_stack')
        self._commands = [
            StartCaptureCommand(self), StopCaptureCommand(self),
	    ReStartCaptureCommand(self),
            PopCommand(self), GetCommand(self), GetStateCommand(self),
	    SaveCommand(self), LoadCommand(self), ExecuteCommand(self),
	    ]
        self._settings = [
            Setting(section=self.setting_section, help=self.__doc__),
            Setting(section=self.setting_section, option='path',
                    value=os.path.join('resources', 'command_stack'),
                    help='Directory containing command stack files.'), # TODO: allow colon separated list, like $PATH.
            ]
	self.command_stack = FileCommandStack()
        self.state = 'inactive'
        # inactive <-> active.
        self._valid_transitions = {
            'inactive': ['active'],
            'active': ['inactive'],
            }

    def default_settings(self):
        return self._settings

    def log(self, msg):
        log = logging.getLogger('hooke')
        log.debug('%s %s' % (self.name, msg))

    def set_state(self, state):
        state_change = '%s -> %s' % (self.state, state)
        self.log('changing state: %s' % state_change)
        if state not in self._valid_transitions[self.state]:
            e = ValueError(state)
            e.state_change = state_change
            raise e
        self.state = state


# Define commands

class StartCaptureCommand (CaptureCommand):
    """Clear any previous stack and run the mock-engine.
    """
    def __init__(self, plugin):
        super(StartCaptureCommand, self).__init__(
            name='start command capture', plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        self._set_state('active')
        self.plugin.command_stack = FileCommandStack()  # clear command stack
        super(StartCaptureCommand, self)._run(hooke, inqueue, outqueue, params)


class ReStartCaptureCommand (CaptureCommand):
    """Run the mock-engine.
    """
    def __init__(self, plugin):
        super(ReStartCaptureCommand, self).__init__(
            name='restart command capture', plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        self._set_state('active')
        super(ReStartCaptureCommand, self)._run(hooke, inqueue, outqueue, params)


class StopCaptureCommand (CommandStackCommand):
    """Stop the mock-engine.
    """
    def __init__(self, plugin):
        super(StopCaptureCommand, self).__init__(
            name='stop command capture', help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        self._set_state('inactive')


class PopCommand (CommandStackCommand):
    """Pop the top command off the stack.
    """
    def __init__(self, plugin):
        super(PopCommand, self).__init__(
            name='pop command from stack', help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        outqueue.put(self.plugin.command_stack.pop())


class GetCommand (CommandStackCommand):
    """Return the command stack.
    """
    def __init__(self, plugin):
        super(GetCommand, self).__init__(
            name='get command stack', help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        outqueue.put(self.plugin.command_stack)

class GetStateCommand (CommandStackCommand):
    """Return the mock-engine state.
    """
    def __init__(self, plugin):
        super(GetStateCommand, self).__init__(
            name='get command capture state', help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        outqueue.put(self.plugin.state)


class SaveCommand (CommandStackCommand):
    """Save the command stack.
    """
    def __init__(self, plugin):
        super(SaveCommand, self).__init__(
            name='save command stack',
            arguments=[
                Argument(name='output', type='file',
                         help="""
File name for the output command stack.  Defaults to overwriting the
input command stack.  If the command stack does not have an input file
(e.g. it is the default) then the file name defaults to `default`.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        params = self._setup_params(hooke, params)
        self.plugin.command_stack.save(params['output'])

    def _setup_params(self, hooke, params):
        if params['output'] == None and self.plugin.command_stack.path == None:
            params['output'] = 'default'
        if params['output'] != None:
            params['output'] = os.path.join(
                self.plugin.config['path'], params['output'])
        return params

class LoadCommand (CommandStackCommand):
    """Load the command stack.

    .. warning:: This is *not safe* with untrusted input.
    """
    def __init__(self, plugin):
        super(LoadCommand, self).__init__(
            name='load command stack',
            arguments=[
                Argument(name='input', type='file',
                         help="""
File name for the input command stack.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        params = self._setup_params(hooke, params)
        self.plugin.command_stack.clear()
        self.plugin.command_stack.load(params['input'])

    def _setup_params(self, hooke, params):
        if params['input'] == None and self.plugin.command_stack.path == None:
            params['input'] = 'default'
        if params['input'] != None:
            params['input'] = os.path.join(
                self.plugin.config['path'], params['input'])
        return params


class ExecuteCommand (Command):
    """Execute a :class:`~hooke.command_stack.CommandStack`.
    """
    def __init__(self, plugin):
        super(ExecuteCommand, self).__init__(
            name='execute command stack',
            arguments=[
                Argument(name='commands', type='command stack',
                         help="""
Command stack to apply to each curve.  Defaults to the plugin's
current stack.
""".strip()),
                ],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        params = self._setup_params(hooke=hooke, params=params)
        if len(params['commands']) == 0:
            return
        params['commands'].execute(hooke=hooke, stack=params['stack'])

    def _setup_params(self, hooke, params):
        if params['commands'] == None:
            params['commands'] = self.plugin.command_stack
        return params
