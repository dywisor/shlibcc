# Copyright 1999-2013 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

EAPI=5

PYTHON_COMPAT=( python{2_7,3_2,3_3} )
EGIT_REPO_URI="git://git.erdmann.es/dywi/${PN}.git"

inherit distutils-r1 git-r3

DESCRIPTION="shlib linker"
HOMEPAGE="http://git.erdmann.es/trac/dywi_${PN}"

LICENSE="GPL-2+"
SLOT="0"
IUSE="tools"

KEYWORDS=""

DEPEND=""
RDEPEND="${DEPEND-}
	virtual/python-argparse
"

python_install_all() {
	distutils-r1_python_install_all

	if use tools; then
		local mode
		for mode in \
			'link' 'deplist' 'revdep' 'depgraph' 'deptable' 'list-modules'
		do
			ln -s "${PN}" "${ED}/usr/bin/${PN}-${mode}" || die "ln<tools>"
		done
	fi
}
