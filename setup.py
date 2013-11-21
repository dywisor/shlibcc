#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import distutils.core

VERSION = '0.0.11'

MY_NAME  = 'André Erdmann'
MY_EMAIL = 'dywi@mailerd.de'

distutils.core.setup (
	name         = 'shlibcc',
	version      = VERSION,
	description  = 'shlib linker - (semi-)automatic generation of shell scripts',
	author       = MY_NAME,
	author_email = MY_EMAIL,
	license      = 'GPLv2+',
	#url          = '',
   scripts      = [ os.path.join ( 'bin', 'shlibcc' ), ] ,
	packages     = (
      'shlibcclib',
      'shlibcclib/generic',
	),
	classifiers = [
		'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
		'Development Status :: 3 - Alpha',
		'Environment :: Console',
	],
)
