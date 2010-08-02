#!/usr/bin/python
#
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

"""Auto-generate reStructuredText of the hooke module tree for Sphinx.

This script is adapted from one written for `Bugs Everywhere`_.

.. _Bugs Everywhere: http://bugseverywhere.org/
"""

import sys
import os, os.path


sys.path.insert(0, os.path.abspath('..'))


def title(modname):
    t = ':mod:`%s`' % modname
    delim = '*'*len(t)
    return '\n'.join([delim, t, delim, '', ''])

def automodule(modname):
    return '\n'.join([
            '.. automodule:: %s' % modname,
            '   :members:',
            '   :undoc-members:',
            '', ''])

def toctree(children):
    if len(children) == 0:
        return ''
    return '\n'.join([
            '.. toctree::',
            '   :maxdepth: 2',
            '',
            ] + [
            '   %s.txt' % c for c in sorted(children)
            ] + ['', ''])

def make_module_txt(modname, children):
    filename = os.path.join('hooke', '%s.txt' % modname)
    if not os.path.exists('hooke'):
        os.mkdir('hooke')
    if os.path.exists(filename):
        return None # don't overwrite potentially hand-written files.
    f = file(filename, 'w')
    f.write(title(modname))
    f.write(automodule(modname))
    f.write(toctree(children))
    f.close()



