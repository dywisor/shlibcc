# shlibcc -- shlib module linker, config
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'ShlibccConfig', 'main', ]

import os
import sys
import argparse

import shlibcclib.deptable
import shlibcclib.deptree
import shlibcclib.linker
import shlibcclib.message

version     = ( 0, 0, 3 )
__version__ = '.'.join ( str ( a ) for a in version )


class ShlibccConfig ( object ):
   """The shlibcc config data structure. Also handles arg parsing."""

   def get_parser ( self, ACTIONS, DEFAULT_ACTION ):

      def is_fs_dir ( v ):
         d = os.path.abspath ( v )
         if not os.path.isdir ( d ):
            raise argparse.ArgumentTypeError (
               "{!r} is not a directory.".format ( v )
            )
         else:
            return d
      # --- end of is_fs_dir (...) ---

      def is_fs_file_or_none ( v ):
         if v is None:
            return None
         elif v is True:
            return True
         elif v is False:
            return False
         else:
            a = os.path.abspath ( v )
            if os.path.isfile ( a ):
               return a
            else:
               raise argparse.ArgumentTypeError (
                  "file {!r} does not exist.".format ( v )
               )
       # --- end of is_fs_file_or_none (...) ---

      def couldbe_output_file ( v ):
         if v == '-':
            return v
         else:
            f = os.path.abspath ( v )
            if os.path.exists ( f ):
               raise argparse.ArgumentTypeError (
                  "output file {!r} exists".format ( f )
               )
            elif not os.path.isdir ( os.path.dirname ( f ) ):
               raise argparse.ArgumentTypeError (
                  'parent directory does not exists '
                  'for output file {!r}'.format ( f )
               )
            else:
               return f
      # --- end of couldbe_output_file (...) ---

      parser = argparse.ArgumentParser (
         description = "shlib linker version " + self.version_str,
         add_help    = True
      )
      arg = parser.add_argument

      action_grp = parser.add_argument_group (
         "actions", "set the shlibcc mode"
      )
      action_arg = action_grp.add_argument

      output_grp = parser.add_argument_group (
         "output options", "control creation of the linked module"
      )
      output_arg = output_grp.add_argument

      shlib_grp = parser.add_argument_group (
         "shlib options", "shell module library options"
      )
      shlib_arg = shlib_grp.add_argument

      strip_grp = parser.add_argument_group (
         "strip", "remove code/comments",
      )
      strip_arg = strip_grp.add_argument

      dep_grp = parser.add_argument_group (
         "deptable/deptree options"
      )
      dep_arg = dep_grp.add_argument


      arg (
         '--version', '-V', action='version', version=self.version_str
      )

      arg (
         'modules',
         metavar = "module",
         nargs   = "*",
         help    = "shlib modules to process",
      )

      shlib_arg (
         '--shlib-dir', '-S',
         dest    = "shlib_dir",
         default = os.getcwd(),
         metavar = "<dir>",
         type    = is_fs_dir,
         help    = "shlib root directory",
      )

      shlib_arg (
         '--shell',
         default ='sh',
         choices = frozenset ( { 'sh', 'ash', 'bash' } ),
         dest    = "shell_format",
         help    = "shell interpreter that will be used, defaults to sh",
      )

      shlib_arg (
         '--bash',
         dest    = "shell_format",
         action  = "store_const",
         const   = "bash",
         help    = "prefer bash module files where available",
      )

      shlib_arg (
         '--sh',
         dest    = "shell_format",
         action  = "store_const",
         const   = "sh",
         help    = "compile for generic sh",
      )

      shlib_arg (
         '--ash',
         dest    = "shell_format",
         action  = "store_const",
         const   = "ash",
         help    = "compile for busybox\' ash",
      )

      output_arg (
         '--output', '-O',
         dest    = "output",
         default = '-',
         metavar = "<file>",
         type    = couldbe_output_file,
         help    = "output file, '-' for stdout",
      )

      output_arg (
         '--stdout', '-1',
         dest    = "output",
         action  = "store_const",
         const   = '-',
         help    = "write to stdout",
      )

      output_arg (
         '--main',
         dest    = "main_script",
         default = None,
         metavar = "<file>",
         type    = is_fs_file_or_none,
         help    = "script body (if any)",
      )

      output_arg (
         '--depfile', '-D',
         default    = None,
         const      = True,
         nargs      = "?",
         metavar    = "<file>",
         type       = is_fs_file_or_none,
         help       = '''
            file that lists extra dependencies or read the main script's deps
         '''
      )

      output_arg (
         '--exclude', '-x',
         dest    = "modules_exclude",
         default = argparse.SUPPRESS,
         action  = "append",
         help    = "module dependencies to ignore",
         metavar = "<module>",
      )

      output_arg (
         '--no-header',
         default = False,
         action  = "store_true",
         help    = "don\'t write the header"
      )

      output_arg (
         '--short-header',
         default = False,
         action  = "store_true",
         help    = 'write a minimal header',
      )

      output_arg (
         '--header-file', '-H',
         dest    = "header_file",
         default = None,
         metavar = "<file>",
         help    = "custom header file",
      )

      # doesn't do much currently
      #  (removes the "# your script starts here!" line)
      output_arg (
         '--as-lib', '-L',
         dest    = "is_lib",
         default = False,
         action  = "store_true",
         help    = "indicates that the result will be a library",
      )

      output_arg (
         '--allow-empty',
         dest    = "allow_empty",
         default = False,
         action  = "store_true",
         help    = "create output even if no modules given",
      )

      arg (
         '--no-sort',
         dest    = "no_sort",
         default = False,
         action  = "store_true",
         help    = "don\'t sort the modules (UNSAFE)",
      )

