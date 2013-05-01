# shlibcc -- dependency graph (+dependency resolution)
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import shlibcclib.generic.graph

class ModuleData ( object ):

   def __init__ ( self, name, fspath ):
      self.name   = name
      self.fspath = fspath
   # --- end of __init__ (...) ---

   def __str__ ( self ):
      return self.name
   # --- end of __str__ (...) ---



class DependencyGraph ( shlibcclib.generic.graph.DirectedGraph ):

   def __init__ ( self, deptable ):
      super ( DependencyGraph, self ).__init__()

      for deptable_node in iter ( deptable ):
         if deptable_node.name != '.':
            self.add_node (
               deptable_node.name,
               ModuleData ( deptable_node.name, deptable_node.fspath ),
               deptable_node.direct_deps,
            )

      self.expand()
   # --- end of __init__ (...) ---

   def sort_dependencies ( self ):
      # the result of toposort is a list where a node at position k
      # _can_ depend on any other node with position l >= k
      # => reverse the list
      return list (
         item [1] for item in reversed ( self.toposort() )
      )
   # --- end of sort_dependencies (...) ---

# --- end of DependencyGraph ---

class DependencyList ( object ):

   def __init__ ( self, deptable ):
      self.depgraph = DependencyGraph ( deptable )
      self.deplist  = self.depgraph.sort_dependencies()
   # --- end of __init__ (...) ---

   def __iter__ ( self ):
      return iter ( self.deplist )
   # --- end of __iter__ (...) ---

   def __str__ ( self ):
#      max_i_len = max ( 1, len ( str ( len ( self.deplist ) ) ) )
#
#      return '\n'.join (
#         "{n:>{l}}: {name}".format ( n=( i + 1 ), name=data.name, l=max_i_len )
#         for i, data in enumerate ( self.deplist )
#      )
      return '\n'.join ( data.name for data in self.deplist )
   # --- end of __str__ (...) ---
