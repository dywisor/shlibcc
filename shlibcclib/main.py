# shlibcc -- shlib module linker, config
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'ShlibccConfig', 'main', ]

import os
import argparse

import shlibcclib.deptable
import shlibcclib.deptree
import shlibcclib.linker

version     = ( 0, 0, 1 )
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

      arg (
         '--version', '-V', action='version', version=self.version_str
      )

      arg (
         'modules',
         nargs = "+",
         help  = "shlib modules to process",
      )

      arg (
         '--shell',
         default ='sh',
         choices = frozenset ( { 'sh', 'ash', 'bash' } ),
         dest    = "shell_format",
         help    = "output format",
      )

      arg (
         '--bash',
         dest    = "shell_format",
         action  = "store_const",
         const   = "bash",
         help    = "compile for bash",
      )

      arg (
         '--sh',
         dest    = "shell_format",
         action  = "store_const",
         const   = "sh",
         help    = "compile for generic sh",
      )

      arg (
         '--shlib-dir', '-S',
         dest    = "shlib_dir",
         default = os.getcwd(),
         metavar = "<dir>",
         type    = is_fs_dir,
         help    = "shlib root directory",
      )

      arg (
         '--output', '-O',
         dest    = "output",
         default = '-',
         metavar = "<file>",
         type    = couldbe_output_file,
         help    = "output file, '-' for stdout",
      )

      arg (
         '--stdout', '-1',
         dest    = "output",
         action  = "store_const",
         const   = '-',
         help    = "write to stdout",
      )

      arg (
         '--main',
         dest    = "main_script",
         default = None,
         metavar = "<file>",
         help    = "script body (if any)",
      )

      arg (
         '--no-header',
         default = False,
         action  = "store_true",
         help    = "don\'t write the header"
      )

      arg (
         '--header-file', '-H',
         dest    = "header_file",
         default = None,
         metavar = "<file>",
         help    = "custom header file",
      )

      arg (
         '--no-sort',
         dest    = "no_sort",
         default = False,
         action  = "store_true",
         help    = "don\'t sort the output",
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

      arg (
         '--write-immediate',
         default = False,
         action  = "store_true",
         help    = 'write partial results as soon as they\'re ready',
      )

      arg (
         '--max-depth',
         default = 7,
         metavar = "n",
         type    = int,
         help    = '''
            set maximum recursion depth to n when searching for module files
         ''',
      )


      arg (
         '--action',
         default = DEFAULT_ACTION,
         metavar = "<action>",
         choices = ACTIONS,
         help    = "choose from {}.".format ( ', '.join ( ACTIONS ) ),
      )

      for action in ACTIONS:
         arg (
            '--' + action,
            default = argparse.SUPPRESS,
            dest    = "action",
            action  = "store_const",
            const   = action,
            help    = "set action to {!r}".format ( action ),
         )
      # -- for

      return parser
   # --- end of get_parser (...) ---


   def __init__ ( self, actions, default_action ):
      assert default_action in actions
      self.version_str     = __version__
      parser               = self.get_parser ( actions, default_action )
      self._argv_config    = parser.parse_args()
      self.use_bash        = self._argv_config.shell_format == 'bash'
      self.use_stdout      = self._argv_config.output == '-'
      self.write_immediate = (
         self.use_stdout or self._argv_config.write_immediate
      )

   def __getattr__ ( self, key ):
      return getattr ( self._argv_config, key )

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

   # parse args / create config
   config = ShlibccConfig (
      [ ACTION_LINK, ACTION_DEPTABLE, ACTION_DEPTREE ],
      default_action
   )

   # deptable is always required
   deptable = shlibcclib.deptable.make_dependency_table (
      root     = config.shlib_dir,
      modules  = config.modules,
      config   = config,
   )

   if config.action == ACTION_DEPTABLE:

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
