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
Test the commands listed in :file:`doc/tutorial.txt`.

>>> import os
>>> import os.path
>>> from uuid import uuid4
>>> from hooke.hooke import Hooke, HookeRunner
>>> h = Hooke()
>>> r = HookeRunner()
>>> h = r.run_lines(h, ['set_config conditions temperature 300.0'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_config conditions temperature'])
300.0
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['set_config conditions temperature 295.3'])
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['get_config conditions temperature'])
295.3
Success
<BLANKLINE>
>>> h = r.run_lines(h, ['print_config'])  # doctest: +ELLIPSIS
# Default environmental conditions in case they are not specified in
# the force curve data.  Configuration options in this section are
# available to every plugin.
[conditions]
# Temperature in Kelvin
temperature = 295.3
<BLANKLINE>
...
>>> file_name = '%s.cfg' % uuid4()
>>> config_already_exists = os.path.exists(file_name)
>>> config_already_exists
False
>>> h = r.run_lines(h, ['save_config --output %s' % file_name])
Success
<BLANKLINE>
>>> os.path.isfile(file_name)
True
>>> if config_already_exists == False:
...     os.remove(file_name)
"""
