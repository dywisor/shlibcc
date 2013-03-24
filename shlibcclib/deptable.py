# shlibcc -- dependency table
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'DependencyTable', 'make_dependency_table' ]

import os

import shlibcclib.message

debug_print = shlibcclib.message.debug_print

class MaxRecursionDepthReached ( Exception ):

   def __init__ ( self, N, backtrace, name ):
      super ( MaxRecursionDepthReached, self ).__init__ (
         'max depth {depth!r} reached while searching for modules '
         '({modules!r} -> {mod}) - consider increasing --max-depth'.format (
            depth   = N,
            modules = backtrace,
            mod     = name,
         )
      )
   # --- end of __init__ (...) ---

# --- end of MaxRecursionDepthReached ---

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

   def __iter__ ( self ):
      """)terator that yields all modules."""
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


def make_dependency_table ( root, modules, config ):
   """Creates a dependency table.

   arguments:
   * root    -- shlib root directory (currently, this must be a single dir)
   * modules -- modules requested by the user (module names)
   * config  -- configuration
   """
   SUFFIX_DEPEND = '.depend'
   SUFFIX_SH     = '.sh'
   SUFFIX_BASH   = '.bash'

   STRIP_DIR       = os.sep + '.'
   MAX_REC_DEPTH   = config.max_depth
   MODULES_EXCLUDE = config.modules_exclude

   D = DependencyTable()

   def file_lookup_sh ( name, basename=None ):
      """Tries to find a sh file."""
      b = basename or os.path.join ( root, name )
      s = b + SUFFIX_SH
      if os.path.isfile ( s ):
         return ( b, s )
      else:
         None
   # --- end of file_lookup_sh (...) ---

   def file_lookup_bash ( name ):
      """Tries to find a bash file. Falls back to file_lookup_sh()."""
      b = os.path.join ( root, name )
      s = b + SUFFIX_BASH
      if os.path.isfile ( s ):
         return ( b, s )
      else:
         return file_lookup_sh ( name, basename=b )
   # --- end of file_lookup_bash (...) ---

   def depfile_lookup ( basename, fname ):
      """Tries to find a dependency file."""
      if os.path.isfile ( fname + SUFFIX_DEPEND ):
         return fname + SUFFIX_DEPEND
      elif os.path.isfile ( basename + SUFFIX_DEPEND ):
         return basename + SUFFIX_DEPEND
      else:
         return None
   # --- end of depfile_lookup (...) ---

   file_lookup = file_lookup_bash if config.use_bash else file_lookup_sh

   def deptable_populate ( name, backtrace ):
      """Populates the dependency table.

      Adds the given module and all of its dependencies to the table.
      """
      def deptable_populate_from_file (
         fspath_noext, fspath, module_name, backtrace
      ):
         """Adds a module file to the table."""
         if len ( backtrace ) >= MAX_REC_DEPTH:
            raise MaxRecursionDepthReached (
               MAX_REC_DEPTH, backtrace, module_name
            )

         elif module_name in MODULES_EXCLUDE:

            return False

         elif D.add_new ( module_name, fspath ):
            node    = D.last
            depfile = depfile_lookup ( fspath_noext, fspath )

            if depfile:
               debug_print (
                  "depfile of module {!r} is {!r}".format (
                     module_name, depfile
                  )
               )

               # recursion, fetch all deps and parse them afterwards
               with open ( depfile, 'rt' ) as FH:
                  deps = [ l.strip() for l in FH.readlines() ]

               for dep in deps:
                  if dep and dep [0] != '#':
                     if deptable_populate (
                        name      = dep,
                        backtrace = backtrace,
                     ):
                        debug_print (
                           "module {!r}: add dep {!r}".format (
                              module_name, dep
                           )
                        )
                        node.register_direct_dep ( dep )
            else:
               debug_print (
                  "module {!r} has no dependencies.".format ( module_name )
               )


            return True
         else:
            return True
      # --- end of deptable_populate_from_file (...) ---

      def deptable_populate_from_directory ( directory, dir_name, backtrace ):
         """Adds a directory to the table."""

         # recursively expand directory
         if len ( backtrace ) >= MAX_REC_DEPTH:
            raise MaxRecursionDepthReached (
               MAX_REC_DEPTH, backtrace, dir_name
            )

         elif dir_name in MODULES_EXCLUDE:

            return False

         elif D.add_new ( dir_name, directory ):
            node = D.last

            for fname in os.listdir ( directory ):

               fpath = directory + os.sep + fname
               if directory == root or not dir_name:
                  module_name = fname
               else:
                  module_name = dir_name + os.sep + fname

               if os.path.isdir  ( fpath ):
                  if deptable_populate_from_directory (
                     directory = fpath,
                     dir_name  = module_name,
                     backtrace = backtrace + [ dir_name ],
                  ):
                     node.register_direct_dep ( module_name )
               elif config.use_bash and \
                  fpath [ -len ( SUFFIX_BASH ): ] == SUFFIX_BASH \
               :
                  module_name = module_name [ : - len ( SUFFIX_BASH ) ]

                  if deptable_populate_from_file (
                     fspath_noext = fpath [ : -len ( SUFFIX_BASH ) ],
                     fspath       = fpath,
                     module_name  = module_name,
                     backtrace    = backtrace + [ dir_name ],
                  ):
                     node.register_direct_dep ( module_name )

               elif fpath [ -len ( SUFFIX_SH ): ] == SUFFIX_SH:

                  module_name = module_name [ : - len ( SUFFIX_SH ) ]

                  if deptable_populate_from_file (
                     fspath_noext = fpath [ : -len ( SUFFIX_SH ) ],
                     fspath       = fpath,
                     module_name  = module_name,
                     backtrace    = backtrace + [ dir_name ],
                  ):
                     node.register_direct_dep ( module_name )
               # -- end if;
            # -- end for;
            return True
         else:
            return True
      # --- end of deptable_populate_from_directory (...) ---


      # find module <name> and call deptable_populate_from_*

      mod_dir = os.path.abspath ( os.path.join ( root, name ) )

      if len ( backtrace ) >= MAX_REC_DEPTH:
         raise MaxRecursionDepthReached (
            MAX_REC_DEPTH, backtrace, name
         )

      elif name [-1] == os.sep or os.path.isdir ( mod_dir ):
         return deptable_populate_from_directory (
            mod_dir, os.path.normpath ( name ), backtrace + [ name ]
         )

      else:
         mod = file_lookup ( name )
         if mod:
            return deptable_populate_from_file (
               fspath_noext = mod [0],
               fspath       = mod [1],
               module_name  = name,
               backtrace    = backtrace
            )
         else:
            raise Exception (
               "no such module: {}; backtrace : {}".format (
                  name,
                  ' -> '.join ( backtrace ) if backtrace else '<none>'
               )
            )

   # --- end of deptable_populate (...) ---

   for module in modules:
      deptable_populate ( module, [] )

   return D
# --- end of make_dependency_table (...) ---
