#! /usr/bin/env python
#
# event.py

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

"""Event related classes, etc.
"""

# system imports
import os
import os.path
import pwd
import stat
import time

# app imports
from hcron.constants import *
import hcron.globals as globals
from hcron.library import listStToBitmask, WHEN_BITMASKS, WHEN_INDEXES, WHEN_MIN_MAX
from hcron.notify import sendEmailNotification
from hcron.execute import remoteExecute
from hcron.logger import *

def handleEvents(events):
    for event in events:
        #logMessage("info", "Processing event (%s)." % event.name)
        try:
            event.activate()
        except Exception, detail:
            logMessage("error", "handleEvents (%s)" % detail)

def reloadEvents(signalHomeMtime):
    """Reload events for all users whose signal file mtime is <= to
    that of the signal home directory. Any signal files that are
    created subsequently, will be caught in the next pass.
    """
    userNames = {}  # to ensure reload only once per user

    for fileName in os.listdir(HCRON_SIGNAL_HOME):
        path = os.path.join(HCRON_SIGNAL_HOME, fileName)
        st = os.stat(path)
        mtime = st[stat.ST_MTIME]

        if mtime <= signalHomeMtime:
            ownerId = st[stat.ST_UID]
            userName = pwd.getpwuid(ownerId).pw_name

            if userName not in userNames:
                globals.eventListList.reload(userName)
                userNames[userName] = None

            try:
                os.remove(path) # remove singles and multiples
            except Exception, detail:
                logMessage("warning", "Could not remove signal file (%s)." % path)

class BadEventDefinitionException(Exception):
    pass

class EventListList:
    def __init__(self, userNames):
        logMessage("info", "Initializing events list.")
        self.load(userNames)

    def load(self, userNames=None):
        """Load from scratch.
        """
        logMessage("info", "Loading events.")

        t0 = time.time()
        self.eventLists = {}
        self.userNames = userNames
        total = 0 

        for userName in self.userNames:
            self.reload(userName)

    def reload(self, userName):
        if userName not in self.userNames:
            return

        if userName in self.eventLists:
            self.remove(userName)

        t0 = time.time()
        el = EventList(userName)
        t1 = time.time()

        if el:
            self.eventLists[userName] = el
            count = len(el.events)
            logLoadEvents(userName, count, t1-t0)

    def remove(self, userName):
        if userName in self.eventLists:
            count = len(self.eventLists[userName].events)

            logDiscardEvents(userName, count)
            del self.eventLists[userName]

    def test(self, datemasks, userNames=None):
        events = []
        userNames = userNames or self.userNames

        for userName in userNames:
            el = self.eventLists.get(userName)

            if el:
                events.extend(el.test(datemasks))
        return events

class EventList:
    def __init__(self, userName):
        self.userName = userName
        self.load()

    def getEventsHome(self):
        config = globals.config.get()
        eventsBasePath = (config.get("eventsBasePath") or "").strip()

        if eventsBasePath == "":
            path = os.path.expanduser("~%s/.hcron/%s/events" % (self.userName, HOST_NAME))
        else:
            path = os.path.join(eventsBasePath, self.userName, ".hcron/%s/events" % HOST_NAME)

        if path.startswith("~"):
            return None

        return path

    def load(self):
        self.events = {}
        eventsHome = self.getEventsHome()

        if eventsHome == None:
            return

        eventsHomeLen = len(eventsHome)
        maxEventsPerUser = globals.config.get().get("maxEventsPerUser", MAX_EVENTS_PER_USER)

        for root, dirNames, fileNames in os.walk(eventsHome):
            for fileName in fileNames:
                if fileName.startswith("."):
                    # ignore hidden files
                    continue

                path = os.path.join(root, fileName)

                try:
                    name = path[eventsHomeLen+1:]
                    event = Event(path, name, self.userName)
                except Exception, detail:
                    # bad Event definition
                    continue

                self.events[path] = event

                if len(self.events) == maxEventsPerUser:
                    logMessage("warning", "Reached maximum events allowed (%s)." % maxEventsPerUser)
                    return

    def printEvents(self):
        for path, event in self.events.items():
            print "path (%s) event (%s)" % (path, event)

    def test(self, datemasks):
        events = []

        for event in self.events.values():
            if event.test(datemasks):
                events.append(event)

        return events

class Event:
    def __init__(self, path, name, userName):
        self.path = path
        self.userName = userName
        self.name = name
        self.load()

    def load(self):
        d = {}
        masks = {}
        try:
            f = open(self.path, "r")

            for line in f:
                line = line.strip()

                if line == "" or line.startswith("#"):
                    continue

                name, value = line.split("=", 1)
                d[name] = self.hcronVariableSubstitution(value)

                if name.startswith("when_"):
                    masks[WHEN_INDEXES[name]] = listStToBitmask(value, WHEN_MIN_MAX[name], WHEN_BITMASKS[name])

        except Exception, detail:
            raise BadEventDefintionException("Ignored event file (%s)." % self.path)

        # enforce some fields
        d.setdefault("template_name", None)

        # discard templates
        if d["template_name"] == self.name.split("/")[-1]:
            raise TemplateEventDefinitionException("Ignored event file (%s). Template name (%s)." % (self.path, d["template_name"]))

        # check for full specification
        for name in HCRON_EVENT_DEFINITION_NAMES:
            if name not in d:
                raise BadEventDefinitionException("Ignored event file (%s). Missing name (%s)." % \
                    (self.path, name))

        self.d = d
        self.masks = masks

    def __repr__(self):
        when = "%(when_month)s %(when_day)s %(when_hour)s %(when_minute)s %(when_dow)s" % self.d
        return """<Event name (%s) when (%s)>""" % (self.name, when)

    def test(self, datemasks):
        masks = self.masks
        for i in xrange(len(datemasks)):
            if not (datemasks[i] & masks[i]):
                return 0
        return 1

    def activate(self):
        asUserName = self.d.get("as_user")
        command = self.d.get("command")
        if asUserName == "":
            asUserName = self.userName
        hostName = self.d.get("host")

        # execute
        remoteExecute(self.name, self.userName, asUserName, hostName, command)

        # notify
        toAddr = self.d.get("notify_email")
        if toAddr:
            content = self.d.get("notify_message", "")
            subject = """hcron: "%s" executed at %s@%s""" % (self.name, asUserName, hostName)
            sendEmailNotification(self.name, self.userName, toAddr, subject, content)

    def hcronVariableSubstitution(self, value):
        """Perform HCRON_* variable substitution.
        """
        # check for HCRON_*
        if "$HCRON_" not in value:
            return value

        # resolve HCRON_EVENT_NAME[*] then HCRON_EVENT_NAME
        components = self.name.split("/")
        for i in xrange(-len(components), len(components)):
            variable = "$HCRON_EVENT_NAME[%d]" % i
            component = components[i]
            value = value.replace(variable, component)

        if "$HCRON_EVENT_NAME[" in value:
            raise Exception("Variable index out of range.")

        value = value.replace("$HCRON_EVENT_NAME", self.name)

        # HCRON_HOST_NAME
        value = value.replace("$HCRON_HOST_NAME", socket.getfqdn())

        return value
