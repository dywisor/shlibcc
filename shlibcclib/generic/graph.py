# shlibcc -- (generic) directed graph
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

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

   def visualize_edges ( self, reverse=False ):
      def gen_edges_str():
         for node in self._nodes.values():
            node_str = str ( node )
            for dest_node in node.get_nodes():
               yield "{src} ==> {dest}".format (
                  src  = node_str,
                  dest = str ( dest_node )
               )
      # --- end of gen_edges_str (...) ---

      def gen_reverse_edges_str():
         for node in self._nodes.values():
            node_str = str ( node )
            for src_node in node.get_reverse_nodes():
               yield "{dest} <== {src}".format (
                  src  = str ( src_node ),
                  dest = node_str
               )

      return '\n'.join (
         gen_reverse_edges_str() if reverse else gen_edges_str()
      )
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

      if T.has_edges():
         raise self.GraphException ( "Graph has >= 1 cycle." )
      else:
         return list (
            ( node.get_name(), node.get_data() )
            for node in sorted_nodes
         )

   # --- end of toposort_kahn (...) ---

   def toposort ( self ):
      """Sorts the nodes of this graph in topological order.

      Returns a (sorted) list of 2-tuples ( node_name, node_data ).
      """
      return self.toposort_kahn()
   # --- end of sort_topological (...) ---
