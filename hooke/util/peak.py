# Copyright (C) 2007-2010 Fabrizio Benedetti
#                         Massimo Sandal <devicerandom@gmail.com>
#                         W. Trevor King <wking@drexel.edu>
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

"""Utility functions for spotting peaks in signal data.
"""

from math import floor

import numpy

from ..command import Argument


class Peak (object):
    """A peak (signal spike) instance.

    Peaks are a continuous series of signal data points that exceed
    some threshold.

    Parameters
    ----------
    name : string
        Short comment explaining peak selection algorithm.
    index : int
        Offset of the first peak point in the original signal data.
    values : array
        Signal data values for each peak point.
    """
    def __init__(self, name='peak', index=0, values=[]):
        self.name = name
        self.index = index
        self.values = values

    def __str__(self):
        return '<%s %s %d:%d>' % (self.__class__.__name__, self.name,
                                  self.index, self.post_index())

    def __repr__(self):
        return '<%s %s %d %s>' % (self.__class__.__name__, self.name,
                                  self.index, self.values)

    def post_index(self):
        """The index *after* the end of the peak.

        Examples
        --------

        >>> p = Peak(index=5, values=numpy.arange(3))

        The peak consists of indicies 5, 6, and 7.o

        >>> p.post_index()
        8
        """
        return self.index + len(self.values)

def mask_to_peaks(data, mask, name='peak'):
    """Convert a mask array to a list of :class:`Peak`\s.

    Parameters
    ----------
    data : array
        Input data.
    mask : array of booleans
        `False` when data is noise, `True` for peaks.

    Returns
    -------
    peaks : list of :mod:`Peak`\s.
        A :mod:`Peak` instances for each continuous peak block.

    See Also
    --------
    peaks_to_mask

    Examples
    --------

    >>> data = numpy.arange(-10, -1)
    >>> mask = numpy.zeros(data.shape, dtype=numpy.bool)
    >>> mask[:2] = True
    >>> mask[5:8] = True
    >>> mask_to_peaks(data, mask, 'special points')
    [<Peak special points 0 [-10  -9]>, <Peak special points 5 [-5 -4 -3]>]
    """
    peaks = []
    i = 0
    while i < len(mask):
        if mask[i] == True: # masked peak point
            start_i = i
            while i < len(mask) and mask[i] == True:
                i += 1
            post_i = i
            peaks.append(Peak(
                    name=name, index=start_i, values=data[start_i:post_i]))
        else:
            i += 1
    return peaks

def peaks_to_mask(data, peaks):
    """Convert a list of :class:`Peak`\s to a mask array.

    Parameters
    ----------
    data : array
        Input data.
    peaks : list of :mod:`Peak`\s.
        A :mod:`Peak` instances for each continuous peak block.

    Returns
    -------
    mask : array of booleans
        `False` when data is noise, `True` for peaks.

    See Also
    --------
    mask_to_peaks

    Examples
    --------

    >>> data = numpy.arange(-10, -1)
    >>> mask = numpy.ones(data.shape, dtype=numpy.bool)
    >>> mask[:2] = False
    >>> mask[5:8] = False
    >>> peaks = mask_to_peaks(data, mask, 'special points')
    >>> mask2 = peaks_to_mask(data, peaks)
    >>> min(mask == mask2)
    True
    """
    mask = numpy.zeros(data.shape, dtype=numpy.bool)
    for peak in peaks:
        mask[peak.index:peak.post_index()] = True
    return mask

