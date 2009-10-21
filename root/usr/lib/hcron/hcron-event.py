#! /usr/bin/env python
#
# hcron-event.py

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

# system imports
import os
import subprocess
import sys

# app import
from hcron.constants import *
from hcron.event import signalReload

# constants
EDITOR = os.environ.get("EDITOR", "vi")

def printUsage(progName):
    print """\
usage: %s <path>
       %s [-h|--help]

Create/edit an hcron event definition at the given path (note: the
last component of the path is taken as the event name). An event
definition is stored in a text file in which each field and value
pair is set as name=value.""" % (progName, progName)

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1 or args[0] in [ "-h", "--help" ]:
        printUsage(PROG_NAME)
        sys.exit(0)

    try:
        path = args[0]
        if not os.path.exists(path):
            f = open(path, "w")
            f.write(HCRON_EVENT_DEFINITION)
            f.close()
        subprocess.call([ EDITOR, path ])

    except Exception, detail:
        print "Error: Problem creating event file."
        sys.exit(-1)

    try:
        if raw_input("Reload events (y/n)? ") in [ "y" ]:
            signalReload()
            print "Reload signalled for this machine (%s)." % HOST_NAME
        else:
            print "Reload deferred."

    except Exception, detail:
        print detail
        sys.exit(-1)

