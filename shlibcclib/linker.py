# shlibcc -- linker
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'link', ]

import os.path
import sys

import shlibcclib.defaultheader
import shlibcclib.shlib

def link ( config, all_modules ):
   """Links the given modules into a single ("big") file.

   arguments:
   * config      -- configuration
   * all_modules -- modules that should be linked (an iterable)
   """

   use_stdout = config.use_stdout # ?

   shlib = shlibcclib.shlib.ShlibFile ( config=config, header=None )

   # add header, if any
   if config.no_header:
      pass
   elif config.header_file:
      with open ( config.header_file, 'rt' ) as HEADER_FH:
         shlib.header = (
            '# ' + '\n# '.join ( l.strip() for l in HEADER_FH )
         )
   else:
      shlib.header = shlibcclib.defaultheader.make ( config )
   # -- end if;

   if config.cat:
      shlib.pre_header = '\n'.join ( sys.stdin.readlines() )

   if config.defsym_file:
      with open ( config.defsym_file, 'rt' ) as DEFSYM_FH:
         shlib.defsym = ''.join ( DEFSYM_FH.readlines() )

   # write all modules
   for module in all_modules:
      if not os.path.isdir ( module.fspath ):
         shlib.add_module ( module.name, module.fspath )

   # write the script body, if any
   if config.main_script:
      shlib.add_module ( '__main__', config.main_script )
   elif not config.is_lib:
      shlib.footer = "# your script starts here!"

   if config.use_stdout:
      shlib.write ( sys.stdout )
   else:
      shlib.write ( config.output )

# --- end of link (...) ---
