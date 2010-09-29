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

"""``pluggable`` provides utility functions for extensible plugin modules.
"""

import logging

from ..compat.odict import odict
from .graph import Node, Graph


class IsSubclass (object):
    """A safe subclass comparator.
    
    Examples
    --------

    >>> class A (object):
    ...     pass
    >>> class B (A):
    ...     pass
    >>> C = 5
    >>> is_subclass = IsSubclass(A)
    >>> is_subclass(A)
    True
    >>> is_subclass = IsSubclass(A, blacklist=[A])
    >>> is_subclass(A)
    False
    >>> is_subclass(B)
    True
    >>> is_subclass(C)
    False
    """
    def __init__(self, base_class, blacklist=None):
        self.base_class = base_class
        if blacklist == None:
            blacklist = []
        self.blacklist = blacklist
    def __call__(self, other):
        try:
            subclass = issubclass(other, self.base_class)
        except TypeError:
            return False
        if other in self.blacklist:
            return False
        return subclass


def submods(this_modname, submodnames):
    """Iterate through (submodname, submod) pairs.
    """
    for submodname in submodnames:
        count = len([s for s in submodnames if s == submodname])
        assert count > 0, 'No %s entries: %s' % (submodname, submodnames)
        assert count == 1, 'Multiple (%d) %s entries: %s' \
            % (count, submodname, submodnames)
        try:
            this_mod = __import__(this_modname, fromlist=[submodname])
        except ImportError, e:
            # Use the root logger because the 'hooke' logger is
            # configured by a Hooke instance after module imports.
            logging.warn('could not import %s from %s: %s'
                         % (submodname, this_modname, e))
            continue
        submod = getattr(this_mod, submodname)
        yield (submodname, submod)


def construct_odict(this_modname, submodnames, class_selector,
                    instantiate=True):
    """Search the submodules `submodnames` of a module `this_modname`
    for class objects for which `class_selector(class)` returns
    `True`.  If `instantiate == True` these classes are instantiated
    and stored in the returned :class:`hooke.compat.odict.odict` in
    the order in which they were discovered.  Otherwise, the class
    itself is stored.
    """
    objs = odict()
    for submodname,submod in submods(this_modname, submodnames):
        for objname in dir(submod):
            obj = getattr(submod, objname)
            if class_selector(obj):
                if instantiate == True:
                    try:
                        obj = obj()
                    except Exception, e:
                        logging.error('could not instantiate %s from %s: %s'
                                      % (obj, submodname, e))
                        raise
                name = getattr(obj, 'name', submodname)
                objs[name] = obj
    return objs


def construct_graph(this_modname, submodnames, class_selector,
                    assert_name_match=True):
    """Search the submodules `submodnames` of a module `this_modname`
    for class objects for which `class_selector(class)` returns
    `True`.  These classes are instantiated, and the `instance.name`
    is compared to the `submodname` (if `assert_name_match` is
    `True`).

    The instances are further arranged into a dependency
    :class:`hooke.util.graph.Graph` according to their
    `instance.dependencies()` values.  The topologically sorted graph
    is returned.
    """
    instances = {}
    for submodname,submod in submods(this_modname, submodnames):
        for objname in dir(submod):
            obj = getattr(submod, objname)
            if class_selector(obj):
                try:
                    instance = obj()
                except Exception, e:
                    logging.error('could not instantiate %s from %s: %s'
                                  % (obj, submodname, e))
                    raise
                if assert_name_match == True and instance.name != submodname:
                    raise Exception(
                        'Instance name %s does not match module name %s'
                        % (instance.name, submodname))
                instances[instance.name] = instance
    nodes = {}
    for i in instances.values():     # make nodes for each instance
        nodes[i.name] = Node(data=i)
    for n in nodes.values():         # fill in dependencies for each node
        n.extend([nodes[name] for name in n.data.dependencies()])
    graph = Graph(nodes.values())
    graph.topological_sort()
    return graph
