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

"""The `system` module provides :class:`SystemPlugin` and several
associated :class:`hooke.command.Command`\s for interacting with the
operating system and execution environment.
"""

import os
import os.path
import subprocess
import sys

from ..command import Command, Argument
from . import Builtin


class SystemPlugin (Builtin):
    def __init__(self):
        super(SystemPlugin, self).__init__(name='system')
        self._commands = [
            ListDirectoryCommand(self), GetWorkingDirectoryCommand(self),
            ChangeDirectoryCommand(self), SystemCommand(self)]


class ListDirectoryCommand (Command):
    """List the files in a directory.
    """
    def __init__(self, plugin):
        super(ListDirectoryCommand, self).__init__(
            name='ls', aliases=['dir'],
            arguments=[
                Argument(
    name='path', type='path', default='.',
    help="""
Path to the directory whose contents get listed.  Defaults to the
current working directory.
""".strip()),
],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
	outqueue.put('\n'.join(sorted(os.listdir(params['path']))))

class GetWorkingDirectoryCommand (Command):
    """Get the current working directory.
    """
    def __init__(self, plugin):
        super(GetWorkingDirectoryCommand, self).__init__(
            name='cwd', aliases=['pwd'], help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
	outqueue.put(os.getcwd())

class ChangeDirectoryCommand (Command):
    """Change the current working directory.
    """
    def __init__(self, plugin):
        super(ChangeDirectoryCommand, self).__init__(
            name='cd',
            arguments=[
                Argument(
    name='path', type='path', default='~',
    help="""
Path of the directory to change into.  Default to the user's home
directory.
""".strip()),
],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        os.chdir(os.path.expanduser(params['path']))

class SystemCommand (Command):
    """Execute a system command and report the output.
    """
    def __init__(self, plugin):
        super(SystemCommand, self).__init__(
            name='system',
            arguments=[
                Argument(
    name='command', type='string', optional=False, count=-1,
    help="""
Command line to execute.
""".strip()),
],
            help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        p = subprocess.Popen(
            params['command'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout,stderr = p.communicate()
        returncode = p.wait()
        outqueue.put(stdout)
        outqueue.put(stderr)
