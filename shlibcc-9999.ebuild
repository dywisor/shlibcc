# Copyright 1999-2013 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

EAPI=5

# python < 2.7 is not supported
PYTHON_COMPAT="python2_7 python3_1 python3_2"

inherit base python-distutils-ng git-2

EGIT_REPO_URI="git://git.erdmann.es/dywi/${PN}.git"

DESCRIPTION="shlib linker"
HOMEPAGE="http://git.erdmann.es/trac/dywi_${PN}"

LICENSE="GPL-2+"
SLOT="0"
IUSE="tools"

KEYWORDS=""

DEPEND=""
RDEPEND="${DEPEND:-}
	virtual/python-argparse
"

python_prepare_all() {
	base_src_prepare
}

python_install_all() {
	newbin "${PN}.py" "${PN}"
	if use tools; then
		local mode
		for mode in \
			'link' 'deplist' 'revdep' 'depgraph' 'deptable' 'list-modules'
		do
			newbin "${PN}.py" "${PN}-${mode}"
		done
	fi
}
