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

"""Define :class:`Graph`, a directed, acyclic graph structure.
:class:`Graph`\s are composed of :class:`Node`\s, also defined by this
module.
"""

import bisect

class CyclicGraphError (ValueError):
    pass

class Node (list):
    """A node/element in a graph.

    Contains a list of the node's parents, and stores the node's
    `data`.

    Examples
    --------

    >>> a = Node(data='a')
    >>> b = Node(parents=[a], data='b')
    >>> c = Node(parents=[a], data='c')
    >>> d = Node(parents=[b, c], data='d')
    >>> str(d)
    'd'

    We can list all of a node's ancestors.

    >>> print [node for node in d.ancestors()]
    [b, c, a]
    >>> print [node for node in d.ancestors(depth_first=True)]
    [b, a, c]

    Ancestors works with cycles.

    >>> a.append(d)
    >>> print [node for node in d.ancestors()]
    [b, c, a, d]

    We can find the cycle path.

    >>> print d.parent_path(d)
    [b, a, d]

    After a run through :meth:`Graph.set_children`, we can also
    list children

    >>> g = Graph([a, b, c, d])
    >>> g.set_children()
    >>> print a.children
    [b, c]

    And descendents.

    >>> print [node for node in a.descendents(depth_first=True)]
    [b, d, a, c]
    """
    def __init__(self, parents=[], data=None):
        list.__init__(self, parents)
        self.data = data
        self.children = []

    def __cmp__(self, other):
        return -cmp(self.data, other.data)
    def __eq__(self, other):
        return self.__cmp__(other) == 0
    def __ne__(self, other):
        return self.__cmp__(other) != 0
    def __lt__(self, other):
        return self.__cmp__(other) < 0
    def __gt__(self, other):
        return self.__cmp__(other) > 0
    def __le__(self, other):
        return self.__cmp__(other) <= 0
    def __ge__(self, other):
        return self.__cmp__(other) >= 0

    def __str__(self):
        return str(self.data)
    def __repr__(self):
        return self.__str__()

    def traverse(self, next, depth_first=False):
        """Iterate through all nodes returned by `next(node)`.

        Will only yield each traversed node once, even in the case of
        diamond inheritance, etc.

        Breadth first by default.  Set `depth_first==True` for a
        depth first search.
        """
        stack = list(next(self))
        popped = []
        while len(stack) > 0:
            node = stack.pop(0)
            if node in popped:
                continue
            popped.append(node)
            yield node
            if depth_first == True:
                for target in reversed(next(node)):
                    stack.insert(0, target)
            else:
                stack.extend(next(node))

    def ancestors(self, depth_first=False):
        """Generate all ancestors.

        This is a small wrapper around :meth:`traverse`.
        """
        next = lambda node : node  # list node's parents
        for node in self.traverse(next=next, depth_first=depth_first):
            yield node

    def descendents(self, depth_first=False):
        """Generate all decendents.

        This is a small wrapper around :meth:`traverse`.
        """
        next = lambda node : node.children
        for node in self.traverse(next=next, depth_first=depth_first):
            yield node

    def path(self, next, node):
        """Return the shortest list of nodes connecting `self` to
        `node` via `next(node)`.
        """
        if node in self:
            return [node]
        stack = list(next(self))
        paths = dict((id(n), [n]) for n in stack)
        while len(stack) > 0:
            n = stack.pop(0)
            n_path = paths[id(n)]
            for target in next(n):
                if id(target) in paths:
                    continue
                t_path = list(n_path)
                t_path.append(target)
                if id(target) == id(node):
                    return t_path
                stack.append(target)
                paths[id(target)] = t_path

    def parent_path(self, node):
        """Return the shortest list of nodes connecting `self` to
        its parent `node`.

        This is a small wrapper around :meth:`path`.
        """
        next = lambda node : node  # list node's parents
        return self.path(next, node)

    def child_path(self, node):
        """Return the shortest list of nodes connecting `self` to
        its child `node`.

        This is a small wrapper around :meth:`path`.
        """
        next = lambda node : node.children
        return self.path(next, node)


class GraphRow (object):
    """Represent the state of a single row in a graph.

    Generated by :class:`GraphRowGenerator`, printed with
    :class:`GraphRowPrinter`.

    :attr:`node` is the active node and :attr:`active` is its branch
    column index.  :attr:`width` is the number of current branch
    columns.

    :attr:`born`, :attr:`dead`, and :attr:`inherited` are lists of
    `(branch_column_index, target_node)` pairs.  `dead` lists nodes
    from previous rows whose branches complete on this row,
    `inherited` lists nodes from previous rows whose branches continue
    through this row, and `born` list nodes whose branches start on
    this row.
    """
    def __init__(self, node, active=-1, dead=None, inherited=None, born=None,
                 tip_to_root=False):
        self.node = node
        self.active = active
        if dead == None:
            dead = []
        self.dead = dead
        if inherited == None:
            inherited = []
        self.inherited = inherited
        if born == None:
            born = []
        self.born = born
        self.tip_to_root = tip_to_root

