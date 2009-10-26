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

def signalReload():
    """Signal to reload.
    """
    import tempfile
    from hcron.file import AllowedUsersFile, ConfigFile

    globals.config = ConfigFile(HCRON_CONFIG_PATH)
    globals.allowedUsers = AllowedUsersFile(HCRON_ALLOW_PATH)
    config = globals.config.get()
    signalHome = config.get("signalHome") or HCRON_SIGNAL_HOME
    userName = pwd.getpwuid(os.getuid()).pw_name

    if userName not in globals.allowedUsers.get():
        raise Exception("Warning: You are not an allowed hcron user.")

    try:
        tempfile.mkstemp(prefix=userName, dir=signalHome)
    except:
        raise Exception("Error: Could not signal for reload.")

def handleEvents(events):
    """Handle all events given and chain events as specified in the
    events being handled.
    """
    for event in events:
        chainedEvents = {}

        while event and event not in chainedEvents:
            chainedEvents[event] = None

            #logMessage("info", "Processing event (%s)." % event.getName())
            try:
                nextEventName = event.activate()
            except Exception, detail:
                logMessage("error", "handleEvents (%s)" % detail)
                nextEventName = None

            if nextEventName != None:
                eventList = globals.eventListList.get(event.userName)
                nextEvent = eventList and eventList.get(nextEventName)
                logChainEvents(event.userName, event.getName(), nextEventName, cycleDetected=(nextEvent in chainedEvents))
                event = nextEvent

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
    """Event list list.

    All event lists are keyed on user name.
    """
    def __init__(self, userNames):
        logMessage("info", "Initializing events list.")
        self.load(userNames)

    def get(self, userName):
        return self.eventLists.get(userName)

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
    """Event list for a user.

    All events are key on their name (i.e., path relative to
    ~/.hcron/<hostName>/events).
    """

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

    def get(self, name):
        return self.events.get(name)

    def load(self):
        self.events = {}
        eventsHome = self.getEventsHome()

        if eventsHome == None:
            return

        try:
            # allow read even if over NFS with root_squash;
            # catch any possible exceptions to guarantee seteuid(0)
            os.seteuid(pwd.getpwnam(self.userName).pw_uid)

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
                        pass
                        #continue

                    self.events[name] = event

                    if len(self.events) >= maxEventsPerUser:
                        event.reason = "maximum events reached"
                        logMessage("warning", "Reached maximum events allowed (%s)." % maxEventsPerUser)

        except Exception, detail:
            logMessage("error", "Could not load events.")

        os.seteuid(0)  # guarantee return to uid 0

        self.dump()

    def dump(self):
        eventListFileName = "%s/%s" % (HCRON_EVENT_LISTS_DUMP_DIR, self.userName)

        if not eventListFileName.startswith(HCRON_EVENT_LISTS_DUMP_DIR):
            # paranoia?
            return

        oldUmask = os.umask(0337)

        try:
            os.remove(eventListFileName)
        except:
            pass

        try:
            userId = pwd.getpwnam(self.userName).pw_uid
            f = open(eventListFileName, "w+")
            os.chown(eventListFileName, userId, 0)

            events = self.events

            for name in sorted(events.keys()):
                reason = events[name].reason
                if reason == None:
                    f.write("accepted::%s\n" % name)
                else:
                    f.write("rejected:%s:%s\n" % (reason, name))

            f.close()
        except Exception, detail:
            if f != None:
                f.close()

        os.umask(oldUmask)

    def printEvents(self):
        for name, event in self.events.items():
            print "name (%s) event (%s)" % (name, event)

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
        self.reason = None
        self.load()

    def getName(self):
        return self.name

    def getPath(self):
        return self.path

    def load(self):
        # default for implied "this year"
        d = {
            "when_year": "*",
        }
        masks = {
            WHEN_INDEXES["when_year"]: listStToBitmask("*", WHEN_MIN_MAX["when_year"], WHEN_BITMASKS["when_year"]),
        }

        try:
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
                self.reason = "bad definition"
                self.d = d
                raise BadEventDefintionException("Ignored event file (%s)." % self.path)
    
            # enforce some fields
            d.setdefault("template_name", None)
    
            # discard templates
            if d["template_name"] == self.name.split("/")[-1]:
                self.reason = "template"
                self.d = d
                raise TemplateEventDefinitionException("Ignored event file (%s). Template name (%s)." % (self.path, d["template_name"]))
    
            # check for full specification
            for name in HCRON_EVENT_DEFINITION_NAMES:
                if name not in d:
                    self.reason = "not fully specified"
                    self.d = d
                    raise BadEventDefinitionException("Ignored event file (%s). Missing name (%s)." % \
                        (self.path, name))

        except:
            pass

        self.d = d
        self.masks = masks

    def __repr__(self):
        when = "%s %s %s %s %s %s" % \
            (self.d.get("when_year"),
                self.d.get("when_month"),
                self.d.get("when_day"),
                self.d.get("when_hour"),
                self.d.get("when_minute"),
                self.d.get("when_dow"))
        return """<Event name (%s) when (%s)>""" % (self.name, when)

    def test(self, datemasks):
        if self.reason != None:
            return 0

        masks = self.masks
        for i in xrange(len(datemasks)):
            if not (datemasks[i] & masks[i]):
                return 0
        return 1

    def activate(self):
        """Activate event and return next event in chain.
        """
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

        nextEventName = self.d.get("next_event")
        nextEventName = nextEventName and self.resolveEventName(nextEventName)

        return nextEventName

    def resolveEventName(self, name):
        """Resolve event name relative to the current event.
        
        1) relative to .../events
        2) relative to the current path
        """
        if name.startswith("~/"):
            name = name[2:]
        else:
            name = os.path.normpath(os.path.join(os.path.dirname(self.name), name))

        return name

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