#      arg (
#         '--tabstospaces',
#         default = False,
#         action  = "store_true",
#         help    = "convert leading tabs to spaces (NOT IMPLEMENTED)",
#      )

#      arg (
#         '--tabsize',
#         default = 3,
#         metavar = "<int>",
#         help    = "tab size (set to <= 0 to disable entirely) (NOT IMPLEMENTED)",
#      )

      shlib_arg (
         '--max-depth',
         default = 7,
         metavar = "n",
         type    = int,
         help    = '''
            set maximum recursion depth to n when searching for module files
         ''',
      )

      arg (
         '--cat', '--piped',
         default = False,
         action  = "store_true",
         help    = "pass stdin to the output",
      )

      arg (
         '--debug', '--dbg',
         default = False,
         action  = "store_true",
         help    = "enable debug print statements",
      )

      action_arg (
         '--action',
         default = DEFAULT_ACTION,
         metavar = "<action>",
         choices = ACTIONS,
         help    = "choose from {}.".format ( ', '.join ( ACTIONS ) ),
      )

      for index, action in enumerate ( ACTIONS ):
         action_arg (
            '--' + action, '-s' + str ( index ),
            default = argparse.SUPPRESS,
            dest    = "action",
            action  = "store_const",
            const   = action,
            help    = "set action to {!r}".format ( action ),
         )
      # -- for

      strip_arg (
         '--strip-all', '--strip',
         dest    = "strip_all",
         default = False,
         action  = "store_true",
         help    = '''
            enable --strip-comments, --strip-virtual and --no-enclose-modules
         '''
      )

      strip_arg (
         '--strip-comments',
         default = False,
         action  = "store_true",
         help    = "remove all comments (EXPERIMENTAL)",
      )

      strip_arg (
         '--strip-virtual',
         default = False,
         action  = "store_true",
         help    = "remove module code that contains comments only",
      )

      strip_arg (
         '--keep-dev-comments',
         dest    = "strip_dev_comments",
         default = True,
         action  = "store_false",
         help    = "keep dev notes",
      )

      strip_arg (
         '--no-enclose-modules',
         dest    = "enclose_modules",
         default = True,
         action  = "store_false",
         help    = "don\'t print module begin/end lines",
      )

      dep_arg (
         '--depends', '-d',
         dest    = "restrict_depends",
         default = list(),
         action  = "append",
         help    = "only print modules that depend on <module>",
         metavar = "<module>",
      )

      return parser
   # --- end of get_parser (...) ---

   def _expand_modules ( self ):
      if self._argv_config.depfile is True:

         if self._argv_config.main_script:
            # "inlined" code copy from deptable.py's depfile_lookup()

            SUFFIX_DEPEND = ".depend"

            depfile = self._argv_config.main_script + SUFFIX_DEPEND

            if not os.path.isfile ( depfile ):
               depfile = (
                  os.path.splitext ( self._argv_config.main_script ) [0]
                  + SUFFIX_DEPEND
               )

               if not os.path.isfile ( depfile ):
                  return False
         else:
            self.parser.error ( "--depfile without an arg requires --main" )

      elif self._argv_config.depfile:
         depfile = self._argv_config.depfile
      else:
         return False

      with open ( depfile, 'rt' ) as FH:
         deps = [ l.strip() for l in FH.readlines() ]

      if deps:
         modules = list ( self._argv_config.modules )

         for dep in filter (
            lambda d : d and d [0] != '#',
            deps
         ):
            modules.append ( dep )

         self.modules = modules

   # --- end of _expand_modules (...) ---

   def __init__ ( self, actions, default_action ):
      assert default_action in actions
      self.version_str     = __version__
      self.parser          = self.get_parser ( actions, default_action )
      self.error           = self.parser.error
      self._argv_config    = self.parser.parse_args()
      self.use_bash        = self._argv_config.shell_format == 'bash'
      self.use_stdout      = self._argv_config.output == '-'

      if self.strip_all:
         self.strip_comments     = True
         self.strip_virtual      = True
         self.strip_dev_comments = True
         self.enclose_modules    = False
      # -- end if strip_all;

      self.modules_exclude = (
         frozenset ( self._argv_config.modules_exclude )
         if hasattr ( self._argv_config, 'modules_exclude' )
         else frozenset()
      )

      self._expand_modules()

      self.restrict_depends = frozenset ( self._argv_config.restrict_depends )

      if self.restrict_depends:
        if not self.modules:
           self.modules = [ '.', ]

      elif not self.modules and not self._argv_config.allow_empty:
         self.parser.error ( "no modules specified, try --allow-empty" )

      shlibcclib.message.DEBUG_PRINT = bool ( self._argv_config.debug )

      #del self.parser, self.error
   # --- end of __init__ (...) ---

   def __getattr__ ( self, key ):
      return getattr ( self._argv_config, key )
   # --- end of __getattr__ (...) ---

