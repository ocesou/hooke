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

"""The `calculus` module provides functions for calculating
derivatives and integrals of discrete data.
"""

import copy

import numpy

from ..curve import Data


def derivative(x_data, f_data, weights={-1:-0.5, 1:0.5}):
    """Calculate the discrete derivative (finite difference) of
    f_data with respect to x_data.

    Examples
    --------

    >>> d = Data((5,2), dtype=numpy.float,
    ...          info={'columns':['x', 'x**2']})
    >>> for i in range(5):
    ...     d[i,0] = i
    ...     d[i,1] = i**2
    >>> d
    Data([[  0.,   0.],
           [  1.,   1.],
           [  2.,   4.],
           [  3.,   9.],
           [  4.,  16.]])
    >>> dd = derivative(x_data=d[:,0], f_data=d[:,1])
    >>> dd
    Data([ 1.,  2.,  4.,  6.,  7.])

    Notes
    -----

    *Weights*

    The returned :class:`Data` block shares its x vector with the
    input data.  The `i`\th df/dx value in the returned data is
    caclulated with::

        (df/dx)[i] = (SUM_j w[j] f[i+j]) / h

    where ``h = x[i+1]-x[i]`` is the x coordinate spacing (assumed
    constant) and ``j`` ranges over the keys of `weights`.

    There standard schemes translate as follows:

    ========  ======================  ===================
    scheme    formula                 weights       
    ========  ======================  ===================
    forward   ``(f[i+1]-f[i])/h``     ``{0:-1,1:1}``
    backward  ``(f[i]-f[i-1])/h``     ``{0:1,-1:-1}``
    central   ``(f[i+1]-f[i-1])/2h``  ``{-1:-0.5,1:0.5}``
    ========  ======================  ===================

    The default scheme is central differencing.

    *Boundary conditions*

    The boundary conditions could be configurable in principle.  The
    current scheme just extrapolates virtual points out to negative
    `i` following::

        f[i<0] = 2*f[0] - f[-i]

    With analogous treatment for `i > data.shape[0]`.  This ensures that
    `f[i]-f[0]` is odd about `i=0`, which keeps derivatives smooth.::

        f[i] - f[0] = f[0] - f[-i] == -(f[-i] - f[0])    
    """
    output = Data(f_data.shape, dtype=f_data.dtype)
    h = x_data[1] - x_data[0]
    chunks = []
    for i,w in weights.items():
        chunk = numpy.roll(w*f_data, -i)
        if i > 0: # chunk shifted down, replace the high `i`s
            zero = len(chunk) - 1 - i
            for j in range(1,i+1):
                chunk[zero+j] = 2*chunk[zero] - chunk[zero-j]
        elif i < 0: # chunk shifted up, replace the low `i`s
            zero = -i
            for j in range(1,zero+1):
                chunk[zero-j] = 2*chunk[zero] - chunk[zero+j]
        chunks.append(chunk)
    return sum(chunks)
