#! /usr/bin/env python
#
# server.py

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

"""Library of routines, classes, etc. for hcron.
"""

# system imports
from datetime import datetime, timedelta
import os
import sys
from time import sleep, time

# app imports
from hcron.constants import *
import hcron.globals as globals
from hcron.event import EventListList, handle_events, reload_events
from hcron.library import date_to_bitmasks
from hcron.logger import *

class Server:
    def serverize(self):
        if os.fork() != 0:
            # exit original/parent process
            sys.exit(0)
   
        # close streams - the Python way
        sys.stdin.close(); os.close(0); os.open("/dev/null", os.O_RDONLY)
        sys.stdout.close(); os.close(1); os.open("/dev/null", os.O_RDWR)
        sys.stderr.close(); os.close(2); os.open("/dev/null", os.O_RDWR)
    
        # detach from controlling terminal
        os.setsid()
    
        # misc
        os.chdir("/")   # / is always available
        os.umask(0022)

    def run(self, immediate=False):
        """Run scheduling loop.
        """
        minuteDelta = timedelta(minutes=1)
        now = datetime.now()

        if immediate:
            # special case: run with the current "now" time instead of
            # waiting for the next interval
            self.run_now(now)

        while True:
            #
            # prep for next interval
            #
            next = now+minuteDelta
            next = next.replace(second=0)
            oldNow = now
            now = datetime.now()
            delta = (next-now).seconds+2
    
            log_sleep(delta)
            sleep(delta)
            now = datetime.now()

            #
            # check and update as necessary
            #
            if globals.config.is_modified():
                log_message("info", "hcron.conf was modified")
                # restart
                globals.pidFile.remove()
                if "--immediate" not in sys.argv:
                    # do not miss current "now" time
                    sys.argv.append("--immediate")
                os.execv(sys.argv[0], sys.argv)
            if globals.allowedUsers.is_modified():
                log_message("info", "hcron.allow was modified")
                globals.allowedUsers.load()
                globals.eventListList = EventListList(globals.allowedUsers.get())
            if globals.signalHome.is_modified():
                log_message("info", "signalHome was modified")
                globals.signalHome.load()
                reload_events(globals.signalHome.get_modified_time())

            self.run_now(now)

    def run_now(self, now):
        """Run using the "now" time value.
        """
        #
        # match events and act
        #
        t0 = time()
        # hcron: 0=sun - 6=sat; isoweekday: 1=mon = 7=sun
        hcronWeekday = now.isoweekday() % 7
        datemasks = date_to_bitmasks(now.year, now.month, now.day, now.hour, now.minute, hcronWeekday)
        events = globals.eventListList.test(datemasks)
        if events:
            handle_events(events)
        log_work(len(events), (time()-t0))
