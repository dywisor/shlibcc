#!/usr/bin/python
# -*- coding: utf-8 -*-
# shlibcc -- multicall script - shlibcc{,-link,-deptree,-deptable}
#
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

if __name__ == '__main__':

   import os.path
   import sys

   import shlibcclib.main

   script_name = os.path.basename ( sys.argv [0] )

   script_mode = 'link'
   if script_name != 'shlibcc':
      for mode in { 'link', 'deptree', 'deptable' }:
         if script_name.endswith ( mode ):
            script_mode = mode
            break

   shlibcclib.main.main ( script_mode )
