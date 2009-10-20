#! /usr/bin/env python
#
# hcron-scheduler.py

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

"""This is the backend event scheduler. It is typically run by root
although it can be run by individual users, but with reduced
functionality (i.e., it only handlers the user's own events).
"""

# secure by restricting sys.path to /usr and first path entry
import sys
firstPath = sys.path[0]
sys.path = [ path for path in sys.path if path.startswith("/usr") ]
sys.path.insert(0, firstPath)
del firstPath

# system imports
import os.path
import pprint
import signal

# app imports
from hcron.constants import *
import hcron.globals as globals
from hcron.event import EventListList
from hcron.file import AllowedUsersFile, ConfigFile, PidFile, SignalHome
from hcron.logger import *
from hcron.server import Server

def dumpSignalHandler(num, frame):
    logMessage("info", "Received signal to dump.")
    signal.signal(num, dumpSignalHandler)
    pp = pprint.PrettyPrinter(indent=4)

    try:
        config = globals.config.get()
        f = open(HCRON_CONFIG_DUMP_PATH, "w+")
        f.write(pp.pformat(config))
        f.close()
    except Exception, detail:
        if f != None:
            f.close()

    try:
        allowedUsers = globals.allowedUsers.get()
        f = open(HCRON_ALLOWED_USERS_DUMP_PATH, "w+")
        f.write("\n".join(allowedUsers))
        f.close()
    except Exception, detail:
        if f != None:
            f.close()

    try:
        ell = globals.eventListList
        f = open(HCRON_EVENTS_DUMP_PATH, "w+")
        for userName in sorted(ell.eventLists.keys()):
            el = ell.eventLists[userName]
            for path in sorted(el.events.keys()):
                f.write("%s: %s\n" % (userName, path))
        f.close()
    except Exception, detail:
        if f != None:
            f.close()

def reloadSignalHandler(num, frame):
    logMessage("info", "Received signal to reload.")
    signal.signal(num, reloadSignalHandler)
    globals.eventListList.load(globals.allowedUsers.get())

def quitSignalHandler(num, frame):
    logMessage("info", "Received signal to exit.")
    globals.pidFile.remove()
    sys.exit(0)

def printUsage(progName):
    print """\
usage: %s

This program loads a collection of event definitions from one or
more users and executes commands according their defined schedulues.
When run as root, event definitions are read from registered users
(listed in hcron.allow) for the local host; otherwise, this is done
for the current user, only.""" % progName

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
    setupLogger()
    globals.allowedUsers = AllowedUsersFile(HCRON_ALLOW_PATH)
    globals.signalHome = SignalHome(HCRON_SIGNAL_HOME)
    globals.eventListList = EventListList(globals.allowedUsers.get())

    signal.signal(signal.SIGHUP, reloadSignalHandler)
    signal.signal(signal.SIGUSR1, dumpSignalHandler)
    signal.signal(signal.SIGTERM, quitSignalHandler)
    signal.signal(signal.SIGQUIT, quitSignalHandler)
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)   # we don't care about children/zombies

    globals.server = Server()
    globals.server.serverize()  # don't catch SystemExit
    globals.pidFile = PidFile(HCRON_PID_FILE_PATH)
    globals.pidFile.create()

    try:
        logStart()
        globals.server.run()
    except Exception, detail:
        logMessage("warning", "Unexpected exception (%s)." % detail)
        #print detail
        pass

    globals.pidFile.remove()
    logExit()
    sys.exit(-1)
