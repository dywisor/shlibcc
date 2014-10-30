# shlibcc -- main() and config
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'ShlibccConfig', 'main', ]

import os
import sys
import argparse
import collections

import shlibcclib.deptable
import shlibcclib.library
import shlibcclib.depgraph
import shlibcclib.deputil
import shlibcclib.linker
import shlibcclib.message
import shlibcclib.shlib

version     = ( 0, 0, 14 )
__version__ = '.'.join ( str ( a ) for a in version )

DEFAULT_SHLIB_DIR = None


class BlockerAction ( object ):

   ACTION_IGNORE        =  1
   ACTION_EXCLUDE       =  2
   ACTION_ERROR         =  4
   ACTION_EXCLUDE_QUIET =  8
   ACTION_WARN          = 32

   ACTIONS  = {
      'ignore'        : ACTION_IGNORE,
      'exclude'       : ACTION_EXCLUDE,
      'error'         : ACTION_ERROR,
      'err'           : ACTION_ERROR,
      'fail'          : ACTION_ERROR,
      'exclude-quiet' : ACTION_EXCLUDE_QUIET,
      'warn'          : ACTION_WARN,
   }

   @classmethod
   def get_keys ( cls ):
      return list ( cls.ACTIONS.keys() )

   @classmethod
   def from_str ( cls, s ):
      return cls ( cls.ACTIONS[s], key=s )

   def __init__ ( self, value, key=None ):
      super ( BlockerAction, self ).__init__()
      assert key is None or key in self.__class__.ACTIONS
      self.key   = key
      self.value = value

   def __eq__ ( self, other ):
      return self.value == other

   def __ne__ ( self, other ):
      return self.value != other

   def __str__ ( self ):
      if self.key is not None:
         return str ( self.key )
      else:
         value = self.value
         if value == self.ACTION_IGNORE:
            return "ignore"
         elif value == self.ACTION_EXCLUDE:
            return "exclude"
         elif value == self.ACTION_ERROR:
            return "error"
         elif value == self.ACTION_EXCLUDE_QUIET:
            return "exclude-quiet"
         elif value == self.ACTION_WARN:
            return "warn"
         else:
            return "UNDEF"
   # --- end of __str__ (...) ---

