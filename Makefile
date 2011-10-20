#
# Makefile
#

# this can only be done in the first Makefile
HERE_FILE:="$(CURDIR)/$(strip $(MAKEFILE_LIST))"
HERE_DIR:=$(shell dirname $(HERE_FILE))

STATIC_DIR=$(HERE_DIR)/static

none:

install:
	if test "${INSTALL_DIR}" = ""; then echo "error: INSTALL_DIR not defined"; exit 1; fi
	if test -e ${INSTALL_DIR}; then rm -rf ${INSTALL_DIR}; fi
	:
	mkdir -p ${INSTALL_DIR}
	mkdir -p ${INSTALL_DIR}/usr/bin
	:
	(cd ${STATIC_DIR}; tar cf - etc/*) | (cd ${INSTALL_DIR}; tar xvf -)
	(cd ${STATIC_DIR}; tar cf - usr/bin/*) | (cd ${INSTALL_DIR}; tar xvf -)
	(cd ${STATIC_DIR}; tar cf - usr/lib/hcron/*) | (cd ${INSTALL_DIR}; tar xvf -)
	(cd ${STATIC_DIR}; tar cf - usr/share/*) | (cd ${INSTALL_DIR}; tar xvf -)
	(cd ${STATIC_DIR}; tar cf - var/*) | (cd ${INSTALL_DIR}; tar xvf -)
