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

"""Define :class:`Experiment` and assorted subclasses.

This allows :class:`hooke.plugin.Plugin`\s to specify the types of
experiments they can handle.
"""

class Experiment (object):
    """Base class for experiment classification.
    """
    pass

class ForceClamp (Experiment):
    """Constant force force spectroscopy [#fernandez2004]_.

    .. [#fernandez2004] J.M. Fernandez, H. Li.
      "Force-Clamp Spectroscopy Monitors the Folding Trajectory of a
      Single Protein."
      Science, 2004.
      doi: `10.1126/science.1092497 <http://dx.doi.org/10.1126/science.1092497>`_
    """
    pass

class VelocityClamp (Experiment):
    """Constant piezo velocity force spectroscopy [#rief1997]_.
    
    .. [#rief1997] M. Rief, M. Gautel, F. Oesterhelt, J.M. Fernandez,
      H.E. Gaub.
      "Reversible Unfolding of Individual Titin Immunoglobulin Domains by AFM."
      Science, 1997.
      doi: `10.1126/science.276.5315.1109 <http://dx.doi.org/10.1126/science.276.5315.1109>`_
    """
    pass

class TwoColorCoincidenceDetection (Experiment):
    """Two-color fluorescence coincidence spectroscopy [#clarke2007]_.

    .. [#clarke2007] R.W. Clarke, A. Orte, D. Klenerman.
      "Optimized Threshold Selection for Single-Molecule Two-Color
      Fluorescence Coincidence Spectroscopy."
      Anal. Chem., 2007.
      doi: `10.1021/ac062188w <http://dx.doi.org/10.1021/ac062188w>`_
    """
    pass
