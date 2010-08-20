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
>>> from hooke.command_stack import CommandStack
>>> from hooke.engine import CommandMessage
>>> from hooke.hooke import Hooke
>>> h = Hooke()

Setup logging so we can check command output in the doctest.

>>> log = logging.getLogger('hooke')
>>> stdout_handler = logging.StreamHandler(sys.stdout)
>>> log.addHandler(stdout_handler)

Setup a playlist to act on.

>>> h.run_command('load playlist',
...     {'input': 'test/data/vclamp_picoforce/playlist'})  # doctest: +ELLIPSIS
engine running internal <CommandMessage load playlist {input: test/data/vclamp_picoforce/playlist}>
engine message from load playlist (<class 'hooke.playlist.FilePlaylist'>): <FilePlaylist ...>
engine message from load playlist (<class 'hooke.command.Success'>): 
>>> stack = CommandStack([
...         CommandMessage('get curve'),
...         CommandMessage('zero surface contact point'),
...         ])

Test `apply command stack to playlist`.

>>> h.run_command('apply command stack to playlist',
...     {'commands': stack, 'evaluate': True})  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE, +REPORT_UDIFF
engine running internal <CommandMessage apply command stack to playlist
  {commands: [<CommandMessage get curve>,
              <CommandMessage zero surface contact point>],
   evaluate: True}>
loading curve 20071120a_i27_t33.100 with driver ...
engine running internal <CommandMessage execute command stack {...}>
engine running internal <CommandMessage get curve {stack: True}>
engine message from get curve (<class 'hooke.curve.Curve'>): <Curve 20071120a_i27_t33.100>
engine message from get curve (<class 'hooke.command.Success'>): 
engine running internal <CommandMessage zero surface contact point {...}>
engine message from zero surface contact point (<type 'dict'>): {...}
engine message from zero surface contact point (<class 'hooke.command.Success'>): 
engine message from execute command stack (<class 'hooke.command.Success'>): 
loading curve 20071120a_i27_t33.101 with driver ...
engine running internal <CommandMessage execute command stack {...}>
engine running internal <CommandMessage get curve {stack: True}>
engine message from get curve (<class 'hooke.curve.Curve'>): <Curve 20071120a_i27_t33.101>
engine message from get curve (<class 'hooke.command.Success'>): 
engine running internal <CommandMessage zero surface contact point {...}>
engine message from zero surface contact point (<type 'dict'>): {...}
engine message from zero surface contact point (<class 'hooke.command.Success'>): 
engine message from execute command stack (<class 'hooke.command.Success'>): 
loading curve 20071120a_i27_t33.102 with driver ...

...
loading curve 20071120a_i27_t33.199 with driver ...
engine running internal <CommandMessage execute command stack {...}>
engine running internal <CommandMessage get curve {stack: True}>
engine message from get curve (<class 'hooke.curve.Curve'>): <Curve 20071120a_i27_t33.199>
engine message from get curve (<class 'hooke.command.Success'>): 
engine running internal <CommandMessage zero surface contact point {...}>
engine message from zero surface contact point (<type 'dict'>): {...}
engine message from zero surface contact point (<class 'hooke.command.Success'>): 
engine message from execute command stack (<class 'hooke.command.Success'>): 
loading curve 0x06130001 with driver ...
unloading curve 20071120a_i27_t33.100
engine running internal <CommandMessage execute command stack
  {commands: [<CommandMessage get curve>,
              <CommandMessage zero surface contact point>],
   curve: ...}>
engine running internal <CommandMessage get curve {stack: True}>
...
engine message from apply command stack to playlist (<class 'hooke.command.Success'>): 
>>> curve = h.playlists.current().current(
...     )  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE
loading curve 20071120a_i27_t33.100 with driver ...
engine running internal <CommandMessage zero surface contact point
  {block: None, curve: <Curve 20071120a_i27_t33.100>, ...}>
engine message from zero surface contact point (<type 'dict'>): {...}
engine message from zero surface contact point (<class 'hooke.command.Success'>): 
unloading curve 20071120a_i27_t33.102
>>> curve
<Curve 20071120a_i27_t33.100>
>>> curve.command_stack  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE
[<CommandMessage zero surface contact point
    {block: None, curve: <Curve 20071120a_i27_t33.100>, ...}>]

Test `apply command stack to playlist` without evaluating.

>>> stack = CommandStack([
...         CommandMessage('flat_filter_peaks --block retract --min_points 1'),
...         ])
>>> h.run_command('apply command stack to playlist',
...     {'commands': stack, 'evaluate': False}
...     )  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE, +REPORT_UDIFF
engine running internal
  <CommandMessage apply command stack to playlist {...}>
unloading curve 20071120a_i27_t33.100
unloading curve 20071120a_i27_t33.101
unloading curve 20071120a_i27_t33.102
...
unloading curve 20071120a_i27_t33.199
unloading curve 0x06130001
unloading curve 0x07200000
engine message from apply command stack to playlist
  (<class 'hooke.command.Success'>): 
>>> for c in curve.command_stack:
...     print c  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE, +REPORT_UDIFF
<CommandMessage zero surface contact point
  {..., curve: <Curve 20071120a_i27_t33.100>...}>
<CommandMessage flat_filter_peaks --block retract --min_points 1>

Test `clear curve command stack`.

>>> h.run_command('clear curve command stack', arguments={})
engine running internal <CommandMessage clear curve command stack>
engine message from clear curve command stack (<class 'hooke.command.Success'>): 
>>> curve.command_stack
[]
"""
