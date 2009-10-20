#
# SConstruct DIST=<dist> ARCH=<arch>
#

import os

UNAME_SYSNAME, UNAME_NODENAME, UNAME_RELEASE, UNAME_VERSION, UNAME_MACHINE = os.uname()

DEBIAN = 0
RPM = 0

if  "DIST" in ARGUMENTS and "ARCH" in ARGUMENTS:
    DIST = ARGUMENTS["DIST"]
    ARCH = ARGUMENTS["ARCH"]
else:
    print "Require DIST and ARCH keyword settings."
    Exit(-1)

if DIST == "jaunty":
    DEBIAN = 1
    PLATFORM = "%s-%s" % (DIST, ARCH)
    DEBIAN_CONTROL_ARCHITECTURE = "Architecture: %s" % ARCH
    DEBIAN_CONTROL_DEPENDS = "Depends: python (>=2.4)"

elif DIST == "etch":
    DEBIAN = 1
    PLATFORM = "%s-%s" % (DIST, ARCH)
    DEBIAN_CONTROL_ARCHITECTURE = "Architecture: %s" % ARCH
    DEBIAN_CONTROL_DEPENDS = "Depends: python (>=2.4)"

if DEBIAN:
    Export("ARCH",
        "DIST",
        "PLATFORM",
        "DEBIAN_CONTROL_ARCHITECTURE",
        "DEBIAN_CONTROL_DEPENDS")

    SConscript("SConscript.general")
    SConscript("SConscript.debian")

else:
    print "Error: DIST (%s) and ARCH (%s) not supported." % (DIST, ARCH)
    Exit(-1)