class GraphRowPrinter (object):
    """Customizable printing for :class:`GraphRow`.

    The string rendering can be customized by changing :attr:`chars`.
    Control over the branch columns:

    ================= ===========================================
    `node: ...`       the active (most recently inserted) node
    `split/join: ...` branching/merging runs from the active node
    `run: connected`  connect a branch to its eventual node
    `run: blank`      place-holder for extinct runs
    ================= ===========================================

    Branch columns are seperated by separator columns:

    ================= =======================================================
    `sep: split/join` separate split/join branch columns from the active node
    `sep: default`    separate all remaining branch columns
    ================= =======================================================
    """
    def __init__(self, chars=None):
        if chars == None:
            chars = {
                'node: both tip and root': 'b',
                'node: root': 'r',
                'node: tip': 't',
                'node: regular': '*',
                'split/join: born and died left of active': '>',
                'split/join: born and died right of active': '<',
                'split/join: born left of active': '/',
                'split/join: born right of active': '\\',
                'split/join: died left of active': '\\',
                'split/join: died right of active': '/',
                'run: blank': ' ',
                'run: connected': '|',
                'sep: split/join': '-',
                'sep: default': ' ',               
                }
        self.chars = chars
    def __call__(self, graph_row):
        """Render the :class:`GraphRow` instance `graph_row` as a
        string.
        """
        dead = [i for i,node in graph_row.dead]
        inherited = [i for i,node in graph_row.inherited]
        born = [i for i,node in graph_row.born]
        right_connect = max(graph_row.active,
                            max(born+[-1]), # +[-1] protects against empty born
                            max(dead+[-1]))
        left_connect = min(graph_row.active,
                           min(born+[right_connect]),
                           min(dead+[right_connect]))
        max_col = max(right_connect, max(inherited+[-1]))
        string = []
        for i in range(max_col + 1):
            # Get char, the node or branch column character.
            if i == graph_row.active:
                if len(born) == 0:
                    if len(dead) == 0:
                        char = self.chars['node: both tip and root']
                    elif graph_row.tip_to_root == True:
                        # The dead are children
                        char = self.chars['node: root']
                    else: # The dead are parents
                        char = self.chars['node: tip']
                elif len(dead) == 0:
                    if graph_row.tip_to_root == True:
                        # The born are parents
                        char = self.chars['node: tip']
                    else: # The born are children
                        char = self.chars['node: root']
                else:
                    char = self.chars['node: regular']
            elif i in born:
                if i in dead: # born and died
                    if i < graph_row.active:
                        char = self.chars[
                            'split/join: born and died left of active']
                    else:
                        char = self.chars[
                            'split/join: born and died right of active']
                else: # just born
                    if i < graph_row.active:
                        char = self.chars['split/join: born left of active']
                    else:
                        char = self.chars['split/join: born right of active']
            elif i in dead: # just died
                if i < graph_row.active:
                    char = self.chars['split/join: died left of active']
                else:
                    char = self.chars['split/join: died right of active']
            elif i in inherited:
                char = self.chars['run: connected']
            else:
                char = self.chars['run: blank']
            # Get sep, the separation character.
            if i < left_connect or i >= right_connect:
                sep = self.chars['sep: default']
            else:
                sep = self.chars['sep: split/join']
                if char == self.chars['run: blank']:
                    char = self.chars['sep: split/join']
            string.extend([char, sep])
        return ''.join(string)[:-1] # [-1] strips final sep

