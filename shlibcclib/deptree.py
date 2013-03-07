# shlibcc -- dependency tree
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'DependencyTree', 'make_deptree', ]

import sys

class DependencyTree ( object ):
   """A dependency tree (as it is implemented here) represents a list of nodes
   with the same depth and a pointer to the next (child-)tree.

   Important for circular dependencies:
   New nodes have to be inserted with the lowest depth that they have.

   Example:

   insert ( A, want_level=5 )
   insert ( A, want_level=0 )

   This won't work as expected. "A" will exist twice.

   insert ( A, want_level=0 )
   insert ( A, want_level=5 )

   ^ works.

   So, take care when choosing the proper algorithm for inserting.
   BFS (breadth-first search), but DFS won't.

   The tree has to be balanced by calling fixup() after inserting all
   dependencies. This will (try to) resolve all conflicts within a level
   by sorting the modules accordingly.
   """

   class DependencyTreeNode ( object ):
      """Tree data element."""
      def __init__ ( self, name, fspath, deps ):
         super ( DependencyTree.DependencyTreeNode, self ).__init__()
         self.name      = name
         self.fspath    = fspath
         # initially, any dependency is a possible conflict
         self.conflicts = set ( deps )
      # --- end of __init__ (...) ---
   # --- end of DependencyTreeNode ---

   def __init__ ( self, parent=None ):
      """DependencyTree constructor.

      arguments:
      * parent -- parent tree, if any. Defaults to None.
      """
      super ( DependencyTree, self ).__init__()

      if parent is None:
         self.depth = 0
      else:
         self.depth = parent.depth + 1

      self._nodes = dict()
      self._child = None
   # --- end of __init__ (...) ---

   def find ( self, name ):
      """Searches for a module (by name) and returns its tree node if found,
      else None.

      argument:
      * name --
      """
      node = self._nodes.get ( name, None )
      if node:
         return node
      elif self._child:
         return self._child.find ( name )
      else:
         return None
   # --- end of find (...) ---

   def has ( self, name ):
      """Returns true if a module named "name" is in the tree, else False."""
      return self.find ( name ) is not None
   # --- end of has (...) ---

   def insert ( self, name, fspath, want_level, deps ):
      """Inserts a module into the dependency tree.

      Returns True if the module has been inserted (is new),
      else False (exists).

      arguments:
      * name       -- name of the module
      * fspath     -- path to the module file
      * want_level -- desired tree level where the module should be inserted
      * deps       -- direct dependencies of the module
      """
      if name not in self._nodes:
         if want_level == self.depth:
            # ^ that's why it is important to use a BFS approach for inserting
            # else we'd have to walk the tree down and search for already
            # inserted nodes
            self._nodes [name] = self.DependencyTreeNode (
               name, fspath, deps
            )
            return True
         else:
            if self._child is None:
               self._child = self.__class__ ( self )
            return self._child.insert ( name, fspath, want_level, deps )
      else:
         return False
   # --- end of insert (...) ---

   def fixup ( self ):
      """Balances this tree, i.e. resolve all conflicts in this tree.

      Raises: Exception if balancing is not possible.
      """
      if self._child:
         # balance child first
         self._child.fixup()

      nodes      = list()
      nodes_done = set()
      nodes_todo = list()

      # module names provided by this level
      provided = frozenset ( self._nodes.keys() )

      # set node conflicts
      for node in self._nodes.values():
         node.conflicts &= ( provided - { node.name } )
         if not node.conflicts:
            nodes.append   ( node )
            nodes_done.add ( node.name )
         else:
            nodes_todo.append ( node )

      # resolve the conflicts
      # while <have conflicts> and <at least one conflict resolved> do
      #    foreach node do
      #       update node conflicts
      #       if <node has no conflicts> then
      #          mark node as resolved
      #       end if
      #    end foreach
      # end while
      #
      while nodes_todo:
         nodes_todo_next = list()

         for node in nodes_todo:
            node.conflicts -= nodes_done

            if not node.conflicts:
               nodes.append   ( node )
               nodes_done.add ( node.name )
            else:
               nodes_todo_next.append ( node )


         if len ( nodes_todo ) == len ( nodes_todo_next ):
            if len ( nodes_todo_next ) <= 2:
               # break simple circle (== 2 would do it, too)
               for node in nodes_todo_next:
                  sys.stderr.write (
                     "Leaving depdencies unresolved for module {}: {}".\
                     format (
                        node.name, ', '.join ( node.conflicts )
                     )
                  )
                  nodes.append   ( node )
                  nodes_done.add ( node.name )

               nodes_todo = None
            else:
               raise Exception ( "complex circular dependencies detected!" )
         else:
            nodes_todo = nodes_todo_next

      # -- end while;

      assert len ( self._nodes ) == len ( nodes )
      self._nodes = nodes

      return self
   # --- end of fixup (...) ---

   def __iter__ ( self ):
      """dependency tree iterator.
      Recursively yields all modules nodes of the child tree and then all
      modules nodes of this tree level (if any).
      """
      if self._child:
         for node in iter ( self._child ):
            yield node

      if hasattr ( self._nodes, 'values' ):
         for node in self._nodes.values():
            yield node
      else:
         for node in self._nodes:
            yield node
   # --- end of __iter__ (...) ---

   def get_height ( self ):
      """Get the height of this tree, i.e. the maximum depth."""
      if self._child:
         return self._child.get_height()
      else:
         return self.depth
   # --- end of get_depth (...) ---

   def gen_str ( self, _height=None, _s_height=None ):
      """Generates strings representing the tree structure."""
      # output format is <<
      # 0 : <module 0x0>
      # 0 : <module 0x1>
      # ...
      # 0 : <module 0xk>
      # 1 : <module 1x0>
      # 1 : <module 1x1>
      # ...
      # 1 : <module 1xk>
      # ...
      # n : <module nx0>
      # n : <module nx1>
      # ...
      # n : <module nxk>
      # >>

      if _height is None:
         height   = self.get_height()
         s_height = len ( str ( height ) )
      else:
         height   = _height
         s_height = _s_height


      if self.depth <= height:

         for node in (
            self._nodes.values() if hasattr ( self._nodes, 'values' )
            else self._nodes
         ):
            if node.conflicts:
               yield "{:<{l}} : {} ({}) UNRESOLVED: {!r}".format (
                  self.depth, node.name, node.fspath, node.conflicts,
                  l=s_height
               )
            else:
               yield "{:<{l}} : {} ({})".format (
                  self.depth, node.name, node.fspath, l=s_height
               )
         # -- end for;

         if self._child:
            for s in self._child.gen_str ( height, s_height ):
               yield s
   # --- end of gen_str (...) ---

   def __str__ ( self ):
      return '\n'.join ( self.gen_str() )
   # --- end of __str__ (...) ---

# --- end of DependencyTree ---


def make_dependency_tree ( modules, D ):
   """Creates a dependency tree.

   arguments:
   * modules -- the top level dependencies (modules requested by the user)
   * D       -- dependency lookup table
   """
   T               = DependencyTree()
   # level 0 is reserved for top-level modules
   level_no        = 0
   level_deps      = set()
   top_level_nodes = frozenset ( D.iter_nodes ( modules, frozen=True ) )

   for node in top_level_nodes:
      level_deps.update ( node [2] )

   while level_deps:
      level_no        += 1
      level_deps_next  = set()

      for name, fspath, module_deps in D.iter_nodes ( level_deps ):
         if T.insert ( name, fspath, level_no, module_deps ):
            level_deps_next |= module_deps

      level_deps = level_deps_next

   # -- end while;

   # add remaining top-level modules to the deptree
   #  this ensures that all modules are inserted where required (and not
   #  necessarily where "requested", which would be level 0)
   #  the downside is increased time complexity here
   for node in top_level_nodes:
      if not T.has ( node [0] ):
         T.insert ( node [0], node [1], 0, node [2] )

   return T.fixup()
# --- end of make_dependency_tree (...) ---
