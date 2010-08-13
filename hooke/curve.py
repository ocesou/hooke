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

"""The `curve` module provides :class:`Curve` and :class:`Data` for
storing force curves.
"""

import logging
import os.path

import numpy

from .command_stack import CommandStack


class NotRecognized (ValueError):
    def __init__(self, curve):
        self.__setstate__(curve)

    def __getstate__(self):
        return self.curve

    def __setstate__(self, data):
        if isinstance(data, Curve):
            msg = 'Not a recognizable curve format: %s' % data.path
            super(NotRecognized, self).__init__(msg)
            self.curve = data

class Data (numpy.ndarray):
    """Stores a single, continuous data set.

    Adds :attr:`info` :class:`dict` to the standard :class:`numpy.ndarray`.

    See :mod:`numpy.doc.subclassing` for the peculiarities of
    subclassing :class:`numpy.ndarray`.

    Examples
    --------

    >>> d = Data(shape=(3,2), info={'columns':['distance (m)', 'force (N)']})
    >>> type(d)
    <class 'hooke.curve.Data'>
    >>> for i in range(3): # initialize d
    ...    for j in range(2):
    ...        d[i,j] = i*10 + j
    >>> d
    Data([[  0.,   1.],
           [ 10.,  11.],
           [ 20.,  21.]])
    >>> d.info
    {'columns': ['distance (m)', 'force (N)']}

    The information gets passed on to slices.

    >>> row_a = d[:,0]
    >>> row_a
    Data([  0.,  10.,  20.])
    >>> row_a.info
    {'columns': ['distance (m)', 'force (N)']}

    The data-type is also pickleable, to ensure we can move it between
    processes with :class:`multiprocessing.Queue`\s.

    >>> import pickle
    >>> s = pickle.dumps(d)
    >>> z = pickle.loads(s)
    >>> z
    Data([[  0.,   1.],
           [ 10.,  11.],
           [ 20.,  21.]])
    >>> z.info
    {'columns': ['distance (m)', 'force (N)']}
    """
    def __new__(subtype, shape, dtype=numpy.float, buffer=None, offset=0,
                strides=None, order=None, info=None):
        """Create the ndarray instance of our type, given the usual
        input arguments.  This will call the standard ndarray
        constructor, but return an object of our type.
        """
        obj = numpy.ndarray.__new__(
            subtype, shape, dtype, buffer, offset, strides, order)
        # add the new attribute to the created instance
        if info == None:
            info = {}
        obj.info = info
        # Finally, we must return the newly created object:
        return obj

    def __array_finalize__(self, obj):
        """Set any extra attributes from the original object when
        creating a new view object."""
        # reset the attribute from passed original object
        self.info = getattr(obj, 'info', {})
        # We do not need to return anything

    def __reduce__(self):
        """Collapse an instance for pickling.

        Returns
        -------
        reconstruct : callable
            Called to create the initial version of the object.
        args : tuple
            A tuple of arguments for `reconstruct`
        state : (optional)
            The state to be passed to __setstate__, if present.
        iter : iterator (optional)
            Yielded items will be appended to the reconstructed
            object.
        dict : iterator (optional)
            Yielded (key,value) tuples pushed back onto the
            reconstructed object.
        """
        base_reduce = list(numpy.ndarray.__reduce__(self))
        # tack our stuff onto ndarray's setstate portion.
        base_reduce[2] = (base_reduce[2], (self.info,))
        return tuple(base_reduce)

    def __setstate__(self, state):
        base_class_state,own_state = state
        numpy.ndarray.__setstate__(self, base_class_state)
        self.info, = own_state


class Curve (object):
    """A grouped set of :class:`Data` runs from the same file with metadata.

    For an approach/retract force spectroscopy experiment, the group
    would consist of the approach data and the retract data.  Metadata
    would be the temperature, cantilever spring constant, etc.

    Two important :attr:`info` settings are `filetype` and
    `experiment`.  These are two strings that can be used by Hooke
    commands/plugins to understand what they are looking at.

    * :attr:`info['filetype']` should contain the name of the exact
      filetype defined by the driver (so that filetype-speciofic
      commands can know if they're dealing with the correct filetype).
    * :attr:`info['experiment']` should contain an instance of a
      :class:`hooke.experiment.Experiment` subclass to identify the
      experiment type.  For example, various
      :class:`hooke.driver.Driver`\s can read in force-clamp data, but
      Hooke commands could like to know if they're looking at force
      clamp data, regardless of their origin.

    Another important attribute is :attr:`command_stack`, which holds
    a :class:`~hooke.command_stack.CommandStack` listing the commands
    that have been applied to the `Curve` since loading.
    """
    def __init__(self, path, info=None):
        #the data dictionary contains: {name of data: list of data sets [{[x], [y]}]
        self.path = path
        self.driver = None
        self.data = None
        if info == None:
            info = {}
        self.info = info
        self.name = os.path.basename(path)
        self.command_stack = CommandStack()
        self._hooke = None  # Hooke instance for Curve.load()

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        return u'<%s %s>' % (self.__class__.__name__, self.name)

    def __repr__(self):
        return self.__str__()

    def set_hooke(self, hooke=None):
        if hooke != None:
            self._hooke = hooke

    def identify(self, drivers):
        """Identify the appropriate :class:`hooke.driver.Driver` for
        the curve file (`.path`).
        """
        if 'filetype' in self.info:
            driver = [d for d in drivers if d.name == self.info['filetype']]
            if len(driver) == 1:
                driver = driver[0]
                if driver.is_me(self.path):
                    self.driver = driver
                    return
        for driver in drivers:
            if driver.is_me(self.path):
                self.driver = driver # remember the working driver
                return
        raise NotRecognized(self)

    def load(self, hooke=None):
        """Use the driver to read the curve into memory.

        Also runs any commands in :attr:`command_stack`.  All
        arguments are passed through to
        :meth:`hooke.command_stack.CommandStack.execute`.
        """
        self.set_hooke(hooke)
        log = logging.getLogger('hooke')
        log.debug('loading curve %s with driver %s' % (self.name, self.driver))
        data,info = self.driver.read(self.path, self.info)
        self.data = data
        for key,value in info.items():
            self.info[key] = value
        if self._hooke != None:
            self.command_stack.execute(self._hooke)
        elif len(self.command_stack) > 0:
            log.warn(
                'could not execute command stack for %s without Hooke instance'
                % self.name)

    def unload(self):
        """Release memory intensive :attr:`.data`.
        """
        log = logging.getLogger('hooke')
        log.debug('unloading curve %s' % self.name)
        self.data = None
