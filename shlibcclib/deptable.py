# shlibcc -- dependency table
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'DependencyTable', ]

import os
import sys

import shlibcclib.message

debug_print = shlibcclib.message.debug_print


class DependencyTableException ( Exception ):
   pass


class DependencyTable ( object ):
   """A DependencyTable lists all modules and their direct dependencies."""

   class DependencyTableNode ( object ):

      def __init__ ( self, name, fspath ):
         super ( DependencyTable.DependencyTableNode, self ).__init__()
         self.name        = name
         self.fspath      = fspath
         self.direct_deps = set()
      # --- end of __init__ (...) ---

      def register_direct_dep ( self, dep ):
         """Adds a modules dependency."""
         self.direct_deps.add ( dep )
      # --- end of register_direct_dep (...) ---

      def __str__ ( self ):
         return "* {file} ({name}) => {deps}".format (
            file = self.fspath,
            name = self.name,
            deps = ' '.join ( self.direct_deps ) or "<none>",
         )
      # --- end of __str__ (...) ---

   # --- end of DependencyTableNode ---

   def __init__ ( self ):
      # name => direct deps
      self._table = dict()
      self.last   = None
   # --- end of __init__ (...) ---

   def iter_nodes ( self, module_names, frozen=False ):
      """Iterator that yields all requested modules.

      arguments:
      * module_names --
      * frozen       -- whether to make the generated tuples hashable (True)
                        or not (False). Defaults to False, which is faster.
      """
      for m in module_names:
         name = os.path.normpath ( m )
         node = self._table [name]
         assert node.name == name
         yield (
            node.name,
            node.fspath,
            frozenset ( node.direct_deps ) if frozen else node.direct_deps
         )
   # --- end of iter_entries (...) ---

   def names ( self ):
      return self._table.keys()
   # --- end of names (...) ---

   def get_names ( self ):
      return list ( self._table.keys() )
   # --- end of get_names (...) ---

   def __iter__ ( self ):
      """Iterator that yields all modules."""
      return iter ( self._table.values() )
   # --- end of __iter__ (...) ---

   def add_new ( self, name, fspath ):
      """Adds a module to this table.

      Returns True if an entry for the module has been added (module is new),
      else False (module exists).

      arguments:
      * name   -- name of the module
      * fspath -- path to the module file
      """
      if name in self._table:
         self.last = None
         return False
      else:
         self.last = self.DependencyTableNode ( name, fspath )
         self._table [name] = self.last
         return True
   # --- end of add_new (...) ---

   def __str__ ( self ):
      return '\n'.join ( str ( node ) for node in self )
   # --- end of __str__ (...) ---

   def get_file_list ( self ):
      for node in self:
         yield ( node.name, node.fspath )
   # --- end of get_file_list (...) ---

# --- end of DependencyTable ---
