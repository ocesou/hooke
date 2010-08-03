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

"""Hooke: tools for analyzing force spectroscopy data.

Mercurial repository:
http://www.physics.drexel.edu/~wking/code/hg/hooke/
"""

from distutils.core import setup
from os import walk
import os.path

from hooke import version


classifiers = """\
Development Status :: 3 - Alpha
Intended Audience :: Science/Research
Operating System :: OS Independent
License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)
Programming Language :: Python
Topic :: Scientific/Engineering
"""

doclines = __doc__.split("\n")

def find_packages(root='hooke'):
    packages = []
    prefix = '.'+os.path.sep
    for dirpath,dirnames,filenames in walk(root):
        if '__init__.py' in filenames:
            if dirpath.startswith(prefix):
                dirpath = dirpath[len(prefix):]
            packages.append(dirpath.replace(os.path.sep, '.'))
    return packages

packages = find_packages()

setup(name="Hooke",
      version=version(),
      maintainer="Massimo Sandal",
      maintainer_email="hookesoftware@googlegroups.com",
      url="http://code.google.com/p/hooke/",
      download_url="http://www.physics.drexel.edu/~wking/code/hg/hgwebdir.gci/hooke/archive/%s.tar.gz" % version(3),
      license = "GNU Lesser General Public License (LGPL)",
      platforms = ["all"],
      description = doclines[0],
      long_description = "\n".join(doclines[2:]),
      classifiers = filter(None, classifiers.split("\n")),
      scripts = ['bin/hooke'],
      packages = packages,
      provides = packages,
      )
