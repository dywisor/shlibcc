# shlibcc -- module library
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import os
import sys
import itertools

from itertools import islice

import shlibcclib.message
import shlibcclib.deptable
import shlibcclib.deputil

from shlibcclib.deputil  import locate_depfile, read_depfile
from shlibcclib.deptable import DependencyTable, DependencyTableException

debug_print = shlibcclib.message.debug_print




class ModuleLibraryException ( Exception ):
   pass

class ModuleLibraryFileException ( ModuleLibraryException ):
   pass

class ModuleLibraryFileNotFoundException ( ModuleLibraryFileException ):
   pass

class MaxSearchDepthReached ( ModuleLibraryException ):

   def __init__ ( self, N, backtrace, name ):
      super ( MaxSearchDepthReached, self ).__init__ (
         'max depth {depth!r} reached while searching for modules '
         '({modules!r} -> {mod}) - consider increasing --max-depth'.format (
            depth   = N,
            modules = backtrace,
            mod     = name,
         )
      )
   # --- end of __init__ (...) ---

# --- end of MaxSearchDepthReached ---

class ModuleBlockers ( object ):


   def __init__ ( self, module_blockers=None, source=None ):
      super ( ModuleBlockers, self ).__init__()
      self._blockers_dict = {}
      if module_blockers:
         self.extend ( module_blockers, source )
   # --- end of __init__ (...) ---

   def extend ( self, blockers, source=None ):
      blockers_dict = self._blockers_dict
      if source is None:
         for name in blockers:
            if name not in blockers_dict:
               blockers_dict [name] = set()
      else:
         for name in blockers:
            if name in blockers_dict:
               blockers_dict [name].add ( source )
            else:
               blockers_dict [name] = { source, }
   # --- end of extend (...) ---

   def iter_intersection ( self, names ):
      blockers_dict = self._blockers_dict
      for name in names:
         entry = blockers_dict.get ( name, None )
         if entry is not None:
            yield ( name, entry )
   # --- end of iter_intersection (...) ---

   def intersection ( self, names ):
      return dict ( self.iter_intersection ( names ) )
   # --- end of intersection (...) ---

   def __and__ ( self, other ):
      if hasattr ( other, 'get_names' ):
         return self.intersection ( other.get_names() )
      elif hasattr ( other, '__iter__' ):
         return self.intersection ( other )
      else:
         return NotImplemented
   # --- end of __and__ (...) ---

   def __str__ ( self ):
      return "{cls.__name__}({blockers})".format (
         cls=self.__class__,
         blockers=', '.join ( repr(k) for k in self._blockers_dict.keys() )
      )
   # --- end of __str__ (...) ---

   def handle_blocker ( self, directory ):
      raise NotImplementedError()

# --- end of ModuleBlockers ---



class ModuleRootDirectory ( object ):

   def __init__ ( self, fspath ):
      super ( ModuleRootDirectory, self ).__init__()
      self.fspath  = os.path.abspath ( fspath )
      self.fspath_relpath_begin = len(self.fspath) + 1

   def get_fspath ( self, relpath=None ):
      if relpath:
         return os.path.join ( self.fspath, relpath.lstrip(os.sep) )
      else:
         return self.fspath

   def get_relpath ( self, abspath ):
      return abspath[self.fspath_relpath_begin:] or None

   def ilocate_file ( self, filetypes, name ):
      basepath = self.get_fspath ( name )

      for ftype in filetypes:
         fpath = basepath + ftype
         if os.path.isfile ( fpath ):
            yield ( ftype, basepath, fpath )
   # --- end of ilocate_file (...) ---

