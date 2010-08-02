# Copyright (C) 2010 W. Trevor King <wking@drexel.edu>
#
# This file is part of Hooke.
#
# Hooke is free software: you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# Hooke is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with Hooke.  If not, see
# <http://www.gnu.org/licenses/>.

"""Hooke integration tests.

Besides the unittests embedded in the Hooke code, we also want to
check the whole system against popular use cases.  This :mod:`test`
module can be scanned by ``nosetests`` in the ususal manner to run any
defined tests.

Because of the ``nosetests`` scanning, the working directory for all
tests is the Hooke source root directory.  If you change directories
during a test, be sure to change back to the original directory when
you're done.
"""