def noise(data, cut_side='both', stable=0.005, max_cut=0.2):
    """Find the portion of `data` that is "noise".

    Parameters
    ----------
    data : array
        Input signal.
    cut_side : {'both', 'positive', 'negative'}
        Side of the curve to cut from.
    stable : float
        Convergence threshold (stop if, when cutting more points, the
        relative change in the standard deviation is less than
        `stable`).
    max_cut : float
        Maximum fraction (0 to 1) of points to cut to evaluate noise,
        even if it doesn't converge (to avoid "eating" all the noise).

    Returns
    -------
    mask : array
        :math:`mask[i] == True` if `i` indexes a noise portion of
        `data`.  It is `False` otherwise.
    mean : float
        The most recently calculated mean.
    std : float
        The most recently calculated standard deviation.
    converged : {True, False}
        Whether the algorithm converged.

    Notes
    -----

    Algorithm:

    1) Calculate the mean and standard deviation of `data`
    2) Remove the most extreme point (from `cut_side`).
    3) Calclate mean and standard deviation of the remaining data.
    4) If the relative change in standard deviation is less than
      `stable` or the new standard deviation is zero, return with
      `converged` set to `True`.
    5) If `max cut` of the original number of points have been cut,
       return with `converged` set to `False`.
    6) Return to step (2)

    The implementation relies on :meth:`numpy.ndarray.argmax`.

    Examples
    --------

    For our test data, use a step decrease.

    >>> data = numpy.zeros((50,), dtype=numpy.float)
    >>> data[:5] = 1.0
    >>> mask,mean,std,converged = noise(data, cut_side='positive')

    The standard deviation will decrease as long as you're removing
    non-zero points (however, the relative change in the standard
    deviation increases), so we expect the first 10 values to be
    masked.

    >>> expected_mask = numpy.ones(data.shape, dtype=numpy.bool)
    >>> expected_mask[:5] = False
    >>> min(mask == expected_mask)
    True

    When the remaining points are all zero, the mean and standard
    deviation are both zero.  So the algorithm exits with successful
    convergence.

    >>> mean
    0.0
    >>> std
    0.0
    >>> converged
    True

    If we had mad more of the initial points 1, the algorithm would
    be limited by `max_cut` and not converge:

    >>> max_cut = 0.2
    >>> data[:2*max_cut*len(data)] = 1.0
    >>> mask,mean,std,converged = noise(
    ...     data, cut_side='positive', max_cut=max_cut)
    >>> expected_mask = numpy.ones(data.shape, dtype=numpy.bool)
    >>> expected_mask[:max_cut*len(data)] = False
    >>> min(mask == expected_mask)
    True
    >>> converged
    False
    """
    mask = numpy.ones(data.shape, dtype=numpy.bool)
    masked_mean = data.mean()
    masked_std = data.std()

    if cut_side == 'both':
        def new_mask(data, mask, masked_mean):
            mask[(numpy.absolute(data-masked_mean)*mask).argmax()] = 0
            return mask
    elif cut_side == 'positive':
        def new_mask(data, mask, masked_mean):
            mask[(data*mask).argmax()] = 0
            return mask
    elif cut_side == 'negative':
        def new_mask(data, mask, masked_mean):
            mask[(data*mask).argmin()] = 0
            return mask
    else:
        raise ValueError(cut_side)

    num_cuts = 0
    max_cuts = min(int(floor(max_cut * len(data))), len(data))
    while num_cuts < max_cuts:
        mask = new_mask(data, mask, masked_mean)
        num_cuts += 1
        new_masked_mean = (data*mask).mean()
        new_masked_std = (data*mask).std()
        rel_std = (masked_std-new_masked_std) / new_masked_std # >= 0
        if rel_std < stable or new_masked_std == 0:
            return (mask, new_masked_mean, new_masked_std, True)
        masked_mean = new_masked_mean
        masked_std = new_masked_std
    return (mask, masked_mean, masked_std, False)

noise_arguments = [
    Argument('cut side', type='string', default='both',
             help="""
Select the side of the curve to cut from.  `positive`, `negative`, or
`both`.
""".strip()),
    Argument('stable', type='float', default=0.005, help="""
Convergence threshold (stop if, when cutting more points, the relative
change in the standard deviation is less than `stable`).
""".strip()),
    Argument('max cut', type='float', default=0.2, help="""
The maximum fraction (0 to 1) of points to cut to evaluate noise, even
if it doesn't converge (to avoid "eating" all the noise).
""".strip()),
    ]
"""List :func:`noise`'s :class:`~hooke.command.Argument`\s for easy use
by plugins in :mod:`~hooke.plugin`.
"""

