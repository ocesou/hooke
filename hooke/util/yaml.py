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

"""Add representers to YAML to support Hooke.

Without introspection, YAML cannot decide how to save some
objects.  By refusing to save these objects, we obviously loose
that information, so make sure the things you drop are either
stored somewhere else or not important.

>>> import yaml
>>> a = numpy.array([1,2,3])
>>> print yaml.dump(a)
null
...
<BLANKLINE>

The default behavior is to crash.

>>> yaml.Dumper.yaml_representers.pop(numpy.ndarray)  # doctest: +ELLIPSIS
<function none_representer at 0x...>
>>> print yaml.dump(a)  # doctest: +REPORT_UDIFF
!!python/object/apply:numpy.core.multiarray._reconstruct
args:
- !!python/name:numpy.ndarray ''
- !!python/tuple [0]
- b
state: !!python/tuple
- 1
- !!python/tuple [3]
- !!python/object/apply:numpy.dtype
  args: [i4, 0, 1]
  state: !!python/tuple [3, <, null, null, null, -1, -1, 0]
- false
- "\\x01\\0\\0\\0\\x02\\0\\0\\0\\x03\\0\\0\\0"
<BLANKLINE>

Hmm, at one point that crashed like this::

    Traceback (most recent call last):
      ...
        if data in [None, ()]:
    TypeError: data type not understood

Must be because of the other representers I've loaded since.

Restore the representer for future tests.

>>> yaml.add_representer(numpy.ndarray, none_representer)

We also avoid !!python/unicode tags by sacrificing the string/unicode
distinction.

>>> yaml.dump('ascii', allow_unicode=True)
'ascii\\n...\\n'
>>> yaml.dump(u'ascii', allow_unicode=True)
'ascii\\n...\\n'
>>> a = yaml.dump(u'Fran\\xe7ois', allow_unicode=True)
>>> a
'Fran\\xc3\\xa7ois\\n...\\n'
>>> unicode(a, 'utf-8')
u'Fran\\xe7ois\\n...\\n'
"""

from __future__ import absolute_import
import copy_reg
import sys
import types

import numpy
import yaml
import yaml.constructor
from yaml.constructor import ConstructorError
import yaml.representer

from ..curve import Data, Curve
from ..playlist import FilePlaylist


DATA_INFO_TAG = u'!hooke.curve.DataInfo'


if False: # YAML dump debugging code
    """To help isolate data types etc. that give YAML problems.

    This is usually caused by external C modules (e.g. numpy) that
    define new types (e.g. numpy.ndarray) which YAML cannot inspect.
    """
    def ignore_aliases(data):
        print data, repr(data), type(data), repr(type(data))
        sys.stdout.flush()
        if data in [None, ()]:
            return True
        if isinstance(data, (str, unicode, bool, int, float)):
            return True
    yaml.representer.SafeRepresenter.ignore_aliases = staticmethod(
        ignore_aliases)
else:
    # Avoid error with
    #   numpy.dtype(numpy.int32) in [None, ()]
    # See
    #   http://projects.scipy.org/numpy/ticket/1001
    def ignore_aliases(data):
        try:
            if data in [None, ()]:
                return True
            if isinstance(data, (str, unicode, bool, int, float)):
                return True
        except TypeError, e:
            pass
    yaml.representer.SafeRepresenter.ignore_aliases = staticmethod(
        ignore_aliases)

def unicode_representer(dumper, data):
    return dumper.represent_scalar(u'tag:yaml.org,2002:str', data)
yaml.add_representer(unicode, unicode_representer)

def none_representer(dumper, data):
    return dumper.represent_none(None)
yaml.add_representer(numpy.ndarray, none_representer)

def bool_representer(dumper, data):
    return dumper.represent_bool(data)
yaml.add_representer(numpy.bool_, bool_representer)

def int_representer(dumper, data):
    return dumper.represent_int(data)
yaml.add_representer(numpy.int32, int_representer)
yaml.add_representer(numpy.dtype(numpy.int32), int_representer)

def long_representer(dumper, data):
    return dumper.represent_long(data)
yaml.add_representer(numpy.int64, int_representer)

def float_representer(dumper, data):
    return dumper.represent_float(data)
yaml.add_representer(numpy.float32, float_representer)
yaml.add_representer(numpy.float64, float_representer)

def data_representer(dumper, data):
    info = dict(data.info)
    for key in info.keys():
        if key.startswith('raw '):
            del(info[key])
    return dumper.represent_mapping(DATA_INFO_TAG, info)
