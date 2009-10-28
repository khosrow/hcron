#! /usr/bin/env python
#
# hcron-info.py

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

"""Provide hcron related information.
Simply print the fully qualified host name of the executing machine.
"""

# system imports
import os
import os.path
import pwd
import socket
import sys

# hcron imports
from hcron.constants import *

# constants
PROG_NAME = os.path.basename(sys.argv[0])

def printUsage(PROG_NAME):
    print """\
usage: %s --allowed
       %s -es
       %s --fqdn

Print hcron related information.

Where:
--allowed           output "yes" if permitted to use hcron
-es                 event statuses
--fqdn              fully qualified hostname""" % (PROG_NAME, PROG_NAME, PROG_NAME)

def printAllowed():
    try:
        userName = pwd.getpwuid(os.getuid()).pw_name
        userEventListsPath = "%s/%s" % (HCRON_EVENT_LISTS_DUMP_DIR, userName)

        if os.path.exists(userEventListsPath):
            print "yes"

    except Exception, detail:
        pass

def printFqdn():
    try:
        print socket.getfqdn()
    except Exception, detail:
        print "Error: Could not determine the fully qualified host name."

def printUserEventStatus():
    try:
        userName = pwd.getpwuid(os.getuid()).pw_name
        userEventListsPath = "%s/%s" % (HCRON_EVENT_LISTS_DUMP_DIR, userName)

        print open(userEventListsPath, "r").read()
    except Exception, detail:
        print "Error: Could not read event status information."

if __name__ == "__main__":
    args = sys.argv[1:]

    if len(args) == 0:
        printUsage(PROG_NAME)
        sys.exit(-1)

    while args:
        arg = args.pop(0)

        if arg in [ "--allowed" ]:
            printAllowed()
            break

        if arg in [ "-es" ]:
            printUserEventStatus()
            break

        elif arg in [ "--fqdn" ]:
            printFqdn()
            break


        elif arg in [ "-h", "--help" ]:
            printUsage(PROG_NAME)
            break
        
        else:
            printUsage(PROG_NAME)
            sys.exit(-1)
