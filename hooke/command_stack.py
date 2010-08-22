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

"""The ``command_stack`` module provides tools for managing and
executing stacks of :class:`~hooke.engine.CommandMessage`\s.
"""

import os
import os.path

import yaml

from .engine import CommandMessage


class CommandStack (list):
    """Store a stack of commands.

    Examples
    --------
    >>> c = CommandStack([CommandMessage('CommandA', {'param':'A'})])
    >>> c.append(CommandMessage('CommandB', {'param':'B'}))
    >>> c.append(CommandMessage('CommandA', {'param':'C'}))
    >>> c.append(CommandMessage('CommandB', {'param':'D'}))

    Implement a dummy :meth:`execute_command` for testing.

    >>> def execute_cmd(hooke, command_message, stack=None):
    ...     cm = command_message
    ...     print 'EXECUTE', cm.command, cm.arguments
    >>> c.execute_command = execute_cmd

    >>> c.execute(hooke=None)  # doctest: +ELLIPSIS
    EXECUTE CommandA {'param': 'A'}
    EXECUTE CommandB {'param': 'B'}
    EXECUTE CommandA {'param': 'C'}
    EXECUTE CommandB {'param': 'D'}

    :meth:`filter` allows you to select which commands get executed.
    If, for example, you are applying a set of commands to the current
    :class:`~hooke.curve.Curve`, you may only want to execute
    instances of :class:`~hooke.plugin.curve.CurveCommand`.  Here we
    only execute commands named `CommandB`.
    
    >>> def filter(hooke, command_message):
    ...     return command_message.command == 'CommandB'

    Apply the stack to the current curve.

    >>> c.execute(hooke=None, filter=filter)  # doctest: +ELLIPSIS
    EXECUTE CommandB {'param': 'B'}
    EXECUTE CommandB {'param': 'D'}

    Execute a new command and add it to the stack.

    >>> cm = CommandMessage('CommandC', {'param':'E'})
    >>> c.execute_command(hooke=None, command_message=cm)
    EXECUTE CommandC {'param': 'E'}
    >>> c.append(cm)
    >>> print [repr(cm) for cm in c]  # doctest: +NORMALIZE_WHITESPACE
    ['<CommandMessage CommandA {param: A}>',
     '<CommandMessage CommandB {param: B}>',
     '<CommandMessage CommandA {param: C}>',
     '<CommandMessage CommandB {param: D}>',
     '<CommandMessage CommandC {param: E}>']

    The data-type is also pickleable, which ensures we can move it
    between processes with :class:`multiprocessing.Queue`\s and easily
    save it to disk.  We must remove the unpickleable dummy executor
    before testing though.

    >>> c.execute_command  # doctest: +ELLIPSIS
    <function execute_cmd at 0x...>
    >>> del(c.__dict__['execute_command'])
    >>> c.execute_command  # doctest: +ELLIPSIS
    <bound method CommandStack.execute_command of ...>
    
    Lets also attach a child command message to demonstrate recursive
    serialization (we can't append `c` itself because of
    `Python issue 1062277`_).

    .. _Python issue 1062277: http://bugs.python.org/issue1062277

    >>> import copy
    >>> c.append(CommandMessage('CommandD', {'param': copy.deepcopy(c)}))

    Run the pickle (and YAML) tests.

    >>> import pickle
    >>> s = pickle.dumps(c)
    >>> z = pickle.loads(s)
    >>> print '\\n'.join([repr(cm) for cm in c]
    ...     )  # doctest: +NORMALIZE_WHITESPACE,
    <CommandMessage CommandA {param: A}>
    <CommandMessage CommandB {param: B}>
    <CommandMessage CommandA {param: C}>
    <CommandMessage CommandB {param: D}>
    <CommandMessage CommandC {param: E}>
    <CommandMessage CommandD {param:
      [<CommandMessage CommandA {param: A}>,
       <CommandMessage CommandB {param: B}>,
       <CommandMessage CommandA {param: C}>,
       <CommandMessage CommandB {param: D}>,
       <CommandMessage CommandC {param: E}>]}>
    >>> import yaml
    >>> print yaml.dump(c)
    !!python/object/new:hooke.command_stack.CommandStack
    listitems:
    - !!python/object:hooke.engine.CommandMessage
      arguments: {param: A}
      command: CommandA
    - !!python/object:hooke.engine.CommandMessage
      arguments: {param: B}
      command: CommandB
    - !!python/object:hooke.engine.CommandMessage
      arguments: {param: C}
      command: CommandA
    - !!python/object:hooke.engine.CommandMessage
      arguments: {param: D}
      command: CommandB
    - !!python/object:hooke.engine.CommandMessage
      arguments: {param: E}
      command: CommandC
    - !!python/object:hooke.engine.CommandMessage
      arguments:
        param: !!python/object/new:hooke.command_stack.CommandStack
          listitems:
          - !!python/object:hooke.engine.CommandMessage
            arguments: {param: A}
            command: CommandA
          - !!python/object:hooke.engine.CommandMessage
            arguments: {param: B}
            command: CommandB
          - !!python/object:hooke.engine.CommandMessage
            arguments: {param: C}
            command: CommandA
          - !!python/object:hooke.engine.CommandMessage
            arguments: {param: D}
            command: CommandB
          - !!python/object:hooke.engine.CommandMessage
            arguments: {param: E}
            command: CommandC
      command: CommandD
    <BLANKLINE>

    There is also a convenience function for clearing the stack.

    >>> c.clear()
    >>> print [repr(cm) for cm in c]
    []

    YAMLize a curve argument.

    >>> from .curve import Curve
    >>> c.append(CommandMessage('curve info', {'curve': Curve(path=None)}))
    >>> print yaml.dump(c)
    !!python/object/new:hooke.command_stack.CommandStack
    listitems:
    - !!python/object:hooke.engine.CommandMessage
      arguments:
        curve: !!python/object:hooke.curve.Curve {}
      command: curve info
    <BLANKLINE>
    """
    def execute(self, hooke, filter=None, stack=False):
        """Execute a stack of commands.

        See Also
        --------
        execute_command, filter
        """
        if filter == None:
            filter = self.filter
        for command_message in self:
            if filter(hooke, command_message) == True:
                self.execute_command(
                    hooke=hooke, command_message=command_message, stack=stack)

    def filter(self, hooke, command_message):
        """Return `True` to execute `command_message`, `False` otherwise.

        The default implementation always returns `True`.
        """
        return True

    def execute_command(self, hooke, command_message, stack=False):
        arguments = dict(command_message.arguments)
        arguments['stack'] = stack
        hooke.run_command(command=command_message.command,
                          arguments=arguments)

    def clear(self):
        while len(self) > 0:
            self.pop()


