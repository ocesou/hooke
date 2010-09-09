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
>>> import os
>>> import os.path
>>> from hooke.hooke import Hooke, HookeRunner
>>> h = Hooke()
>>> r = HookeRunner()
>>> playlist = os.path.join('test', 'data', 'vclamp_jpk', 'playlist')
>>> h = r.run_lines(h, ['load_playlist ' + playlist]) # doctest: +ELLIPSIS
<FilePlaylist JPK>
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['curve_info']) # doctest: +ELLIPSIS, +REPORT_UDIFF
name: 2009.04.23-15.15.47.jpk
path: .../test/data/vclamp_jpk/2009.04.23-15.15.47.jpk
driver: <hooke.driver.jpk.JPKDriver object at 0x...>
note: None
command stack: []
blocks: 2
block names: ['approach', 'retract']
block sizes: [(4096, 6), (4096, 4)]
Success
<BLANKLINE>

Ensure that we can at least load each of the example curves.

>>> p = h.playlists.current()
>>> for i,curve in enumerate(p.items()):
...     print (i,
...            curve.info['raw info']['file-format-version'],
...            [d.info['name'] for d in curve.data]) # doctest: +REPORT_UDIFF
(0, '0.5', ['approach', 'retract'])
(1, '0.5', ['approach', 'pause', 'retract'])
(2, '0.2', ['pause-0', 'approach', 'pause-1', 'retract'])
(3, '0.12', ['approach', 'pause-0', 'retract', 'pause-1'])
(4, '0.2', ['pause-0', 'approach', 'pause-1', 'retract'])
(5, '0.12', ['approach', 'pause-0', 'retract', 'pause-1'])

Load each of the example segments in the :file:`Data1D` directory.

>>> driver = [d for d in h.drivers if d.name == 'jpk'][0]
>>> base_dir = os.path.join('test', 'data', 'vclamp_jpk', 'Data1D')
>>> for file_name in sorted(os.listdir(base_dir)):
...     path = os.path.join(base_dir, file_name)
...     print path
...     print driver.is_me(path)
...     data = driver.read(path)
...     print data.shape, data[:5], data[-5:]
...     # doctest: +ELLIPSIS, +REPORT_UDIFF
test/data/vclamp_jpk/Data1D/data1D-ConstantData1D-1282315524304.jpk-data1D
True
(128,) [  9.99999997e-07   9.99999997e-07   9.99999997e-07   9.99999997e-07
   9.99999997e-07] [  9.99999997e-07   9.99999997e-07   9.99999997e-07   9.99999997e-07
   9.99999997e-07]
test/data/vclamp_jpk/Data1D/data1D-MemoryFloatData1D-1282315524326.jpk-data1D
True
(128,) [  5.31691167e+36   5.31691167e+36   1.06338233e+37   1.59507347e+37
   2.12676467e+37] [ Inf  Inf  Inf  Inf  Inf]
test/data/vclamp_jpk/Data1D/data1D-MemoryIntegerData1D-1282315524320.jpk-data1D
True
(128,) [ 0.  0.  0.  0.  0.] [ 0.  0.  0.  0.  0.]
test/data/vclamp_jpk/Data1D/data1D-MemoryIntegerData1D-1282315524323.jpk-data1D
True
(128,) [ 0.  0.  0.  0.  0.] [ 0.  0.  0.  0.  0.]
test/data/vclamp_jpk/Data1D/data1D-MemoryShortData1D-1282315524313.jpk-data1D
True
(128,) [ 0.000511  0.000511  0.001022  0.001533  0.002044] [-0.002683 -0.002172 -0.001661 -0.00115  -0.000639]
test/data/vclamp_jpk/Data1D/data1D-MemoryShortData1D-1282315524316.jpk-data1D
True
(128,) [ 0.  0.  0.  0.  0.] [ 0.  0.  0.  0.  0.]
test/data/vclamp_jpk/Data1D/data1D-RasterData1D-1282315524283.jpk-data1D
True
(128,) [ 0.  1.  2.  3.  4.] [ 123.  124.  125.  126.  127.]

The data for the float and integer samples are not very convincing,
but appear to be correct.  I've emailed Michael Haggerty to confirm
the expected contents.
"""
