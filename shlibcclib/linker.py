# shlibcc -- linker
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'link', ]

import collections
import os
import re
import sys

import shlibcclib.defaultheader


#RE_SHEBANG            = re.compile ( '^\#\!\s*/\S+/\S*sh($|\s+)' )
RE_INCLUDE_PROTECTION = re.compile (
   '^\s*if\s+\[{1,2}\s+\-z\s+..*__HAVE_..*__.*\s+\]{1,2}'
)

def link ( config, all_modules ):
   """Links the given modules into a single ("big") file.

   arguments:
   * config      -- configuration
   * all_modules -- modules that should be linked (an iterable)
   """

   use_stdout      = config.use_stdout
   write_immediate = config.write_immediate

   # open/set FH
   #  _not_ checking "if FH", this could have side effects
   if use_stdout:
      IMMEDIATE_FH = sys.stdout
   elif write_immediate:
      IMMEDIATE_FH = open ( config.output, 'wt' )
   else:
      IMMEDIATE_FH = None
      # blobs will be used to store the text blocks
      blobs        = list()
   # -- end if;

   def write_str ( text ):
      """Writes the given string (or stores it for writing it later)."""
      if write_immediate:
         IMMEDIATE_FH.write ( text )
      else:
         blobs.append ( text )
   # --- end of write_str (...) ---

   def write_text ( text ):
      """Like write_str(), but appends a newline char."""
      if write_immediate:
         IMMEDIATE_FH.write ( text )
         IMMEDIATE_FH.write ( '\n' )
      else:
         blobs.append ( text )
         blobs.append ( '\n' )
   # --- end of write (...) ---

   def write_module ( name, fspath ):
      """Writes a module.

      arguments:
      * name   -- name of the module
      * fspath -- path to the module file
      """
      if os.path.isdir ( fspath ):
         return

      with open ( fspath, 'rt' ) as FH:
         lines = collections.deque (
            l.rstrip() for l in FH.readlines()
         )


      # preparse:

      def discard_lines():
         while lines and not lines [0]:
            lines.popleft()
      # --- end of discard_lines (...) ---

      def discard_end_lines():
         while lines and not lines [-1]:
            lines.pop()
      # --- end of discard_end_lines (...) ---

      # -> (1) discard empty lines
      discard_lines()
      discard_end_lines()


      if not lines:
         return
#      elif RE_SHEBANG.match ( lines [0] ):
      elif len ( lines [0] ) > 2 and lines [0][:2] == '#!':
         lines.popleft()
         discard_lines()
         if not lines:
            return

      # remove if __HAVE__
      #  (could raise an IndexError here)
      if RE_INCLUDE_PROTECTION.match ( lines [0] ) and \
         lines [1][:9]  == 'readonly ' and \
         lines [-1][:2] == 'fi' \
      :
         lines.popleft()
         lines.popleft()
         lines.pop()

         discard_lines()
         discard_end_lines()

         if not lines:
            return

      # write the module
      write_str (
         "\n### begin module {} ###\n\n".format ( name )
      )
      write_text (
         '\n'.join ( lines )
      )
      write_str (
         "\n### end module {} ###\n".format ( name )
      )
   # --- end of write_module (...) ---

   # write the header, if any
   if config.no_header:
      header = None
   elif config.header_file:
      with open ( config.header_file, 'rt' ) as HEADER_FH:
         write_text (
            '# ' + '\n# '.join (
               l.strip() for l in HEADER_FH
            )
         )
   else:
      write_text ( shlibcclib.defaultheader.make ( config ) )
   # -- end if;

   # write all modules
   for module in all_modules:
      write_module ( module.name, module.fspath )

   # write the script body, if any
   if config.main_script:
      write_module ( '__main__', config.main_script )
   else:
      write_str (
         "\n# your script starts here!\n\n"
      )

   # finalize / writeout
   if use_stdout:
      pass
   elif IMMEDIATE_FH:
      IMMEDIATE_FH.close()
   else:
      with open ( config.output, 'wt' ) as FH:
         for blob in blobs:
            FH.write ( blob )
# --- end of do_compile (...) ---
