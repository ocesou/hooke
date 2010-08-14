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
We run this test in a temporary directory for easy cleanup.

>>> import os
>>> import shutil
>>> import tempfile
>>> temp_dir = tempfile.mkdtemp(prefix='tmp-hooke-')

>>> from hooke.hooke import Hooke, HookeRunner
>>> h = Hooke()
>>> r = HookeRunner()

Add add some commands to the stack.

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

Ensure we'll be saving in our temporary directory.

>>> target_dir = os.path.join(temp_dir, 'resources', 'command_stack')
>>> h = r.run_lines(h, ['set_config "command_stack plugin" path %s'
...                     % target_dir])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_command_stack'])  # doctest: +NORMALIZE_WHITESPACE
[<CommandMessage load playlist {input: test/data/test}>,
 <CommandMessage get curve>]
Success
<BLANKLINE>

Save the stack.

>>> h = r.run_lines(h, ['get_command_stack'])  # doctest: +NORMALIZE_WHITESPACE
[<CommandMessage load playlist {input: test/data/test}>,
 <CommandMessage get curve>]
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['save_command_stack'])
Success
<BLANKLINE>
>>> os.listdir(temp_dir)
['resources']
>>> os.listdir(target_dir)
['default']
>>> with open(os.path.join(target_dir, 'default'), 'r') as f:
...     print f.read()
- arguments: {input: !!python/unicode 'test/data/test'}
  command: load playlist
- arguments: {}
  command: get curve
<BLANKLINE>

You can also specify the name explicitly.

>>> h = r.run_lines(h, ['save_command_stack --output my_stack'])
Success
<BLANKLINE>
>>> sorted(os.listdir(target_dir))
['default', 'my_stack']
>>> with open(os.path.join(target_dir, 'my_stack'), 'r') as f:
...     print f.read()
- arguments: {input: !!python/unicode 'test/data/test'}
  command: load playlist
- arguments: {}
  command: get curve
<BLANKLINE>

Further saves overwrite the last save/load path by default.

>>> h = r.run_lines(h, ['restart_command_capture',
...                     'curve_info',
...                     'stop_command_capture'])  # doctest: +REPORT_UDIFF
Success
<BLANKLINE>
Success
<BLANKLINE>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['save_command_stack'])
Success
<BLANKLINE>
>>> with open(os.path.join(target_dir, 'default'), 'r') as f:
...     print f.read()
- arguments: {input: !!python/unicode 'test/data/test'}
  command: load playlist
- arguments: {}
  command: get curve
<BLANKLINE>
>>> with open(os.path.join(target_dir, 'my_stack'), 'r') as f:
...     print f.read()
- arguments: {input: !!python/unicode 'test/data/test'}
  command: load playlist
- arguments: {}
  command: get curve
- arguments: {}
  command: curve info
<BLANKLINE>

But starting command capture (which clears the stack), reverts the
default save name to `default`.

>>> h = r.run_lines(h, ['start_command_capture',
...                     'version',
...                     'stop_command_capture'])  # doctest: +REPORT_UDIFF
Success
<BLANKLINE>
Success
<BLANKLINE>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['save_command_stack'])
Success
<BLANKLINE>
>>> with open(os.path.join(target_dir, 'default'), 'r') as f:
...     print f.read()
- arguments: {}
  command: version
<BLANKLINE>

Clear the stack so loading behavior is more obvious.

>>> h = r.run_lines(h, ['start_command_capture',
...                     'stop_command_capture'])  # doctest: +REPORT_UDIFF
Success
<BLANKLINE>
Success
<BLANKLINE>

Loading is just the inverse of saving.

>>> h = r.run_lines(h, ['load_command_stack'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_command_stack'])
[<CommandMessage version>]
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['load_command_stack --input my_stack'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_command_stack'])  # doctest: +NORMALIZE_WHITESPACE
[<CommandMessage load playlist {input: test/data/test}>,
 <CommandMessage get curve>,
 <CommandMessage curve info>]
Success
<BLANKLINE>

Now that the current stack's name is `my_stack`, that will be the
default stack loaded if you `load_command_stack` without `--input`.

>>> with open(os.path.join(target_dir, 'my_stack'), 'w') as f:
...     f.write('\\n'.join([
...             '- arguments: {}',
...             '  command: debug',
...             '']))
>>> h = r.run_lines(h, ['load_command_stack'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_command_stack'])  # doctest: +NORMALIZE_WHITESPACE
[<CommandMessage debug>]
Success
<BLANKLINE>

Cleanup the temporary directory.

>>> shutil.rmtree(temp_dir)
"""
