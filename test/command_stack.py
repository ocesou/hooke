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

"""
>>> import logging
>>> import sys
>>> from hooke.hooke import Hooke, HookeRunner
>>> h = Hooke()
>>> r = HookeRunner()

The command stack starts off empty.

>>> h = r.run_lines(h, ['get_command_stack'])
[]
Success
<BLANKLINE>

And inactive, so you can't stop it.

>>> h = r.run_lines(h, ['get_command_capture_state'])
inactive
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['stop_command_capture'])
Failure
invalid state change: inactive -> inactive

Because :meth:`hooke.hooke.HookeRunner.run_lines` spawns and closes
its own engine subprocess, we need to run the whole capture session in
a single call.  The command stack, on the other hand, will be
preserved between calls.

You can't restart recording.

>>> h = r.run_lines(h, ['start_command_capture',
...                     'get_command_capture_state',
...                     'start_command_capture',
...                     'restart_command_capture'])  # doctest: +REPORT_UDIFF
Success
<BLANKLINE>
active
Success
<BLANKLINE>
Failure
invalid state change: active -> active
Failure
invalid state change: active -> active

But you can stop and restart.

>>> h = r.run_lines(h, ['start_command_capture',
...                     'stop_command_capture',
...                     'restart_command_capture'])  # doctest: +REPORT_UDIFF
Success
<BLANKLINE>
Success
<BLANKLINE>
Success
<BLANKLINE>

Lets add some commands to the stack.

>>> h = r.run_lines(h, ['start_command_capture',
...                     'load_playlist test/data/test',
...                     'get_curve',
...                     'stop_command_capture'])  # doctest: +REPORT_UDIFF
Success
<BLANKLINE>
Success
<BLANKLINE>
Success
<BLANKLINE>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_command_stack'])  # doctest: +NORMALIZE_WHITESPACE
[<CommandMessage load playlist {input: test/data/test}>,
 <CommandMessage get curve>]
Success
<BLANKLINE>

When capture is stopped, command execution is normal.

>>> h = r.run_lines(h, ['restart_command_capture',
...                     'curve_info',
...                     'stop_command_capture',
...                     'version',
...                     'restart_command_capture',
...                     'previous_curve',
...                     'stop_command_capture']
...     )  # doctest: +ELLIPSIS, +REPORT_UDIFF
Success
<BLANKLINE>
Success
<BLANKLINE>
Success
<BLANKLINE>
Hooke 1.0.0.alpha (Ninken)
...
Success
<BLANKLINE>
Success
<BLANKLINE>
Success
<BLANKLINE>

You can pop commands regardless of the recording state.

>>> h = r.run_lines(h, ['pop_command_from_stack'])
<CommandMessage previous curve>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_command_stack'])  # doctest: +NORMALIZE_WHITESPACE
[<CommandMessage load playlist {input: test/data/test}>,
 <CommandMessage get curve>,
 <CommandMessage curve info>]
Success
<BLANKLINE>

>>> h = r.run_lines(h, ['restart_command_capture',
...                     'pop_command_from_stack',
...                     'get_command_stack',
...                     'stop_command_capture']
...     )  # doctest: +NORMALIZE_WHITESPACE, +REPORT_UDIFF
Success
<BLANKLINE>
<CommandMessage curve info>
Success
<BLANKLINE>
[<CommandMessage load playlist {input: test/data/test}>,
 <CommandMessage get curve>]
Success
<BLANKLINE>
Success
<BLANKLINE>

If you start up again (using `start` not `restart`), the stack is cleared.

>>> h = r.run_lines(h, ['start_command_capture',
...                     'stop_command_capture'])
Success
<BLANKLINE>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_command_stack'])
[]
Success
<BLANKLINE>

Building command stacks is fun, but its useless if you can't execute
them.  First, lets repopulate the in-memory stack.

>>> h = r.run_lines(h, ['start_command_capture',
...                     'debug --attribute config',
...                     'version',
...                     'stop_command_capture']
...     )  # doctest: +REPORT_UDIFF
Success
<BLANKLINE>
Success
<BLANKLINE>
Success
<BLANKLINE>
Success
<BLANKLINE>

Setup logging so we can check command output in the doctest.

>>> log = logging.getLogger('hooke')
>>> stdout_handler = logging.StreamHandler(sys.stdout)
>>> log.addHandler(stdout_handler)

Execute the stack.  We use `h.run_command` because `sys.stdout` is
replaced by a `doctest._SpoofOut`, and doctest has no way to collect
those results from `run_lines`'s engine subprocess.

>>> h.run_command('execute command stack', arguments={}
...     )  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE, +REPORT_UDIFF
engine running internal <CommandMessage execute command stack>
engine running internal <CommandMessage debug {attribute: config, ...}>
engine message from debug (<type 'instance'>):
 <hooke.config.HookeConfigParser instance at 0x...>
engine message from debug (<class 'hooke.command.Success'>):
engine running internal <CommandMessage version {...}>
engine message from version (<type 'str'>): Hooke 1.0.0.alpha (Ninken)
----
...
engine message from version (<class 'hooke.command.Success'>):
engine message from execute command stack (<class 'hooke.command.Success'>): 
"""
