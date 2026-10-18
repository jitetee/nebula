# Recipe for the Termux package build system.
# Use it to submit Nebula to:
#   • Termux User Repository (TUR):  https://github.com/termux-user-repository/tur
#   • the official repo:             https://github.com/termux/termux-packages
# Copy this folder to  packages/nebula/  in a fork, fill in the checksum, open a pull request.
#
# Get the checksum after you push the tag v$TERMUX_PKG_VERSION:
#   curl -fsSL https://github.com/jitetee/nebula/archive/refs/tags/v0.9.0.tar.gz | sha256sum

TERMUX_PKG_HOMEPAGE=https://github.com/jitetee/nebula
TERMUX_PKG_DESCRIPTION="AI-powered terminal helper and shell UI for Termux"
TERMUX_PKG_LICENSE="MIT"
TERMUX_PKG_MAINTAINER="@jitetee"
TERMUX_PKG_VERSION=0.9.0
TERMUX_PKG_SRCURL=https://github.com/jitetee/nebula/archive/refs/tags/v${TERMUX_PKG_VERSION}.tar.gz
TERMUX_PKG_SHA256=REPLACE_WITH_SHA256_OF_THE_TARBALL
TERMUX_PKG_DEPENDS="bash, zsh, curl, tar, gawk, jq, ncurses-utils, coreutils, findutils, grep, sed"
TERMUX_PKG_RECOMMENDS="tgpt, termux-api, openssl-tool"
TERMUX_PKG_PLATFORM_INDEPENDENT=true
TERMUX_PKG_BUILD_IN_SRC=true

termux_step_make() {
	: # nothing to compile — it's shell scripts
}

termux_step_make_install() {
	local app="$TERMUX_PREFIX/opt/nebula"
	mkdir -p "$app" "$TERMUX_PREFIX/bin"
	cp -r bin lib zsh motd assets install docs VERSION LICENSE "$app/"
	chmod 755 "$app/bin/nebula" "$app"/lib/*.sh "$app"/install/*.sh "$app/motd/init.sh" "$app"/motd/motd.d/*
	ln -sf ../opt/nebula/bin/nebula "$TERMUX_PREFIX/bin/nebula"
}

termux_step_create_debscripts() {
	cat <<-EOF >./postinst
		#!$TERMUX_PREFIX/bin/sh
		mkdir -p "$TERMUX_PREFIX/opt/nebula/data"
		chmod 700 "$TERMUX_PREFIX/opt/nebula" "$TERMUX_PREFIX/opt/nebula/data" 2>/dev/null || true
		echo ""
		echo "  ⚡ Nebula installed. Finish setup with:  nebula setup"
		echo ""
	EOF
}
