# Copyright 1999-2013 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

EAPI=5

# python < 2.7 is not supported
PYTHON_COMPAT="python2_7 python3_1 python3_2"

inherit base python-distutils-ng git-2

EGIT_REPO_URI="http://git.erdmann.es/get/${PN}"

DESCRIPTION="shlib linker"
HOMEPAGE="http://git.erdmann.es/?p=shlibcc;a=blob_plain;f=README;hb=HEAD"

LICENSE="GPL-2"
SLOT="0"
IUSE=""

KEYWORDS=""

DEPEND=""
RDEPEND="${DEPEND:-}
	virtual/python-argparse
"

python_prepare_all() {
	base_src_prepare
}

python_install_all() {
	newbin ${PN}.py ${PN}
}
