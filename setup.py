#!/usr/bin/env python
# -*- coding: utf-8 -*-

import distutils.core

VERSION = '0.0.1'

distutils.core.setup (
	name         = 'R_Overlay',
	version      = VERSION,
	description  = 'shlib linker',
	author       = 'André Erdmann',
	author_email = 'dywi@mailerd.de',
	license      = 'GPL',
	#url          = '',
	packages     = (
      'shlibcclib',
	),
)
