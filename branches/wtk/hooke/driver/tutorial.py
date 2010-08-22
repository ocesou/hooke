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

"""Tutorial driver for Hooke.

This example driver explains driver construction.
"""

"""
Here we define a simple file format that is read by this driver. The
file format is as following::

    TUTORIAL_FILE
    PLOT1
    X1
    n1   <- ?
    n2
    ...
    nN
    Y1
    n1
    n2
    ...
    nN
    X2
    n1
    n2
    ..
    nN
    Y2
    n1
    n2
    ..
    nN
    PLOT2
    X1
    ...
    Y1
    ...
    X2
    ...
    Y2
    ...
    END

that is, two plots with two datasets each.
"""

import os.path

# The following are relative imports.  See PEP 328 for details
#   http://www.python.org/dev/peps/pep-0328/
from .. import curve as curve # this module defines data containers.
from .. import experiment as experiment # this module defines expt. types
from ..config import Setting # configurable setting class
from . import Driver as Driver # this is the Driver base class

# The driver must inherit from the parent
# :class:`hooke.driver.Driver` (which we have imported as `Driver`).
class TutorialDriver (Driver):
    """Handle simple text data as an example Driver.
    """
    def __init__(self):
        """YOU MUST OVERRIDE Driver.__init__.

        Here you set a value for `name` to identify your driver.  It
        should match the module name.
        """
        super(TutorialDriver, self).__init__(name='tutorial')

    def default_settings(self):
        """Return a list of any configurable settings for your driver.

        If your driver does not have any configurable settings, there
        is no need to override this method.
        """
        return [
            Setting(section=self.setting_section, help=self.__doc__),
            Setting(section=self.setting_section, option='x units', value='nm',
                    help='Set the units used for the x data.'),
            ]

    def is_me(self, path):
        """YOU MUST OVERRIDE Driver.is_me.

        RETURNS: Boolean (`True` or `False`)

        This method is a heuristic that looks at the file content and
        decides if the file can be opened by the driver itself.  It
        returns `True` if the file opened can be interpreted by the
        current driver, `False` otherwise.  Defining this method allows
        Hooke to understand what kind of files we're looking at
        automatically.
        """
        if os.path.isdir(path):
            return False

        f = open(path, 'r')
        header = f.readline() # we only need the first line
        f.close()

        """Our "magic fingerprint" is the TUTORIAL_FILE header. Of
        course, depending on the data file, you can have interesting
        headers, or patterns, etc. that you can use to guess the data
        format. What matters is successful recognition and the boolean
        (True/False) return.
        """
        if header.startswith('TUTORIAL_FILE'):
            return True
        return False

    def read(self, path, info=None):
        f = open(path,'r') # open the file for reading
        """In this case, we have a data format that is just a list of
        ASCII values, so we can just divide that in rows, and generate
        a list with each item being a row.  Of course if your data
        files are binary, or follow a different approach, do whatever
        you need. :)
        """
        self.data = list(self.filedata)
        f.close() # remember to close the file

        data = curve.Data()
        info = {'filetype':'tutorial', 'experiment':experiment.Experiment()}
        return (data, info)
