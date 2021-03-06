# shlibcc -- default header for the shlib linker
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'make', ]

import time
import textwrap

#SHLIB_AUTHOR_NAME  = 'Andr\u00e9 Erdmann'
SHLIB_AUTHOR_NAME  = 'Andre Erdmann'
SHLIB_AUTHOR_EMAIL = 'dywi@mailerd.de'

ENCODING_COMMENT   = '# -*- coding: utf-8 -*-'

def make ( config, format_comment=None ):
   """Creates the default header for linked files."""

   #HEADER_DATE_FMT = "%Y-%m-%d %H:%M:%S (%Z)"
   HEADER_DATE_FMT = "%Y-%m-%d"

   if format_comment is None:
      comment_formatter = textwrap.TextWrapper(
         width              = 60,
         initial_indent     = '# ',
         subsequent_indent  = '# ',
         break_long_words   = False,
         #replace_whitespace = False,
      )
      fmt = comment_formatter.fill
   else:
      fmt = format_comment

   def centered_comment ( s, l=60, fillchar='-' ):
      if fillchar is not None:
         return '# ' + ( ' ' + str ( s ) + ' ' ).center ( l, fillchar )
      else:
         return '# ' + ( ' ' + str ( s ) + ' ' ).center ( l )
   # --- end of centered (...) ---

   gmtime     = time.gmtime()
   EMPTY_LINE = '#'

   shell_format = config.shell_format

   if shell_format == 'bash':
      shebang = '#!/bin/bash'
   elif shell_format == 'ash':
      shebang = '#!/bin/busybox ash'
   else:
      shebang = '#!/bin/sh'


   shell_opts = (
      "set -{}".format ( config.shell_opts ) if config.shell_opts else None
   )

   if config.short_header:
      return '\n'.join ( filter ( None, (
         shebang,
         shell_opts,
      )))

   else:
      return '\n'.join ( filter ( None, (
         shebang,
         ENCODING_COMMENT,
         EMPTY_LINE,
         fmt (
            'This file has been autogenerated by the '
            'shlib compiler version {ver} on {date}'.format (
               ver  = config.version_str,
               date = time.strftime(HEADER_DATE_FMT)
            ),
         ),
         EMPTY_LINE,
         centered_comment ( "shlib info" ),
         EMPTY_LINE,
         fmt (
            'shlib - shell function library'
         ),
         EMPTY_LINE,
         (
            "# *** comments have been stripped ***\n#"
            if config.strip_comments else None
         ),
         fmt (
            'Copyright (C) 2012-{year} {author} <{mail}>'.format (
               year   = gmtime.tm_year,
               author = SHLIB_AUTHOR_NAME,
               mail   = SHLIB_AUTHOR_EMAIL,
            ),
         ),
         fmt (
            'Distributed under the terms of the GNU General Public License; '
            'either version 2 of the License, or (at your option) '
            'any later version.'
         ),
         EMPTY_LINE,
         fmt (
            'Note: This is the "catch-all" license, certain modules may have '
            'their own (e.g. written by someone else).'
         ),
         EMPTY_LINE,
         centered_comment ( "end shlib info" ),
         EMPTY_LINE,
         shell_opts,
      )))
# --- end of make (...) ---
