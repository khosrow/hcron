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
import os.path
import sys
import os
import pwd
import shutil

# app imports
from hcron.constants import *
from hcron.event import signal_reload
from hcron.file import ConfigFile
from hcron.library import copytree, get_events_home
from hcron import globals

def make_events_snapshot():
    """This depends on python >=v2.5 which creates intermediate
    directories as required.
    """
    globals.config = ConfigFile(HCRON_CONFIG_PATH)
    eventsBasePath = globals.config.get("eventsBasePath", "").strip()

    if eventsBasePath == "":
        src = os.path.expanduser("~%s/.hcron/%s/events" % (USER_NAME, HOST_NAME))
    else:
        src = os.path.join(eventsBasePath, USER_NAME, ".hcron/%s/events" % HOST_NAME)

    dst = get_events_home(USER_NAME)

    # paranoia
    if not dst.startswith(HCRON_EVENTS_SNAPSHOT_HOME):
        raise Exception("Bad destination")

    shutil.rmtree(dst)
    copytree(src, dst, USER_ID)

def print_usage(progName):
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
            print_usage(progName)
            sys.exit(0)
        else:
            print_usage(progName)
            sys.exit(-1)

    #
    # setup
    #
    if 0:
        # plan to move this to something like scheduler
        try:
            make_events_snapshot()
        except:
            print "Error: Could not copy events."
            sys.exit(-1)

    try:
        signal_reload()
        print "Reload signalled for this machine (%s)." % HOST_NAME
    except Exception, detail:
        #print detail
        sys.exit(-1)

    sys.exit(0)