class GraphRowGenerator (list):
    """A :class:`GraphRow` generator.

    Contains a list of :class:`GraphRow`\s (added with
    :meth:`insert`(:class:`hooke.util.graph.Node`)).  You should
    generate a graph with repeated calls::

        tip_to_root = True
        g = GraphRowGenerator(tip_to_root=tip_to_root)
        p = GraphRowPrinter(tip_to_root=tip_to_root)
        for node in nodes:
            g.insert(node)
            print p(g[-1])

    For the split/join branch columns, "born" and "dead" are defined
    from the point of view of `GraphRow`.  For root-to-tip ordering
    (`tip_to_root==False`, the default), "born" runs are determined
    by the active node's children (which have yet to be printed) and
    "dead" runs by its parents (which have been printed).  If
    `tip_to_root==True`, swap "children" and "parents" in the above
    sentence.
    """
    def __init__(self, tip_to_root=False):
        list.__init__(self)
        self.tip_to_root = tip_to_root
    def insert(self, node):
        """Add a new node to the graph.

        If `tip_to_root==True`, nodes should be inserted in
        tip-to-root topological order (i.e. node must be inserted
        before any of its parents).

        If `tip_to_root==False`, nodes must be inserted before any
        of their children.
        """
        if len(self) == 0:
            previous = GraphRow(node=None, active=-1)
        else:
            previous = self[-1]
        current = GraphRow(node=node, active=-1, tip_to_root=self.tip_to_root)
        if self.tip_to_root == True: # children die, parents born
            dead_nodes = list(current.node.children)
            born_nodes = list(current.node)
        else: # root-to-tip: parents die, children born
            dead_nodes = list(current.node)
            born_nodes = list(current.node.children)
        # Mark the dead and inherited branch columns
        for i,node in previous.inherited + previous.born:
            if node in dead_nodes or node == current.node:
                current.dead.append((i, node))
            else:
                current.inherited.append((i, node))
        # Place born and active branch columns
        num_born = max(len(born_nodes), 1) # 1 to ensure slot for active node
        remaining = num_born # number of nodes left to place
        used_slots = [i for i,n in current.inherited]
        old_max = max(used_slots+[-1]) # +[-1] in case used_slots is empty
        slots = sorted([i for i in range(old_max+1) if i not in used_slots])
        remaining -= len(slots)
        slots.extend(range(old_max+1, old_max+1+remaining))
        current.active = slots[0]
        current.born = zip(slots, born_nodes)
        # TODO: sharing branches vs. current 1 per child
        self.append(current)