yaml.add_representer(Data, data_representer)

def data_constructor(loader, node):
    info = loader.construct_mapping(node)
    return Data(shape=(0,0), dtype=numpy.float32, info=info)
yaml.add_constructor(DATA_INFO_TAG, data_constructor)

def object_representer(dumper, data):
    cls = type(data)
    if cls in copy_reg.dispatch_table:
        reduce = copy_reg.dispatch_table[cls](data)
    elif hasattr(data, '__reduce_ex__'):
        reduce = data.__reduce_ex__(2)
    elif hasattr(data, '__reduce__'):
        reduce = data.__reduce__()
    else:
        raise RepresenterError("cannot represent object: %r" % data)
    reduce = (list(reduce)+[None]*5)[:5]
    function, args, state, listitems, dictitems = reduce
    args = list(args)
    if state is None:
        state = {}
    if isinstance(state, dict) and '_default_attrs' in state:
        for key in state['_default_attrs']:
            if key in state and state[key] == state['_default_attrs'][key]:
                del(state[key])
        del(state['_default_attrs'])
    if listitems is not None:
        listitems = list(listitems)
    if dictitems is not None:
        dictitems = dict(dictitems)
    if function.__name__ == '__newobj__':
        function = args[0]
        args = args[1:]
        tag = u'tag:yaml.org,2002:python/object/new:'
        newobj = True
    else:
        tag = u'tag:yaml.org,2002:python/object/apply:'
        newobj = False
    function_name = u'%s.%s' % (function.__module__, function.__name__)
    if not args and not listitems and not dictitems \
            and isinstance(state, dict) and newobj:
        return dumper.represent_mapping(
                u'tag:yaml.org,2002:python/object:'+function_name, state)
    if not listitems and not dictitems  \
            and isinstance(state, dict) and not state:
        return dumper.represent_sequence(tag+function_name, args)
    value = {}
    if args:
        value['args'] = args
    if state or not isinstance(state, dict):
        value['state'] = state
    if listitems:
        value['listitems'] = listitems
    if dictitems:
        value['dictitems'] = dictitems
    return dumper.represent_mapping(tag+function_name, value)
yaml.add_representer(FilePlaylist, object_representer)
yaml.add_representer(Curve, object_representer)


# Monkey patch PyYAML bug 159.
#   Yaml failed to restore loops in objects when __setstate__ is defined
#   http://pyyaml.org/ticket/159
# With viktor.x.voroshylo@jpmchase.com's patch
def construct_object(self, node, deep=False):
    if deep:
        old_deep = self.deep_construct
        self.deep_construct = True
    if node in self.constructed_objects:
        return self.constructed_objects[node]
    if node in self.recursive_objects:
        obj = self.recursive_objects[node]
        if obj is None :
            raise ConstructorError(None, None,
                 "found unconstructable recursive node", node.start_mark)
        return obj
    self.recursive_objects[node] = None
    constructor = None
    tag_suffix = None
    if node.tag in self.yaml_constructors:
        constructor = self.yaml_constructors[node.tag]
    else:
        for tag_prefix in self.yaml_multi_constructors:
            if node.tag.startswith(tag_prefix):
                tag_suffix = node.tag[len(tag_prefix):]
                constructor = self.yaml_multi_constructors[tag_prefix]
                break
        else:
            if None in self.yaml_multi_constructors:
                tag_suffix = node.tag
                constructor = self.yaml_multi_constructors[None]
            elif None in self.yaml_constructors:
                constructor = self.yaml_constructors[None]
            elif isinstance(node, ScalarNode):
                constructor = self.__class__.construct_scalar
            elif isinstance(node, SequenceNode):
                constructor = self.__class__.construct_sequence
            elif isinstance(node, MappingNode):
                constructor = self.__class__.construct_mapping
    if tag_suffix is None:
        data = constructor(self, node)
    else:
        data = constructor(self, tag_suffix, node)
    if isinstance(data, types.GeneratorType):
        generator = data
        data = generator.next()
        if self.deep_construct:
            self.recursive_objects[node] = data
            for dummy in generator:
                pass
        else:
            self.state_generators.append(generator)
    self.constructed_objects[node] = data
    del self.recursive_objects[node]
    if deep:
        self.deep_construct = old_deep
    return data
yaml.constructor.BaseConstructor.construct_object = construct_object
