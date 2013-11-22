# shlibcc -- (generic) directed graph
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

def get_max_colsize ( *tables ):
   if not tables:
      return None

   try:
      max_colsizes = len ( tables[0][0] ) * [0]
   except IndexError:
      max_colsizes = []

   for rows in tables:
      for row in rows:
         for i, col in enumerate ( row ):
            try:
               current_max = max_colsizes[i]
            except IndexError:
               # resize
               max_colsizes.append ( 0 )
               current_max = 0
            # -- end try

            max_colsizes[i] = max ( current_max, len ( col ) )
         # -- end for
      # -- end for
   # -- end for

   return max_colsizes
# --- end of get_max_colsize (...) ---

def format_table (
   row_data, header=None, join_str=' ',
   postheader_fillchar='-', header_join_str=None
):
   get_coljust_len = lambda col, csize: (len(col)+csize+1)//2

   #rows = [ str(d) for d in row_data ]
   if isinstance ( row_data, list ):
      rows = row_data
   else:
      rows = list ( row_data )

   if rows:
      my_data_join_str = join_str

      if header and any ( header ):
         if header_join_str is None:
            sepa_len           = len ( join_str )
            my_header_join_str = join_str

         else:
            header_j_len       = len ( header_join_str )
            j_len              = len ( join_str )
            sepa_len           = header_j_len
            my_header_join_str = header_join_str

            if header_j_len < j_len:
               my_header_join_str = header_join_str.center ( j_len )
               sepa_len           = j_len
            elif header_j_len > j_len:
               my_data_join_str = join_str.center ( header_j_len )

            del header_j_len, j_len
         # -- end if

         colsize     = get_max_colsize ( header, rows )
         last_col    = len ( colsize ) - 1
         table_width = sum ( colsize ) + sepa_len

         dojoin = my_header_join_str.join
         for row in header:
            yield dojoin (
               (
                  col.center ( colsize[i] ) if i < last_col
                     else col.rjust ( get_coljust_len ( col, colsize[i] ) )
               ) for i, col in enumerate ( row )
            )

            if postheader_fillchar:
               yield table_width * postheader_fillchar
         # -- end for
         del dojoin

      else:
         colsize          = get_max_colsize ( rows )
         last_row         = len ( colsize ) - 1
         my_data_join_str = join_str
         #table_width = sum ( colsize ) + len ( join_str )


      dojoin = my_data_join_str.join
      for row in rows:
         yield dojoin (
            ( col.ljust ( colsize[i] ) if i < last_col else col )
            for i, col in enumerate ( row )
         )
   # -- end if rows
# --- end of format_table (...) ---

def swap_pairs ( iterable ):
   for a, b in iterable:
      yield ( b, a )
# --- end of swap_pairs (...) ---


class Node ( object ):

   def __init__ ( self, name, data ):
      super ( Node, self ).__init__()
      self._name          = name
      self._data          = data
      self._edges         = set()
      self._edges_reverse = set()
   # --- end of __init__ (...) ---

   def __str__ ( self ):
      return str ( self._data or self._name )
   # --- end of __str__ (...) ---

   def get_data ( self ):
      return self._data
   # --- end of get_data (...) ---

   def get_name ( self ):
      return str ( self._name )
   # --- end of get_name (...) ---

   def get_nodes ( self ):
      return self._edges
   # --- end of get_nodes (...) ---

   def get_reverse_nodes ( self ):
      return self._edges_reverse
   # --- end of get_reverse_nodes (...) ---

   def get_node_names ( self ):
      return set (
         node.get_name() for node in self.get_nodes()
      )
   # --- end of get_node_names (...) ---

   def add_edge ( self, node, add_reverse=False ):
      self._edges.add ( node )
      if add_reverse:
         node.add_reverse_edge ( self )
   # --- end of add_edge (...) ---

   def remove_reverse_edge ( self, node ):
      self._edges_reverse.remove ( node )
   # --- end of remove_reverse_edge (...) ---

   def remove_edge ( self, node, remove_reverse=False ):
      if remove_reverse:
         node.remove_reverse_edge ( self )
      self._edges.remove ( node )
   # --- end of remove_edge (...) ---

   def add_reverse_edge ( self, node ):
      self._edges_reverse.add ( node )
   # --- end of add_reverse_edge (...) ---

   def has_incoming_edges ( self ):
      return bool ( self._edges_reverse )
   # --- end of has_incoming_edges (...) ---

   def has_outgoing_edges ( self ):
      return bool ( self._edges )
   # --- end of has_outgoing_edges (...) ---

# --- end of Node ---