class ModuleRootDirectories ( object ):

   FTYPE_SH   = '.sh'
   FTYPE_BASH = '.bash'

   def __init__ ( self, dirpaths, use_bash ):
      super ( ModuleRootDirectories, self ).__init__()
      self.module_directories  = (
          [ ModuleRootDirectory(p) for p in ( dirpaths or () ) ]
      )
      self.module_filetypes    = []

      if use_bash:
         self.module_filetypes.append ( ModuleRootDirectories.FTYPE_BASH )

      self.module_filetypes.append ( ModuleRootDirectories.FTYPE_SH )
   # --- end of __init__ (...) ---

   def iter_module_directories ( self, offset ):
      for k, module_dir in enumerate (
         islice ( self.module_directories, offset, None )
      ):
         yield ( (offset+k), module_dir )
   # ---

   def ifind_module_file ( self, name, offset ):
      filetypes = self.module_filetypes
      for k, module_dir in self.iter_module_directories(offset):
         for result in module_dir.ilocate_file ( filetypes, name ):
            yield ( k, module_dir, result )

   def ifind_module_dir ( self, name, offset ):
      if not name or name == os.sep:
         name = None

      for k, module_dir in self.iter_module_directories(offset):
         dirpath = module_dir.get_fspath ( name )
         if os.path.isdir ( dirpath ):
            yield ( k, module_dir, ( None, dirpath, dirpath ) )

   def find_module ( self, name, offset ):
      for result in self.ifind_module_dir ( name, offset ):
         return result

      for result in self.ifind_module_file ( name, offset ):
         return result

      raise ModuleLibraryFileNotFoundException ( name )
# ---