# --- end of BlockerAction ---


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

      def is_blocker_action ( v ):
         if v and v in BlockerAction.ACTIONS:
            return BlockerAction.from_str ( v )
         else:
            raise argparse.ArgumentTypeError (
               "{!r} is not a blocker action".format ( v )
            )
      # --- end of is_blocker_action (...) ---

      def is_module_section_restriction ( v ):
         if v is None:
            return None
         if not v:
            return set()
         else:
            get_section_name = shlibcclib.shlib.ShlibModule.get_section_name
            whitelist = set()
            blacklist = set()
            add_section = None

            for vname in v.split ( ',' ):
               if vname:
                  if vname[0] in "!^-":
                     name        = vname[1:]
                     add_section = blacklist.add
                  else:
                     name        = vname
                     add_section = whitelist.add

                  try:
                     section = get_section_name ( name )
                  except shlibcclib.shlib.ShlibModuleSyntaxError:
                     raise argparse.ArgumentTypeError (
                        "{!r} is not a known module section".format ( vname )
                     )
                  else:
                     add_section ( section )
            # -- end for

            if blacklist:
               _whitelist = (
                  whitelist or  shlibcclib.shlib.ShlibModule.SECTIONS
               )
               return set (( k for k in _whitelist if k not in blacklist ))
            else:
               return whitelist
      # --- end of is_module_section_restriction (...) ---

      blocker_choices       = ', '.join ( BlockerAction.get_keys() )
      optional_code_choices = ( "comment", "c", "no", "n", "y", "yes" )

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
         default = DEFAULT_SHLIB_DIR or os.getcwd(),
         metavar = "<dir>",
         type    = is_fs_dir,
         help    = "shlib root directory",
      )

      shlib_arg (
         '--shlib-include-dir', '-I',
         dest    = "shlib_include_dirs",
         action  = 'append',
         default = [],
         metavar = "<dir>",
         type    = is_fs_dir,
         help    = "additional shlib root directories",
      )

      shlib_arg (
         '--dropin',
         dest    = "dropin_modules",
         action  = 'store_true',
         default = False,
         # default behavior is downward search
         help    = "always search modules in all libraries"
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

      shlib_arg (
         '--blocker',
         dest    = "blocker_action",
         default = BlockerAction.from_str ( "error" ),
         metavar = '<action>',
         type    = is_blocker_action,
         help    = (
            'action that will be taken when a directory with a blocker '
            'file should be included (choose from '
            + blocker_choices + ') [%(default)s]'
         )
      )

      shlib_arg (
         '--depfile-blocker', '--main-blocker',
         dest    = 'depfile_blocker_strategy',
         default = BlockerAction.from_str ( "exclude" ),
         metavar = '<action>',
         type    = is_blocker_action,
         help    = (
            'control how --depfile blockers are handled '
            '(choose from ' + blocker_choices + ') [%(default)s]'
         )
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
         action     = 'append',
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
         '--extract-sections', '-X',
         dest    = 'restrict_sections',
         metavar = '<section,...>',
         default = None,
         type    = is_module_section_restriction,
         help    = 'comma-separated list of sections to extract',
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

      output_arg (
         '--defsym', '--code-inject',
         dest    = "defsym_file",
         default = None,
         metavar = "<file>",
         type    = is_fs_file_or_none,
         help    = "file that will included directly after the header (e.g. for variables)",
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

      output_arg (
         '--shell-opts',
         dest    = "shell_opts",
         default = None,
         metavar = "<options>",
         help    = '''
            add a \'set -<options>\' statement to the default header
         '''
      )

      output_arg (
         '-u',
         dest   = "shell_opts",
         default = None,
         action = "store_const",
         const  = "u",
         help   = "same as --shell-opts u",
      )

      output_arg (
         '--keep-safety-checks',
         dest    = 'keep_safety_checks',
         default = 'comment',
         nargs   = '?',
         choices = optional_code_choices,
         const   = 'yes',
         metavar = '<y|c|n>',
         help    = (
            "whether to keep @safety_checks as code(y), comment(c) or not(n)"
         )
      )

      output_arg (
         '--enable-debug-code',
         dest    = 'enable_debug_code',
         default = 'no',
         nargs   = '?',
         choices = optional_code_choices,
         const   = 'yes',
         metavar = '<y|c<n>',
         help    = (
            "whether to keep @debug commands as code(y), comment(c) or not(n)"
         )
      )

      arg (
         '--no-sort',
         dest    = "no_sort",
         default = False,
         action  = "store_true",
         help    = "don\'t sort the modules (UNSAFE)",
      )

      arg (
         '--stable-sort',
         dest    = "stable_sort",
         default = True,
         action  = "store_true",
         help    = "use stable sorting",
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
         '--strip-main',
         dest    = "strip_main",
         default = False,
         action  = "store_true",
         help    = "also strip --main file",
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
         default = argparse.SUPPRESS,
         action  = "store_false",
         help    = "don\'t print module begin/end lines (default if not a lib)",
      )

      strip_arg (
         '--enclose-modules',
         dest    = "enclose_modules",
         default = argparse.SUPPRESS,
         action  = "store_true",
         help    = '''
            print module begin/end lines
            (default if a library or no --main given)
         '''
      )

      strip_arg (
         '--no-enclose-sections',
         dest    = "enclose_sections",
         default = argparse.SUPPRESS,
         action  = "store_false",
         help    = "don\'t print section begin/end lines"
      )

      strip_arg (
         '--enclose-sections',
         dest    = "enclose_sections",
         default = argparse.SUPPRESS,
         action  = "store_true",
         help    = "print section begin/end lines"
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

      def lookup_main_depfile():
         main_script = self._argv_config.main_script

         if main_script:
            depfile = shlibcclib.deputil.locate_depfile ( main_script )
            if depfile:
               return depfile
            else:
               self.parser.error ( "--depfile for --main not found." )
         else:
            self.parser.error ( "--depfile without an arg requires --main" )
      # --- end of lookup_main_depfile (...) ---

      if self._argv_config.depfile:
         unique_depfiles = collections.OrderedDict.fromkeys (
            (
               lookup_main_depfile() if depf is True else depf
                  for depf in self._argv_config.depfile
            )
         )
         depfiles = list ( unique_depfiles.keys() )
         del unique_depfiles

         modules, blockers = shlibcclib.deputil.read_depfiles (
            depfiles,
            shlibcclib.deputil.get_relpath_resolver ( self.shlib_dir )
         )

         blocker_action = self._argv_config.depfile_blocker_strategy

         if blockers:
            blockers_str = ', '.join ( str(s) for s in blockers )

            if blocker_action == blocker_action.ACTION_IGNORE:
               sys.stderr.write (
                  "ignoring dep blockers: {}\n".format ( blockers_str )
               )

            elif blocker_action == blocker_action.ACTION_EXCLUDE_QUIET:
               self.modules_exclude.update ( blockers )

            elif blocker_action == blocker_action.ACTION_EXCLUDE:
               sys.stderr.write (
                  "adding dep blockers to exclude list: {}\n".format (
                     blockers_str
                  )
               )
               self.modules_exclude.update ( blockers )

            elif blocker_action == blocker_action.ACTION_WARN:
               sys.stderr.write (
                  "adding dep blockers to blocker list: {}\n".format (
                     blockers_str
                  )
               )
               self.module_blockers = blockers

            else:
               self.module_blockers = blockers
         # -- end if <blockers>

         if self._argv_config.modules:
            self.modules = self._argv_config.modules + modules
         else:
            self.modules = modules

         return True
      else:
         return False
   # --- end of _expand_modules (...) ---

   def __init__ ( self, actions, default_action ):
      super ( ShlibccConfig, self ).__init__()
      assert default_action in actions
      self.version_str     = __version__
      self.module_blockers = None
      self.parser          = self.get_parser ( actions, default_action )
      self.die             = self.parser.exit
      self.error           = self.parser.error
      self._argv_config    = self.parser.parse_args()
      self.use_bash        = self._argv_config.shell_format == 'bash'
      self.use_stdout      = self._argv_config.output == '-'
      self.shlib_path      = (
         [ self.shlib_dir ] + list ( reversed ( self.shlib_include_dirs ) )
      )

      if self._argv_config.shell_opts:
         self.shell_opts = self._argv_config.shell_opts.lstrip ( '-' )

      for attr_name in { 'keep_safety_checks', 'enable_debug_code' }:
         attr = getattr ( self._argv_config, attr_name )
         if attr in { 'y', 'yes' }:
            attr = 'y'
         elif attr in { 'c', 'comment' }:
            attr = 'c'
         elif attr in { 'n', 'no' }:
            attr = 'n'
         else:
            raise AssertionError (
               "unknown {!s} value {!r}".format ( attr_name, attr )
            )
         setattr ( self, attr_name, attr )
         # -- end if <attr>
      # -- end for <attr_name>

      if self._argv_config.strip_all:
         self.strip_comments     = True
         self.strip_virtual      = True
         self.strip_dev_comments = True
         self.enclose_modules    = False
      else:
         if not hasattr ( self._argv_config, 'enclose_modules' ):
            self.enclose_modules = bool (
               self._argv_config.is_lib or not self._argv_config.main_script
            )
      # -- end if strip_all;

      if not hasattr ( self._argv_config, 'enclose_sections' ):
         self.enclose_sections = bool ( self.restrict_sections is not None )

      self.modules_exclude = (
         set ( self._argv_config.modules_exclude )
         if hasattr ( self._argv_config, 'modules_exclude' )
         else set()
      )
      self._expand_modules()
      self.modules_exclude  = frozenset ( self.modules_exclude )
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
      if key != '_argv_config':
         return getattr ( self._argv_config, key )
      else:
         raise AttributeError ( key )
   # --- end of __getattr__ (...) ---

# --- end of ShlibccConfig ---

def main ( default_action ):
   """the main function

   arguments:
   * default_action -- the action that should be performed if not overridden
                       by command line args
   """
   ACTION_LINK             = 'link'
   ACTION_DEPTABLE         = 'deptable'
   ACTION_DEPGRAPH         = 'depgraph'
   ACTION_DEPGRAPH_REVERSE = 'revdep'
   ACTION_DEPLIST          = 'deplist'
   ACTION_MODLIST          = 'list-modules'

   # parse args / create config
   config = ShlibccConfig (
      [
         ACTION_MODLIST, ACTION_DEPTABLE, ACTION_DEPGRAPH,
         ACTION_DEPGRAPH_REVERSE, ACTION_DEPLIST, ACTION_LINK
      ],
      default_action
   )

   # deptable is always required
   deptable = shlibcclib.library.make_dependency_table (
      rootdirs = config.shlib_path,
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

   elif config.action == ACTION_DEPGRAPH:

      depgraph = shlibcclib.depgraph.DependencyGraph ( deptable )

      print ( depgraph.visualize_edges() )

   elif config.action == ACTION_DEPGRAPH_REVERSE:

      depgraph = shlibcclib.depgraph.DependencyGraph ( deptable )

      print ( depgraph.visualize_edges ( reverse=True ) )

   elif config.action == ACTION_DEPLIST:

      deplist = shlibcclib.depgraph.DependencyList (
         deptable, config.stable_sort
      )

      print ( str ( deplist ) )

   elif config.action == ACTION_LINK:

      if config.no_sort:
         shlibcclib.linker.link ( config, deptable )
      else:
         shlibcclib.linker.link (
            config,
            shlibcclib.depgraph.DependencyList ( deptable, config.stable_sort )
         )

   else:
      raise Exception ( "unhandled action {!r}".format ( config.action ) )

# --- end of main (...) ---