class FileCommandStack (CommandStack):
    """A file-backed :class:`CommandStack`.
    """
    version = '0.1'

    def __init__(self, *args, **kwargs):
        super(FileCommandStack, self).__init__(*args, **kwargs)
        self.name = self.path = None

    def __setstate__(self, state):
        self.name = self.path = None
        for key,value in state.items():
            setattr(self, key, value)
        self.set_path(state.get('path', None))

    def set_path(self, path):
        """Set the path (and possibly the name) of the command  stack.

        Examples
        --------
        >>> c = FileCommandStack([CommandMessage('CommandA', {'param':'A'})])

        :attr:`name` is set only if it starts out equal to `None`.
        >>> c.name == None
        True
        >>> c.set_path(os.path.join('path', 'to', 'my', 'command', 'stack'))
        >>> c.path
        'path/to/my/command/stack'
        >>> c.name
        'stack'
        >>> c.set_path(os.path.join('another', 'path'))
        >>> c.path
        'another/path'
        >>> c.name
        'stack'
        """
        if path != None:
            self.path = path
            if self.name == None:
                self.name = os.path.basename(path)

    def save(self, path=None, makedirs=True):
        """Saves the command stack to `path`.
        """
        self.set_path(path)
        dirname = os.path.dirname(self.path) or '.'
        if makedirs == True and not os.path.isdir(dirname):
            os.makedirs(dirname)
        with open(self.path, 'w') as f:
            f.write(self.flatten())

    def load(self, path=None):
        """Load a command stack from `path`.
        """
        self.set_path(path)
        with open(self.path, 'r') as f:
            text = f.read()
        self.from_string(text)

    def flatten(self):
        """Create a string representation of the command stack.

        A playlist is a YAML document with the following syntax::

            - arguments: {param: A}
              command: CommandA
            - arguments: {param: B, ...}
              command: CommandB
            ...

        Examples
        --------
        >>> c = FileCommandStack([CommandMessage('CommandA', {'param':'A'})])
        >>> c.append(CommandMessage('CommandB', {'param':'B'}))
        >>> c.append(CommandMessage('CommandA', {'param':'C'}))
        >>> c.append(CommandMessage('CommandB', {'param':'D'}))
        >>> print c.flatten()
        - arguments: {param: A}
          command: CommandA
        - arguments: {param: B}
          command: CommandB
        - arguments: {param: C}
          command: CommandA
        - arguments: {param: D}
          command: CommandB
        <BLANKLINE>
        """
        return yaml.dump([{'command':cm.command,'arguments':cm.arguments}
                          for cm in self])

    def from_string(self, string):
        """Load a playlist from a string.

        .. warning:: This is *not safe* with untrusted input.

        Examples
        --------

        >>> string = '''- arguments: {param: A}
        ...   command: CommandA
        ... - arguments: {param: B}
        ...   command: CommandB
        ... - arguments: {param: C}
        ...   command: CommandA
        ... - arguments: {param: D}
        ...   command: CommandB
        ... '''
        >>> c = FileCommandStack()
        >>> c.from_string(string)
        >>> print [repr(cm) for cm in c]  # doctest: +NORMALIZE_WHITESPACE
        ['<CommandMessage CommandA {param: A}>',
         '<CommandMessage CommandB {param: B}>',
         '<CommandMessage CommandA {param: C}>',
         '<CommandMessage CommandB {param: D}>']
        """
        for x in yaml.load(string):
            self.append(CommandMessage(command=x['command'],
                                       arguments=x['arguments']))