def above_noise(data, side='both', min_deviations=5.0, mean=None, std=None):
    """Find locations where `data` is far from the `mean`.

    Parameters
    ----------
    data : array
        Input data.
    side : {'both', 'positive', 'negative'}
        Side of the curve that can be "above" the noise.
    min_deviations : float
        Number of standard deviations beyond the mean to define
        "above" the noise.  Increase to tighten the filter.
    mean : float
        The mean of the input data's background noise.
    std : float
        The standard deviation of the input data's background noise.

    Returns
    -------
    mask : array of booleans
        `True` when data is beyond the threshold, otherwise `False`.

    Notes
    -----
    If `mean` and `std` are None, they are calculted using
    the respective `data` methods.

    Examples
    --------

    >>> data = numpy.arange(-3, 4)
    >>> above_noise(data, side='both', min_deviations=1.1, mean=0, std=1.0)
    array([ True,  True, False, False, False,  True,  True], dtype=bool)
    >>> above_noise(data, side='positive', min_deviations=1.1, mean=0, std=1.0)
    array([False, False, False, False, False,  True,  True], dtype=bool)
    >>> above_noise(data, side='negative', min_deviations=1.1, mean=0, std=1.0)
    array([ True,  True, False, False, False, False, False], dtype=bool)
    """
    if mean == None:
        mean = data.mean()
    if std == None:
        std = data.std()
    if side == 'negative':
        data = -data
        mean = -mean
    elif side == 'both':
        data = numpy.absolute(data-mean)
        mean = 0
    return data > (min_deviations * std)

above_noise_arguments = [
    Argument('side', type='string', default='both',
             help="""
Select the side of the curve that counts as "above".  `positive`,
`negative`, or `both`.
""".strip()),
    Argument('min deviations', type='float', default=5.0, help="""
Number of standard deviations above the noise to define a peak.
Increase to tighten the filter.
""".strip()),
    ]
"""List :func:`above_noise`' :class:`~hooke.command.Argument`\s for
easy use by plugins in :mod:`~hooke.plugin`.
"""

def merge_double_peaks(data, peaks, see_double=10):
    """Merge peaks that are "too close" together.

    Parameters
    ----------
    data : array
        Input data.
    peaks : list of :mod:`Peak`\s.
        A :mod:`Peak` instances for each continuous peak block.
    see_double : int
        If two peaks are separated by less than `see double` points,
        count them (and the intervening data) as a single peak.

    Returns
    -------
    peaks : list of :mod:`Peak`\s.
        The modified list of :mod:`Peak`\s.

    Examples
    --------

    >>> data = numpy.arange(150)
    >>> peaks = [Peak(name='a', index=10, values=data[10:12]),
    ...          Peak(name='b', index=15, values=data[15:18]),
    ...          Peak(name='c', index=23, values=data[23:27]),
    ...          Peak(name='d', index=100, values=data[100:101])]
    >>> peaks = merge_double_peaks(data, peaks, see_double=10)
    >>> print '\\n'.join([str(p) for p in peaks])
    <Peak a 10:27>
    <Peak d 100:101>
    >>> min(peaks[0].values == data[10:27])
    True
    """
    i = 0
    while i < len(peaks)-1:
        peak = peaks[i]
        next_peak = peaks[i+1]
        if next_peak.index - peak.post_index() > see_double: # far enough apart
            i += 1 # move on to the next peak
        else: # too close.  merge the peaks
            peaks[i] = Peak(name=peak.name, index=peak.index,
                            values=data[peak.index:next_peak.post_index()])
            peaks.pop(i+1)
    return peaks

merge_double_peaks_arguments = [
    Argument('see double', type='int', default=10, help="""
If two peaks are separated by less than `see double` points, count
them as a single peak.
""".strip()),
    ]
"""List :func:`merge_double_peaks`' :class:`~hooke.command.Argument`\s
for easy use by plugins in :mod:`~hooke.plugin`.
"""

