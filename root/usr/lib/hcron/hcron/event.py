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
from hcron.library import WHEN_BITMASKS, WHEN_INDEXES, WHEN_MIN_MAX, listStToBitmask, dirWalk, getEventsHome
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

    The main/parent process spawns a process for each event. Each
    event (with its chained events) runs in its own process. This
    allows Event to be simple (i.e., no process management, chain
    management).

    Process management (parent): we can regulate the number of
    processes running from here, based on the number of children.

    Chain management (child): we can track and call chain events
    from here based on the return values of the event.activate.
    """
    childPids = {}

    for event in events:
        while len(childPids) > 100:
            # reap immediate children: block wait for first, clean up others without waiting
            pid, status = os.waitpid(0, 0)
            del childPids[pid]

            pid, status = os.waitpid(0, os.WNOHANG)
            while pid != 0:
                del childPids[pid]
                pid, status = os.waitpid(0, os.WNOHANG)

        pid = os.fork()
        childPids[pid] = None

        if pid == 0:
            # child
            eventChainNames = []

            while event:
                eventChainNames.append(event.getName())

                #logMessage("info", "Processing event (%s)." % event.getName())
                try:
                    nextEventName = event.activate(eventChainNames)
                except Exception, detail:
                    logMessage("error", "handleEvents (%s)" % detail)
                    nextEventName = None
    
                if nextEventName == None:
                    break

                logChainEvents(event.userName, event.getName(), nextEventName, cycleDetected=(nextEventName in eventChainNames))

                if nextEventName in eventChainNames:
                    break
                else:
                    eventList = globals.eventListList.get(event.userName)
                    nextEvent = eventList and eventList.get(nextEventName)
                    event = nextEvent

            os._exit(0)

        else:
            # parent
            pass

    while childPids:
        pid, status = os.waitpid(0, 0)
        del childPids[pid]

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

class CannotLoadFileException(Exception):
    pass

class BadEventDefinitionException(Exception):
    pass

class BadVariableSubstitutionException(Exception):
    pass

class TemplateEventDefinitionException(Exception):
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

    def get(self, name):
        return self.events.get(name)

    def load(self):
        self.events = {}
        eventsHome = getEventsHome(self.userName)

        if eventsHome == None:
            return

        try:
            # allow read even if over NFS with root_squash;
            # catch any possible exceptions to guarantee seteuid(0)
            os.seteuid(pwd.getpwnam(self.userName).pw_uid)

            eventsHomeLen = len(eventsHome)
            maxEventsPerUser = globals.config.get().get("maxEventsPerUser", MAX_EVENTS_PER_USER)
            namesToIgnoreCregexp = globals.config.get().get("namesToIgnoreCregexp")
            ignoreMatchFn = namesToIgnoreCregexp and namesToIgnoreCregexp.match

            for root, dirNames, fileNames in dirWalk(eventsHome, ignoreMatchFn=ignoreMatchFn):
                for fileName in fileNames:
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
            # load first (in order to check for test meaningfully)
            try:
                lines = open(self.path, "r")
            except Exception, detail:
                self.reason = "cannot load file"
                raise CannotLoadFileException("Ignored event file (%s)." % self.path)

            for line in lines:
                line = line.strip()
    
                if line == "" or line.startswith("#"):
                    continue

                try:
                    name, value = line.split("=", 1)
                except Exception, detail:
                    self.reason = "bad definition"
                    raise BadEventDefinitionException("Ignored event file (%s)." % self.path)

                try:
                    value = self.hcronVariableSubstitution(value, "HCRON_EVENT_NAME", self.name, self.name.split("/"))
                    value = self.hcronVariableSubstitution(value, "HCRON_HOST_NAME", socket.getfqdn(), None)
                except Exception, detail:
                    self.reason = "bad variable substitution"
                    BadVariableSubstitutionException("Ignored event file (%s)." % self.path)

                d[name] = value

            # enforce some fields
            d.setdefault("template_name", None)

            # template check
            if d["template_name"] == self.name.split("/")[-1]:
                self.reason = "template"
                raise TemplateEventDefinitionException("Ignored event file (%s). Template name (%s)." % (self.path, d["template_name"]))
    
            # bad definition check
            try:
                for name, value in d.items():
                    if name.startswith("when_"):
                        masks[WHEN_INDEXES[name]] = listStToBitmask(value, WHEN_MIN_MAX[name], WHEN_BITMASKS[name])
    
            except Exception, detail:
                self.reason = "bad when_* setting"
                raise BadEventDefinitionException("Ignored event file (%s)." % self.path)

            # full specification check
            for name in HCRON_EVENT_DEFINITION_NAMES:
                if name not in d:
                    self.reason = "not fully specified"
                    raise BadEventDefinitionException("Ignored event file (%s). Missing name (%s)." % \
                        (self.path, name))

        except:
            if self.reason == None:
                self.reason = "unknown problem"

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
            try:
                if not (datemasks[i] & masks[i]):
                    return 0
            except Exception, detail:
                # should not get here
                logMessage("error", "detail (%s) self.reason (%s) user (%s) name (%s) d (%s)." % \
                    (detail, self.reason, self.userName, self.name, str(self.d)))
                return 0

        return 1

    def activate(self, eventChainNames=None):
        """Activate event and return next event in chain.
        """
        asUserName = self.d.get("as_user")
        command = self.d.get("command")
        if asUserName == "":
            asUserName = self.userName
        hostName = self.d.get("host")

        asUserName = self.hcronVariableSubstitution(asUserName, "HCRON_EVENT_CHAIN", None, eventChainNames)
        hostName = self.hcronVariableSubstitution(hostName, "HCRON_EVENT_CHAIN", None, eventChainNames)
        command = self.hcronVariableSubstitution(command, "HCRON_EVENT_CHAIN", None, eventChainNames)

        # execute
        retVal = remoteExecute(self.name, self.userName, asUserName, hostName, command)

        if retVal == 0:
            # success
            # notify
            toAddr = self.d.get("notify_email")
            if toAddr:
                content = self.d.get("notify_message", "")
                content = self.hcronVariableSubstitution(content, "HCRON_EVENT_CHAIN", ":".join(eventChainNames), eventChainNames)

                subject = """hcron: "%s" executed at %s@%s""" % (self.name, asUserName, hostName)
                sendEmailNotification(self.name, self.userName, toAddr, subject, content)
    
            nextEventName = self.d.get("next_event")
    
        else:
            # child, with problem
            nextEventName = self.d.get("failover_event")

        # handle None, "", and valid string
        nextEventName = nextEventName and self.resolveEventName(nextEventName.strip()) or None

        return nextEventName

    def resolveEventName(self, name):
        """Resolve event name relative to the current event.
        
        1) relative to .../events, if starts with "/"
        2) relative to the current path
        """
        if not name.startswith("/"):
            name = os.path.join("/", os.path.dirname(self.name), name)

        name = os.path.normpath(name)[1:]

        return name

    def hcronVariableSubstitution(self, value, varName, varValue, varValues):
        """Perform variable substitution.
        """
        wVarName = "$%s" % varName
        if wVarName not in value:
            return value

        if varValues:
            # resolve varName[index]
            for i in xrange(-len(varValues), len(varValues)):
                wVarName = "$%s[%d]" % (varName, i)
                value = value.replace(wVarName, varValues[i])

            wVarName = "$%s[" % varName
            if wVarName in value:
                raise Exception("Variable index out of range.")

        if varValue:
            # resolve varName
            wVarName = "$%s" % varName
            value = value.replace(wVarName, varValue)

        return value
