# shlibcc -- helper functions for handling deps / dep files
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import collections
import os
from os.path import abspath, dirname, isfile, splitext


relpath_null_resolver = lambda x,k: x


def locate_depfile ( filename, basename=None, file_suffix='.depend' ):
   depfile = filename + file_suffix

   if isfile ( depfile ):
      return depfile
   else:
      depfile = (
         ( splitext ( filename )[0] if basename is None else basename )
         + file_suffix
      )
      if isfile ( depfile ):
         return depfile
      else:
         return None
# --- end of locate_depfile (...) ---

def _read_depfile ( depfile, relpath_resolve, dep_dict, blocker_dict ):
   with open ( depfile, 'rt' ) as FH:
      for line in FH.readlines():
         dep = line.strip()
         if dep and dep[0] != '#':
            if dep[0] != '!':
               dep_dict [relpath_resolve(dep, depfile)] = None
            else:
               blocked = dep[1:].lstrip()
               if not blocked:
                  pass
               elif blocked[0] == '!':
                  raise Exception (
                     "invalid blocker entry {!r} in depfile {!r}".format (
                        dep, depfile
                     )
                  )
               else:
                  blocker_dict [relpath_resolve(blocked, depfile)] = None
      # -- end for <line>
   # -- end with <FH>
# --- end of _read_depfile (...) ---

def read_depfiles ( depfiles, relpath_resolver=None ):
   blockers_d = collections.OrderedDict()
   deps_d     = collections.OrderedDict()
   unrel      = (
      relpath_null_resolver if relpath_resolver is None else relpath_resolver
   )

   for depfile in depfiles:
      _read_depfile ( depfile, unrel, deps_d, blockers_d )

   return ( list ( deps_d.keys() ), list ( blockers_d.keys() ) )
# --- end of read_depfiles (...) ---

def read_depfile ( depfile, relpath_resolver=None ):
   blockers_d = collections.OrderedDict()
   deps_d     = collections.OrderedDict()
   unrel      = (
      relpath_null_resolver if relpath_resolver is None else relpath_resolver
   )

   _read_depfile ( depfile, unrel, deps_d, blockers_d )

   return ( list ( deps_d.keys() ), list ( blockers_d.keys() ) )
# --- end of read_depfile (...) ---

def get_relpath_resolver ( shlib_dir_parent ):
   def resolve_dep_relpath ( relpath, depfile ):
      # lazy implementation
      if relpath[:2] == '.' + os.sep or relpath[:3] == '..' + os.sep:
         path = abspath ( os.path.join ( dirname ( depfile ), relpath ) )

      elif relpath [0] == os.sep:
         #assert len ( path ) > 1
         if relpath[1] == os.sep:
            path = abspath ( relpath )
         else:
            path = abspath (
               os.path.join ( shlib_dir_parent, relpath.lstrip ( os.sep ) )
            )
      else:
         return relpath

      if os.path.isdir ( path ):
         raise Exception (
            "direct depfile imports must be files, not directories."
         )
      else:
         return path
   # --- end of resolve_dep_relpath (...) ---

   return resolve_dep_relpath
# --- end of get_relpath_resolver (...) ---