class DirectedGraph ( object ):

   class GraphException ( Exception ):
      pass

   class NodeException ( Exception ):
      pass

   class NodeNotUniqueException ( NodeException ):
      pass

   class NodeMissingException ( NodeException ):
      pass

   def __init__ ( self ):
      super ( DirectedGraph, self ).__init__()
      self._nodes       = dict()
      self._entry_nodes = None
      self._expanded    = True
   # --- end of __init__ (...) ---

   def __str__ ( self ):
      if self._expanded:
         return self.visualize_edges()
      else:
         return super ( DirectedGraph, self ).__str__()
   # --- end of __str__ (...) ---

   def add_node ( self, name, data, edges_to ):
      """Adds a node to this graph.

      arguments:
      * name     -- a string identifying the node (has to be unique)
      * data     -- the node's data (or None)
                     this item will never be modified, but will always be
                     passed as reference (e.g. when sorting)
      * edges_to -- an iterable of nodes to which this node points to

      Note: You have to call expand() in order to establish all edges
            and to find entry points (nodes without incoming edges).
      """
      if name in self._nodes:
         raise self.NodeNotUniqueException ( name )
      elif edges_to:
         self._nodes [name] = ( Node ( name, data ), edges_to )
      else:
         self._nodes [name] = Node ( name, data )

      self._expanded = False
   # --- end of add_node (...) ---

   def copy ( self ):
      """Returns a copy of this graph with all nodes expanded.

      Use this if you need a copy to safely work on (e.g. topological sorting).
      """
      T = (
         self._copy_class
         if hasattr ( self, '_copy_class' ) else DirectedGraph
      )()

      for name, node in self._nodes.items():
         T.add_node ( name, node.get_data(), node.get_node_names() )

      return T.expand()
   # --- end of copy (...) ---

   def expand ( self ):
      """Establish all edges / find entry points etc.

      Returns self (this object).

      Has to be called after adding all nodes.
      """

      ## rebuild self._nodes with all edges
      nodes_expanded = dict()

      for name, node_item in self._nodes.items():
         if isinstance ( node_item, tuple ):
            node     = node_item [0]
            edges_to = node_item [1]

            for dest_name in edges_to:
               dest_node = self._nodes [dest_name]

               if isinstance ( dest_node, tuple ):
                  node.add_edge ( dest_node [0], add_reverse=True )
               else:
                  node.add_edge ( dest_node, add_reverse=True )

            nodes_expanded [name] = node
         else:
            nodes_expanded [name] = node_item
      # -- end for;

      self._nodes = nodes_expanded

      ## find entry nodes

      self._entry_nodes = set()

      for node in self._nodes.values():
         if not node.has_incoming_edges():
            self._entry_nodes.add ( node )
      # -- end for;

      self._expanded = True

      return self
   # --- end of expand (...) ---

   def has_edges ( self ):
      for node in self._nodes.values():
         if node.has_outgoing_edges():
            return True
      return False
   # --- end of has_edges (...) ---

   def iter_edges ( self ):
      for node in self._nodes.values():
         node_str = str ( node )
         for dest_node in node.get_nodes():
            yield ( node_str, str ( dest_node ) )
   # --- end of iter_edges (...) ---

   def iter_reverse_edges ( self ):
      for node in self._nodes.values():
         node_str = str ( node )
         for src_node in node.get_reverse_nodes():
            yield ( str ( src_node ), node_str )
   # --- end of iter_reverse_edges (...) ---

   def visualize_edges ( self, reverse=False, pretty_print=True ):
      if reverse:
         iter_edges = swap_pairs ( self.iter_reverse_edges() )
         join_str   = ' <== '
         header     = [( '<module>', '<required by>' )]
      else:
         iter_edges = self.iter_edges()
         join_str   = ' ==> '
         header     = [( '<module>', '<depends on>' )]

      if pretty_print:
         return '\n'.join ( format_table (
            sorted ( iter_edges, key=lambda k: ( k[0].count('/'), k[0] ) ),
            header, join_str
         ) )
      else:
         return '\n'.join ( join_str.join ( k ) for k in iter_edges )
   # --- end of visualize_edges (...) ---

   def toposort_kahn ( self ):
      """Topological ordering using Kahn's algorithm."""
      # T is a work copy of self
      T = self.copy()

      sorted_nodes = list()

      while T._entry_nodes:
         entry_node = T._entry_nodes.pop()
         sorted_nodes.append ( entry_node )

         edges_to = set ( entry_node.get_nodes() )

         for dest_node in edges_to:
            entry_node.remove_edge ( dest_node, remove_reverse=True )

            if not dest_node.has_incoming_edges():
               T._entry_nodes.add ( dest_node )
      # --- end while

      if T.has_edges():
         raise self.GraphException ( "Graph has >= 1 cycle." )
      else:
         return list (
            ( node.get_name(), node.get_data() )
            for node in sorted_nodes
         )

   # --- end of toposort_kahn (...) ---

   def toposort_kahn_stable ( self ):
      """Stable topological ordering using Kahn's algorithm."""
      def nodesort ( iterable ):
         return sorted ( iterable, key=lambda node: node.get_name() )
      # --- end of nodesort (...) ---

      # it's important that sorted returns an independent iterable,
      # i.e. not a view (iterator, ...), see the for-loop below
      assert isinstance ( sorted ( set() ), list )

      # T is a work copy of self
      T = self.copy()
      T._entry_nodes = nodesort ( T._entry_nodes )

      sorted_nodes = list()

      while T._entry_nodes:
         new_entry_nodes = False
         entry_node      = T._entry_nodes.pop()
         sorted_nodes.append ( entry_node )

         for dest_node in nodesort ( entry_node.get_nodes() ):
            # modifying entry_node's edges while iterating over them,
            # that's why sorted() has to return an independent iterable
            entry_node.remove_edge ( dest_node, remove_reverse=True )

            if not dest_node.has_incoming_edges():
               new_entry_nodes = True
               T._entry_nodes.append ( dest_node )

         if new_entry_nodes:
            T._entry_nodes = nodesort ( T._entry_nodes )
      # --- end while

      if T.has_edges():
         raise self.GraphException ( "Graph has >= 1 cycle." )
      else:
         return list (
            ( node.get_name(), node.get_data() )
            for node in sorted_nodes
         )

   # --- end of toposort_kahn_stable (...) ---

   def toposort ( self, stable=False ):
      """Sorts the nodes of this graph in topological order.

      Returns a (sorted) list of 2-tuples ( node_name, node_data ).

      arguments:
      * stable -- whether the result should be "stable" (predictable order)
                  or not
      """
      return self.toposort_kahn_stable() if stable else self.toposort_kahn()
   # --- end of sort_topological (...) ---