def drop_narrow_peaks(peaks, min_points=1):
    """Drop peaks that are "too narrow".

    Parameters
    ----------
    peaks : list of :mod:`Peak`\s.
        A :mod:`Peak` instances for each continuous peak block.
    min_points : int
        Minimum number of points for :class:`Peak` acceptance.

    Returns
    -------
    peaks : list of :mod:`Peak`\s.
        The modified list of :mod:`Peak`\s.

    Examples
    --------

    >>> data = numpy.arange(150)
    >>> peaks = [Peak(name='a', index=10, values=data[10:12]),
    ...          Peak(name='b', index=15, values=data[15:18]),
    ...          Peak(name='c', index=23, values=data[23:27]),
    ...          Peak(name='d', index=100, values=data[100:101])]
    >>> peaks = drop_narrow_peaks(peaks, min_points=3)
    >>> print '\\n'.join([str(p) for p in peaks])
    <Peak b 15:18>
    <Peak c 23:27>
    """
    return [peak for peak in peaks if len(peak.values) >= min_points]

drop_narrow_peaks_arguments = [
    Argument('min points', type='int', default=1, help="""
Minimum number of "feature" points for peak acceptance.
""".strip()),
    ]
"""List :func:`drop_narrow_peaks`' :class:`~hooke.command.Argument`\s
for easy use by plugins in :mod:`~hooke.plugin`.
"""

def _kwargs(kwargs, arguments, translations={}, argument_input_keys=False):
    """Split off kwargs for the arguments listed in arguments.

    Also add the kwargs marked in `translations`.

    Examples
    --------

    >>> import pprint
    >>> kwargs = {'param_a':1, 'param_b':2, 'param_c':3}
    >>> args = [Argument(name='param a')]
    >>> translations = {'the_big_c_param':'param_c'}
    >>> pprint.pprint(_kwargs(kwargs, args, translations,
    ...                       argument_input_keys=False))
    {'param_a': 1, 'the_big_c_param': 3}
    >>> pprint.pprint(_kwargs(kwargs, args, translations,
    ...                       argument_input_keys=True))
    {'the_big_c_param': 3}
    >>> kwargs = {'param a':1, 'param b':2, 'param c':3}
    >>> translations = {'the_big_c_param':'param c'}
    >>> pprint.pprint(_kwargs(kwargs, args, translations,
    ...                       argument_input_keys=True))
    {'param_a': 1, 'the_big_c_param': 3}
    """
    arg_keys = [arg.name for arg in arguments]
    keys = [arg.name.replace(' ', '_') for arg in arguments]
    ret = {}
    for arg_key,key in zip(arg_keys, keys):
        in_key = key
        if argument_input_keys == True:
            in_key = arg_key
        if in_key in kwargs:
            ret[key] = kwargs[in_key]
    for target_key,source_key in translations.items():
        if source_key in kwargs:
            ret[target_key] = kwargs[source_key]
    return ret

def find_peaks(data, **kwargs):
    """Catch all peak finder.

    Runs in succession:

    1) :func:`noise`, to determine the standard deviation of the noise
      in `data`.
    2) :func:`above_noise` to select the regions of `data` that are
      "above" the noise.
    3) :func:`merge_double_peaks`
    4) :func:`drop_narrow_peaks`

    The input parameters may be any accepted by the above functions.
    """
    mask,mean,std,converged = noise(data, **_kwargs(kwargs, noise_arguments))
    mask = above_noise(data, mean=mean, std=std,
                       **_kwargs(kwargs, above_noise_arguments))
    peaks = mask_to_peaks(data, mask)
    peaks = merge_double_peaks(
        data, peaks, **_kwargs(kwargs, merge_double_peaks_arguments))
    return drop_narrow_peaks(
        peaks, **_kwargs(kwargs, drop_narrow_peaks_arguments))

find_peaks_arguments = (noise_arguments
                        + above_noise_arguments
                        + merge_double_peaks_arguments
                        + drop_narrow_peaks_arguments)
"""List :func:`find_peaks`' :class:`~hooke.command.Argument`\s for
easy use by plugins in :mod:`~hooke.plugin`.
"""