class Tree(list):
    """A traversable tree structure.

    Examples
    --------

    Construct::

               +-b---d-g
             a-+   +-e
               +-c-+-f-h-i

    with

    >>> i = Tree();       i.n = "i"
    >>> h = Tree([i]);    h.n = "h"
    >>> f = Tree([h]);    f.n = "f"
    >>> e = Tree();       e.n = "e"
    >>> c = Tree([f,e]);  c.n = "c"
    >>> g = Tree();       g.n = "g"
    >>> d = Tree([g]);    d.n = "d"
    >>> b = Tree([d]);    b.n = "b"
    >>> a = Tree();       a.n = "a"
    >>> a.append(c)
    >>> a.append(b)

    Get the longest branch length with

    >>> a.branch_len()
    5

    Sort the tree recursively.  Here we sort longest branch length
    first.

    >>> a.sort(key=lambda node : -node.branch_len())
    >>> "".join([node.n for node in a.traverse()])
    'acfhiebdg'

    And here we sort shortest branch length first.

    >>> a.sort(key=lambda node : node.branch_len())
    >>> "".join([node.n for node in a.traverse()])
    'abdgcefhi'

    We can also do breadth-first traverses.

    >>> "".join([node.n for node in a.traverse(depth_first=False)])
    'abcdefghi'

    Serialize the tree with depth marking branches.

    >>> for depth,node in a.thread():
    ...     print "%*s" % (2*depth+1, node.n)
    a
      b
        d
          g
      c
        e
        f
          h
            i

    Flattening the thread disables depth increases except at
    branch splits.

    >>> for depth,node in a.thread(flatten=True):
    ...     print "%*s" % (2*depth+1, node.n)
    a
      b
      d
      g
    c
      e
    f
    h
    i

    We can also check if a node is contained in a tree.

    >>> a.has_descendant(g)
    True
    >>> c.has_descendant(g)
    False
    >>> a.has_descendant(a)
    False
    >>> a.has_descendant(a, match_self=True)
    True
    """
    def __cmp__(self, other):
        return cmp(id(self), id(other))

    def __eq__(self, other):
        return self.__cmp__(other) == 0

    def __ne__(self, other):
        return self.__cmp__(other) != 0

    def branch_len(self):
        """Return the largest number of nodes from root to leaf (inclusive).

        For the tree::

               +-b---d-g
             a-+   +-e
               +-c-+-f-h-i

        this method returns 5.

        Notes
        -----
        Exhaustive search every time == *slow*.

        Use only on small trees, or reimplement by overriding
        child-addition methods to allow accurate caching.
        """
        if len(self) == 0:
            return 1
        else:
            return 1 + max([child.branch_len() for child in self])

    def sort(self, *args, **kwargs):
        """Sort the tree recursively.

        This method extends :meth:`list.sort` to Trees.

        Notes
        -----
        This method can be slow, e.g. on a :meth:`branch_len` sort,
        since a node at depth `N` from the root has it's
        :meth:`branch_len` method called `N` times.
        """
        list.sort(self, *args, **kwargs)
        for child in self:
            child.sort(*args, **kwargs)

    def traverse(self, depth_first=True):
        """Generate all the nodes in a tree, starting with the root node.

        Parameters
        ----------
        depth_first : bool
          Depth first by default, but you can set `depth_first` to
          `False` for breadth first ordering.  Siblings are returned
          in the order they are stored, so you might want to
          :meth:`sort` your tree first.
        """
        if depth_first == True:
            yield self
            for child in self:
                for descendant in child.traverse():
                    yield descendant
        else: # breadth first, Wikipedia algorithm
            # http://en.wikipedia.org/wiki/Breadth-first_search
            queue = [self]
            while len(queue) > 0:
                node = queue.pop(0)
                yield node
                queue.extend(node)

    def thread(self, flatten=False):
        """Generate a (depth, node) tuple for every node in the tree.

        When `flatten` is `False`, the depth of any node is one
        greater than the depth of its parent.  That way the
        inheritance is explicit, but you can end up with highly
        indented threads.

        When `flatten` is `True`, the depth of any node is only
        greater than the depth of its parent when there is a branch,
        and the node is not the last child.  This can lead to ancestry
        ambiguity, but keeps the total indentation down.  For example::

                      +-b                  +-b-c
                    a-+-c        and     a-+
                      +-d-e-f              +-d-e-f

        would both produce (after sorting by :meth:`branch_len`)::

            (0, a)
            (1, b)
            (1, c)
            (0, d)
            (0, e)
            (0, f)

        """
        stack = [] # ancestry of the current node
        if flatten == True:
            depthDict = {}

        for node in self.traverse(depth_first=True):
            while len(stack) > 0 \
                    and id(node) not in [id(c) for c in stack[-1]]:
                stack.pop(-1)
            if flatten == False:
                depth = len(stack)
            else:
                if len(stack) == 0:
                    depth = 0
                else:
                    parent = stack[-1]
                    depth = depthDict[id(parent)]
                    if len(parent) > 1 and node != parent[-1]:
                        depth += 1
                depthDict[id(node)] = depth
            yield (depth,node)
            stack.append(node)

    def has_descendant(self, descendant, depth_first=True, match_self=False):
        """Check if a node is contained in a tree.

        Parameters
        ----------
        descendant : Tree
          The potential descendant.
        depth_first : bool
          The search order.  Set this if you feel depth/breadth would
          be a faster search.
        match_self : bool
          Set to `True` for::

              x.has_descendant(x, match_self=True) -> True
        """
        if descendant == self:
            return match_self
        for d in self.traverse(depth_first):
            if descendant == d:
                return True
        return False


def python_tree(root_path='hooke', root_modname='hooke'):
    tree = Tree()
    tree.path = root_path
    tree.parent = None
    stack = [tree]
    while len(stack) > 0:
        f = stack.pop(0)
        if f.path.endswith('.py'):
            f.name = os.path.basename(f.path)[:-len('.py')]
        elif os.path.isdir(f.path) \
                and os.path.exists(os.path.join(f.path, '__init__.py')):
            f.name = os.path.basename(f.path)
            f.is_module = True
            for child in os.listdir(f.path):
                if child == '__init__.py':
                    continue
                c = Tree()
                c.path = os.path.join(f.path, child)
                c.parent = f
                stack.append(c)
        else:
            continue
        if f.parent == None:
            f.modname = root_modname
        else:
            f.modname = f.parent.modname + '.' + f.name
            f.parent.append(f)
    return tree

if __name__ == '__main__':
    pt = python_tree(root_path='../hooke', root_modname='hooke')
    for node in pt.traverse():
        print node.modname
        make_module_txt(node.modname, [c.modname for c in node])