# --- end of ShlibccConfig ---

def main ( default_action ):
   """the main function

   arguments:
   * default_action -- the action that should be performed if not overridden
                       by command line args
   """
   ACTION_LINK     = 'link'
   ACTION_DEPTABLE = 'deptable'
   ACTION_DEPTREE  = 'deptree'
   ACTION_MODLIST  = 'list-modules'

   # parse args / create config
   config = ShlibccConfig (
      [ ACTION_MODLIST, ACTION_DEPTABLE, ACTION_DEPTREE, ACTION_LINK ],
      default_action
   )

   # deptable is always required
   deptable = shlibcclib.deptable.make_dependency_table (
      root     = config.shlib_dir,
      modules  = config.modules,
      config   = config,
   )


   if config.restrict_depends:

      print (
         '\n'.join (
            sorted (
               node.name for node in deptable
               if (
                  ( node.name != '.' )
                  and ( node.direct_deps & config.restrict_depends )
               )
            )
         )
         or "<none>"
      )

   elif config.action == ACTION_MODLIST:

      print (
         '\n'.join (
            sorted (
               deptable.names()
            )
         )
      )

   elif config.action == ACTION_DEPTABLE:

      print ( str ( deptable ) )

   elif config.action == ACTION_DEPTREE:

      deptree = shlibcclib.deptree.make_dependency_tree (
         config.modules, deptable
      )

      print ( str ( deptree ) )

   elif config.action == ACTION_LINK:

      if config.no_sort:
         shlibcclib.linker.link ( config, deptable )
      else:
         shlibcclib.linker.link (
            config,
            shlibcclib.deptree.make_dependency_tree ( config.modules, deptable )
         )

   else:
      raise Exception ( "unhandled action {!r}".format ( config.action ) )

# --- end of main (...) ---
