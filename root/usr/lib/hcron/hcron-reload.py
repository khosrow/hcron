#! /usr/bin/env python
#
# hcron-reload.py

# GPL--start
# This file is part of hcron
# Copyright (C) 2008, 2009 Environment/Environnement Canada
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
# GPL--end

"""Signal to the hcron-scheduler to reload a user's event
definition files.
"""

# system imports
import os
import os.path
import pwd
import sys
import tempfile

# app imports
from hcron.constants import *
import hcron.globals as globals
from hcron.file import AllowedUsersFile, ConfigFile

def printUsage(progName):
    print """\
usage: %s

Signal to the hcron-scheduler running of the local machine to reload
one's event defintion files.""" % progName

if __name__ == "__main__":
    progName = os.path.basename(sys.argv[0])

    #
    # parse command line
    #
    args = sys.argv[1:]
    if len(args) > 0:
        if args[0] in [ "-h", "--help" ]:
            printUsage(progName)
            sys.exit(0)
        else:
            printUsage(progName)
            sys.exit(-1)

    #
    # setup
    #
    globals.config = ConfigFile(HCRON_CONFIG_PATH)
    globals.allowedUsers = AllowedUsersFile(HCRON_ALLOW_PATH)
    config = globals.config.get()
    signalHome = config.get("signalHome") or HCRON_SIGNAL_HOME

    try:
        userName = pwd.getpwuid(os.getuid()).pw_name
        if userName not in globals.allowedUsers.get():
            print "Warning: You are not an allowed hcron user."
            sys.exit(-1)
        tempfile.mkstemp(prefix=userName, dir=signalHome)
        print "Reload signalled for this machine (%s)." % HOST_NAME
    except Exception, detail:
        print "Error: Could not signal for reload."
        sys.exit(-1)
    sys.exit(0)