class ModuleLibrary ( object ):

   def handle_blocker ( self, module_directory, dirpath ):
      if self.blocker_action == self.blocker_action.ACTION_IGNORE:
         return True

      blocker = module_directory.get_fspath ( dirpath + os.sep + "block_CC" )
      if not os.path.exists ( blocker ):
         return True

      msg = "CC blocker found in {}".format (
         module_directory.get_relpath(dirpath)
      )

      if self.blocker_action == self.blocker_action.ACTION_EXCLUDE:
         sys.stderr.write (
            "[WARN] {} - excluding it\n".format ( msg )
         )
         return False

      elif self.blocker_action == self.blocker_action.ACTION_EXCLUDE_QUIET:
         return False

      elif self.blocker_action == self.blocker_action.ACTION_WARN:
         sys.stderr.write ( "[WARN] {}\n".format ( msg ) )
         return True

      else:
         self.config.die ( msg + "!" )
   # --- end of handle_blocker (...) ---

   def populate_deptable ( self, modules ):
      MODULE_DIRECTORIES = self.module_directories
      MAXDEPTH           = self.max_search_depth
      MODULES_EXCLUDE    = self.modules_exclude
      MODULE_BLOCKERS    = self.module_blockers
      DEPTABLE           = self.deptable

      def populate_deptable_inner (
         backtrace, search_offset, want_name
      ):
         def is_cwd_ref ( s ):
            return not s or s in { os.sep, '.' }

         def get_subkey ( parent_key, basename ):
            if is_cwd_ref ( parent_key ):
               return basename
            else:
               return parent_key + os.sep + basename
         # --- end of get_subkey (...) ---

         def populate_deptable_from_file (
            backtrace, module_dir, search_offset,
            module_key, module_path, module_basepath
         ):
            if len ( backtrace ) >= MAXDEPTH:
               raise MaxSearchDepthReached ( MAXDEPTH, backtrace, module_key )

            elif module_key in MODULES_EXCLUDE:
               return False

            elif not DEPTABLE.add_new ( module_key, module_path ):
               return True

            else:
               node    = DEPTABLE.last
               depfile = locate_depfile ( module_path, module_basepath )

               if depfile:
                  debug_print (
                     "depfile of module {!r} is {!r}".format (
                        module_key, depfile
                     )
                  )

                  # read deps, blockers
                  deps, blockers = read_depfile ( depfile )

                  if blockers:
                     MODULE_BLOCKERS.extend ( blockers, source=module_key )

                  for dep in deps:
                     # FIXME: not accurate...
                     if (
                        dep.startswith ( "." + os.sep )
                        or dep.startswith ( ".." + os.sep )
                     ):
                        dep_name = os.path.normpath (
                           get_subkey ( os.path.dirname(module_key), dep )
                        )
                     else:
                        dep_name = dep
                     # --

                     if populate_deptable_inner (
                        backtrace, search_offset, dep_name
                     ):
                        debug_print (
                           "module {!r}: add dep {!r}".format (
                              module_key, dep_name
                           )
                        )
                        node.register_direct_dep ( dep_name )
               else:
                  debug_print (
                     "module {!r} has no dependencies.".format ( module_key )
                  )

               return True
         # --- end of populate_deptable_from_file (...) ---

         def populate_deptable_from_directory (
            backtrace, module_dir, search_offset,
            module_key, module_path
         ):
            if len ( backtrace ) >= MAXDEPTH:
               raise MaxSearchDepthReached ( MAXDEPTH, backtrace, module_key )

            elif module_key in MODULES_EXCLUDE:
               return False

            elif not self.handle_blocker ( module_dir, module_path ):
               return True

            elif not DEPTABLE.add_new ( module_key, module_path ):
               return True

            else:
               node = DEPTABLE.last

               for dirpath, dirnames, filenames in os.walk ( module_path ):
                  for basename in dirnames:
                     fspath = module_path + os.sep + basename
                     key    = get_subkey ( module_key, basename )

                     if populate_deptable_from_directory (
                        backtrace + [ basename ],
                        module_dir,
                        search_offset,
                        key,
                        fspath
                     ):
                        node.register_direct_dep ( key )
                  # --

                  for fname in filenames:
                     basename, suffix = os.path.splitext ( fname )
                     if suffix not in MODULE_DIRECTORIES.module_filetypes:
                        continue

                     fspath   = module_path + os.sep + fname
                     basepath = module_path + os.sep + basename
                     key      = get_subkey ( module_key, basename )

                     for other_suffix in MODULE_DIRECTORIES.module_filetypes:
                        if other_suffix == suffix:
                           if populate_deptable_from_file (
                              backtrace + [ basename ],
                              module_dir,
                              search_offset,
                              key,
                              fspath,
                              basepath
                           ):
                              node.register_direct_dep ( key )
                        elif os.path.isfile ( basepath + other_suffix ):
                           break
                     # --
                  # --

                  # non-recursive os.walk()
                  break
               # ---
         # --- end of populate_deptable_from_directory (...) ---

         if len ( backtrace ) >= MAXDEPTH:
            raise MaxSearchDepthReached ( MAXDEPTH, backtrace, want_name )
         # --

         if not is_cwd_ref ( want_name ):
            pass
         elif backtrace or search_offset:
            raise ModuleLibraryFileException (
               "cannot include module root from sublevel."
            )
         elif not MODULE_DIRECTORIES.module_directories:
            pass
         else:
            return populate_deptable_from_directory (
               backtrace + [ "/" ],
               MODULE_DIRECTORIES.module_directories[0],
               search_offset,
               "/",
               MODULE_DIRECTORIES.module_directories[0].fspath
            )
         # --

         offset, module_dir, module_info = (
            MODULE_DIRECTORIES.find_module ( want_name, search_offset )
         )
         module_type     = module_info[0]
         module_basepath = module_info[1]
         module_path     = module_info[2]
         module_key      = module_dir.get_relpath ( module_basepath )

         if module_type is None:
            return populate_deptable_from_directory (
               backtrace + [ module_key ],
               module_dir,
               offset,
               module_key,
               module_path
            )

         else:
            return populate_deptable_from_file (
               backtrace,
               module_dir,
               offset,
               module_key,
               module_path,
               module_basepath
            )
      # --- end of populate_deptable_inner (...) ---

      for module in modules:
         populate_deptable_inner ( [], 0, module )

      blocked_modules = MODULE_BLOCKERS & DEPTABLE
      if blocked_modules:
         HLINE = 79 * '='
         sys.stderr.write (
            HLINE + "\nunsatisfiable module dependencies:\n"
            + '\n'.join (
               "* {module} blocked by {blockers}".format (
                  module=k, blockers=', '.join ( repr(x) for x in v )
               ) for k, v in sorted ( blocked_modules.items() )
            )
            + '\n' + HLINE + '\n'
         )
         raise DependencyTableException ( "cannot create dependency table" )
      # --
   # --- end of populate_deptable (...) ---

   def __init__ ( self, config, rootdirs ):
      super ( ModuleLibrary, self ).__init__()
      self.config              = config
      self.max_search_depth    = config.max_depth
      self.modules_exclude     = config.modules_exclude
      self.blocker_action      = config.blocker_action
      self.deptable            = DependencyTable()
      self.module_blockers     = ModuleBlockers (
         config.module_blockers, source='__config__'
      )
      self.module_directories  = ModuleRootDirectories (
         rootdirs, config.use_bash
      )



def make_dependency_table ( rootdirs, modules, config ):
   """Creates a dependency table.

   arguments:
   * rootdirs -- shlib root directories (in descending order)
   * modules  -- modules requested by the user (module names)
   * config   -- configuration
   """

   module_library = ModuleLibrary ( config, rootdirs )
   module_library.populate_deptable ( modules )
   return module_library.deptable
# --- end of make_dependency_table (...) ---