class Graph (list):
    """A directed, acyclic graph structure.

    Contains methods for sorting and printing graphs.

    Examples
    --------

    >>> class Nodes (object): pass
    >>> n = Nodes()
    >>> for char in ['a','b','c','d','e','f','g','h','i']:
    ...     setattr(n, char, Node(data=char))
    >>> n.b.append(n.a)
    >>> n.c.append(n.a)
    >>> n.d.append(n.a)
    >>> n.e.extend([n.b, n.c, n.d])
    >>> n.f.append(n.e)
    >>> n.g.append(n.e)
    >>> n.h.append(n.e)
    >>> n.i.extend([n.f, n.g, n.h])
    >>> g = Graph([n.a,n.b,n.c,n.d,n.e,n.f,n.g,n.h,n.i])
    >>> g.topological_sort(tip_to_root=True)
    >>> print [node for node in g]
    [i, h, g, f, e, d, c, b, a]
    >>> print g.ascii_graph()
    r-\-\ a
    | | * b
    | * | c
    * | | d
    *-<-< e
    | | * f
    | * | g
    * | | h
    t-/-/ i
    >>> print g.ascii_graph(tip_to_root=True)
    t-\-\ i
    | | * h
    | * | g
    * | | f
    *-<-< e
    | | * d
    | * | c
    * | | b
    r-/-/ a

    >>> for char in ['a','b','c','d','e','f','g','h']:
    ...     setattr(n, char, Node(data=char))
    >>> n.b.append(n.a)
    >>> n.c.append(n.b)
    >>> n.d.append(n.a)
    >>> n.e.append(n.d)
    >>> n.f.extend([n.b, n.d])
    >>> n.g.extend([n.e, n.f])
    >>> n.h.extend([n.c, n.g])
    >>> g = Graph([n.a,n.b,n.c,n.d,n.e,n.f,n.g,n.h])
    >>> print g.ascii_graph(tip_to_root=True)
    t-\ h
    | *-\ g
    | | *-\ f
    | * | | e
    | *-|-/ d
    * | | c
    *-|-/ b
    r-/ a

    >>> for char in ['a','b','c','d','e','f','g','h','i']:
    ...     setattr(n, char, Node(data=char))
    >>> for char in ['a', 'b','c','d','e','f','g','h']:
    ...     nx = getattr(n, char)
    ...     n.i.append(nx)
    >>> g = Graph([n.a,n.b,n.c,n.d,n.e,n.f,n.g,n.h,n.i])
    >>> print g.ascii_graph(tip_to_root=True)
    t-\-\-\-\-\-\-\ i
    | | | | | | | r h
    | | | | | | r g
    | | | | | r f
    | | | | r e
    | | | r d
    | | r c
    | r b
    r a

    >>> for char in ['a','b','c','d','e','f','g','h','i']:
    ...     setattr(n, char, Node(data=char))
    >>> for char in ['b','c','d','e','f','g','h','i']:
    ...     nx = getattr(n, char)
    ...     nx.append(n.a)
    >>> g = Graph([n.a,n.b,n.c,n.d,n.e,n.f,n.g,n.h,n.i])
    >>> print g.ascii_graph(tip_to_root=True)
    t i
    | t h
    | | t g
    | | | t f
    | | | | t e
    | | | | | t d
    | | | | | | t c
    | | | | | | | t b
    r-/-/-/-/-/-/-/ a

    >>> for char in ['a','b','c','d','e','f','g','h','i']:
    ...     setattr(n, char, Node(data=char))
    >>> n.d.append(n.a)
    >>> n.e.extend([n.a, n.c])
    >>> n.f.extend([n.c, n.d, n.e])
    >>> n.g.extend([n.b, n.e, n.f])
    >>> n.h.extend([n.a, n.c, n.d, n.g])
    >>> n.i.extend([n.a, n.b, n.c, n.g])
    >>> g = Graph([n.a,n.b,n.c,n.d,n.e,n.f,n.g,n.h,n.i])
    >>> print g.ascii_graph(tip_to_root=True)
    t-\-\-\ i
    | | | | t-\-\-\ h
    | | | *-|-|-|-<-\ g
    | | | | | | | | *-\-\ f
    | | | | | | | *-|-|-< e
    | | | | | | *-|-|-/ | d
    | | r-|-|-/-|-|-/---/ c
    | r---/ |   | | b
    r-------/---/-/ a

    Ok, enough pretty graphs ;).  Here's an example of cycle
    detection.

    >>> for char in ['a','b','c','d']:
    ...     setattr(n, char, Node(data=char))
    >>> n.b.append(n.a)
    >>> n.c.append(n.a)
    >>> n.d.extend([n.b, n.c])
    >>> n.a.append(n.d)
    >>> g = Graph([n.a,n.b,n.c,n.d])
    >>> g.check_for_cycles()
    Traceback (most recent call last):
      ...
    CyclicGraphError: cycle detected:
      a
      d
      b
      a
    """
    def set_children(self):
        """Fill out each node's :attr:`Node.children` list.
        """
        for node in self:
            for parent in node:
                if node not in parent.children:
                    parent.children.append(node)

    def topological_sort(self, tip_to_root=False):
        """Algorithm from git's commit.c `sort_in_topological_order`_.

        Default ordering is root-to-tip.  Set `tip_to_root=True` for
        tip-to-root.

        In situations where topological sorting is ambiguous, the
        nodes are sorted using the node comparison functions (__cmp__,
        __lt__, ...).  If `tip_to_root==True`, the inverse
        comparison functions are used.

        .. _sort_in_topological_order:
          http://git.kernel.org/?p=git/git.git;a=blob;f=commit.c;h=731191e63bd39a89a8ea4ed0390c49d5605cdbed;hb=HEAD#l425
        """
        # sort tip-to-root first, then reverse if neccessary
        for node in self:
            node._outcount = 0
        for node in self:
            for parent in node:
                parent._outcount += 1
        tips = sorted([node for node in self if node._outcount == 0])
        orig_len = len(self)
        del self[:]
        while len(tips) > 0:
            node = tips.pop(0)
            for parent in node:
                parent._outcount -= 1
                if parent._outcount == 0:
                    bisect.insort(tips, parent)
            node._outcount = -1
            self.append(node)
        final_len = len(self)
        if final_len != orig_len:
            raise CyclicGraphError(
                '%d of %d elements not reachable from tips'
                % (orig_len - final_len, orig_len))
        if tip_to_root == False:
            self.reverse()

    def check_for_cycles(self):
        """Check for cyclic references.
        """
        for node in self:
            if node in node.ancestors():
                path = node.parent_path(node)
                raise CyclicGraphError(
                    'cycle detected:\n  %s'
                    % '\n  '.join([repr(node)]+[repr(node) for node in path]))

    def graph_rows(self, tip_to_root=False):
        """Generate a sequence of (`graph_row`, `node`) tuples.

        Preforms :meth:`set_children` and :meth:`topological_sort`
        internally.
        """
        graph_row_generator = GraphRowGenerator(tip_to_root=tip_to_root)
        self.set_children()
        self.topological_sort(tip_to_root=tip_to_root)
        for node in self:
            graph_row_generator.insert(node)
            yield (graph_row_generator[-1], node)

    def ascii_graph(self, graph_row_printer=None, string_fn=str,
                    tip_to_root=False):
        """Print an ascii graph on the left with `string_fn(node)` on
        the right.  If `graph_row_printer` is `None`, a default
        instance of :class:`GraphRowPrinter` will be used.

        See the class docstring for example output.
        """
        if graph_row_printer == None:
            graph_row_printer = GraphRowPrinter()
        graph = []
        for row,node in self.graph_rows(tip_to_root=tip_to_root):
            graph.append('%s %s' % (graph_row_printer(row), string_fn(node)))
        return '\n'.join(graph)
