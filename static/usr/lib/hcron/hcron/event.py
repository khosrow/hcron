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
from datetime import datetime
import fnmatch
import os
import os.path
import pwd
import re
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

                # allow cycles up to a limit
                #if nextEventName in eventChainNames:
                if len(eventChainNames) > 3:
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
            f = None
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

    def getVarInfo(self, eventChainNames=None):
        dt_utc = datetime.utcnow()
        dt_local = datetime.now()

        varInfo = {
            "when_year": "*",
            "template_name": None,
            "HCRON_DATETIME": datetime.strftime(dt_local, "%Y:%m:%d:%H:%M:%S:%W:%w"),
            "HCRON_DATETIME_UTC": datetime.strftime(dt_utc, "%Y:%m:%d:%H:%M:%S:%W:%w"),
            "HCRON_HOST_NAME": socket.getfqdn(),
            "HCRON_EVENT_NAME": self.name,
        }
        
        if eventChainNames:
            selfEventChainNames = []
            lastEventChainName = eventChainNames[-1]
            for eventChainName in reversed(eventChainNames):
                if eventChainName != lastEventChainName:
                    break
                selfEventChainNames.append(eventChainName)
            varInfo["HCRON_EVENT_CHAIN"] = ":".join(eventChainNames)
            varInfo["HCRON_SELF_CHAIN"] = ":".join(selfEventChainNames)
        else:
            varInfo["HCRON_EVENT_CHAIN"] = ""
            varInfo["HCRON_SELF_CHAIN"] = ""

        return varInfo

    def load(self):
        varInfo = self.getVarInfo()

        masks = {
            WHEN_INDEXES["when_year"]: listStToBitmask("*", WHEN_MIN_MAX["when_year"], WHEN_BITMASKS["when_year"]),
        }

        try:
            try:
                st = open(self.path, "r").read()
            except Exception, detail:
                self.reason = "cannot load file"
                raise CannotLoadFileException("Ignored event file (%s)." % self.path)

            try:
                assignments = load_assignments(st)
            except Exception, detail:
                self.reason = "bad definition"
                raise BadEventDefinitionException("Ignored event file (%s)." % self.path)

            try:
                # early substitution
                eval_assignments(assignments, varInfo)
            except Exception, detail:
                self.reason = "bad variable substitution"
                raise BadVariableSubstitutionException("Ignored event file (%s)." % self.path)

            # template check
            if varInfo["template_name"] == self.name.split("/")[-1]:
                self.reason = "template"
                raise TemplateEventDefinitionException("Ignored event file (%s). Template name (%s)." % (self.path, varInfo["template_name"]))
    
            # bad definition check
            try:
                for name, value in varInfo.items():
                    if name.startswith("when_"):
                        masks[WHEN_INDEXES[name]] = listStToBitmask(value, WHEN_MIN_MAX[name], WHEN_BITMASKS[name])
    
            except Exception, detail:
                self.reason = "bad when_* setting"
                raise BadEventDefinitionException("Ignored event file (%s)." % self.path)

            # full specification check
            for name in HCRON_EVENT_DEFINITION_NAMES:
                if name not in varInfo:
                    self.reason = "not fully specified, missing field (%s)" % name
                    raise BadEventDefinitionException("Ignored event file (%s). Missing field (%s)." % \
                        (self.path, name))
        except:
            if self.reason == None:
                self.reason = "unknown problem"

        self.when = "%s %s %s %s %s %s" % \
            (varInfo.get("when_year"),
                varInfo.get("when_month"),
                varInfo.get("when_day"),
                varInfo.get("when_hour"),
                varInfo.get("when_minute"),
                varInfo.get("when_dow"))

        self.assignments = assignments
        self.masks = masks

    def __repr__(self):
        return """<Event name (%s) when (%s)>""" % (self.name, self.when)

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
                logMessage("error", "detail (%s) self.reason (%s) user (%s) name (%s) when (%s)." % \
                    (detail, self.reason, self.userName, self.name, self.when))
                return 0

        return 1

    def activate(self, eventChainNames=None):
        """Activate event and return next event in chain.
        """
        varInfo = self.getVarInfo(eventChainNames)

        # late substitution
        eval_assignments(self.assignments, varInfo)
        #open("/tmp/hc", "a").write("self.name (%s) varInfo (%s)\n" % (self.name, str(varInfo)))

        # get event file def
        event_as_user = varInfo.get("as_user")
        event_command = varInfo.get("command")
        if event_as_user == "":
            event_as_user = self.userName
        event_host = varInfo.get("host")
        event_notify_email = varInfo.get("notify_email")
        event_notify_message = varInfo.get("notify_message", "")
        event_next_event = varInfo.get("next_event", "")
        event_failover_event = varInfo.get("failover_event", "")

        # execute (host required)
        if event_host == "":
            retVal = 0
        else:
            retVal = remoteExecute(self.name, self.userName, event_as_user, event_host, event_command)

        if retVal == 0:
            # success
            # notify
            if event_notify_email:
                subject = """hcron: "%s" executed at %s@%s""" % (self.name, event_as_user, event_host)
                sendEmailNotification(self.name, self.userName, event_notify_email, subject, event_notify_message)
    
            nextEventName = event_next_event
    
        else:
            # child, with problem
            nextEventName = event_failover_event

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

import re

SUBST_NAME_RE = "(?P<op>[#$])(?P<name>HCRON_\w*)"
SUBST_NAME_CRE = re.compile(SUBST_NAME_RE)
def searchNameSelect(st, lastPos):
    """Find startPos and endPos for:
    1. [#$]<name>[<body>]
    2. [#$]<name>{<body>}
    3. [#$]<name>
    otherwise:
    3. None, None
    """
    startPos, endPos = None, None
    s = SUBST_NAME_CRE.search(st, lastPos)
    if s:
        startPos, endPos = s.span()
        if endPos < len(st):
            openB = st[endPos]
            if openB in [ "[", "{" ]:
                if openB == "[":
                    closeB = "]"
                elif openB == "{":
                    closeB = "}"

                depth = 0
                for ch in st[endPos:]:
                    if ch == openB:
                        depth += 1
                    elif ch == closeB:
                        depth -= 1
                        if depth == 0:
                            endPos += 1
                            break
                    endPos += 1
                else:
                    # no closing bracket
                    startPos = None
                    endPos = None

    return startPos, endPos
        
SUBST_NAME_SELECT_RE = "(?P<op>[#$])(?P<name>HCRON_\w*)(((?P<square_bracket>\[)(?P<square_select>.*)\])|((?P<curly_bracket>\{)(?P<curly_select>.*)\}))?"
SUBST_SEP_LIST_RE = "(?:(?P<sep>.*)!)?(?P<list>.*)"
SUBST_LIST_RE = "(.*)(?:,(.*))?"
SUBST_SLICE_RE = "(\d*)(:(\d*))?(:(\d*))?"
SUBST_NAME_SELECT_CRE = re.compile(SUBST_NAME_SELECT_RE)
SUBST_SEP_LIST_CRE = re.compile(SUBST_SEP_LIST_RE)
SUBST_LIST_CRE = re.compile(SUBST_LIST_RE)
SUBST_SLICE_CRE = re.compile(SUBST_SLICE_RE)

def hcronVariableSubstitution(value, varInfo, depth=1):
    """Perform variable substitution.

    Search for substitutable segments, substitute, repeat. Once a
    substitution is done, that segment is not treated again.
    """
    l = []
    lastPos = 0
    while True:
        if 0:
            s = SUBST_NAME_SELECT_CRE.search(value, lastPos)
            if s == None:
                break
            startPos, endPos = s.span()

        startPos, endPos = searchNameSelect(value, lastPos)

        if startPos == None:
            break

        l.append(value[lastPos:startPos])
        l.append(hcronVariableSubstitution2(value[startPos:endPos], varInfo))
        lastPos = endPos

    l.append(value[lastPos:])

    #open("/tmp/hc", "a").write("value (%s) -> (%s)\n" % (value, "".join(l)))

    return "".join(l)

def hcronVariableSubstitution2(value, varInfo, depth=1):
    """Recursively resolve all variables in value with settings in
    varInfo. The mechanism is:
    1) match
    2) resolve
    3) proceed to next match level (name, select, ...)
    """
    try:
        # default
        substSep = ":"

        nid = SUBST_NAME_SELECT_CRE.match(value).groupdict()
        #open("/tmp/hc", "a").write("nid (%s)\n" % str(nid))

        op = nid.get("op")
        substName = nid.get("name")
        nameValue = varInfo.get(substName)
        substBracket = nid.get("square_bracket") and "[" or (nid.get("curly_bracket") and "{") or None
        #open("/tmp/hc", "a").write(" **** substBracket *** (%s)\n" % substBracket)
        if substBracket == "[":
            substSelect = nid.get("square_select", "")
        elif substBracket == "{":
            substSelect = nid.get("curly_select", "")
        else:
            substSelect = None
        substSelect = hcronVariableSubstitution2(substSelect, varInfo, depth+1)


        if substSelect == None:
            # no select
            if nameValue != None:
                value = nameValue
        else:
            sid = SUBST_SEP_LIST_CRE.match(substSelect).groupdict()
            substSep = sid.get("sep")
            if substSep == None:
                # special case!
                substSep = substName == "HCRON_EVENT_NAME" and "/" or ":"
            else:
                substSep = hcronVariableSubstitution2(substSep, varInfo, depth+1)

            nameValues = nameValue.split(substSep)

            substList = sid["list"]
            substList = hcronVariableSubstitution2(substList, varInfo, depth+1)

            # fix RE to avoid having to check for None for single list value
            ll = substList.split(",")
            #open("/tmp/hc", "a").write("-- ll (%s)\n" % str(ll))

            if substBracket == "[":
                # indexing
                for i in xrange(len(ll)):
                    ll[i] = hcronVariableSubstitution2(ll[i], varInfo, depth+1)
                    #open("/tmp/hc", "a").write("---- ll (%s) i (%s) ll[i] (%s)\n" % (str(ll), i, ll[i]))
                    irl = [ el != "" and el or None for el in SUBST_SLICE_CRE.match(ll[i]).groups() ]
                    #open("/tmp/hc", "a").write("------- irl (%s)\n" % str(irl))
                    start, endColon, end, stepColon, step = irl[0:5]
                    start = hcronVariableSubstitution2(start, varInfo, depth+1)
                    end = hcronVariableSubstitution2(end, varInfo, depth+1)
                    step = hcronVariableSubstitution2(step, varInfo, depth+1)

                    if start != "":
                        start = int(start)
                    if end == None:
                        if endColon == None:
                            end = start+1
                        else:
                            end = None
                    else:
                        end = int(end)
                    if step == None:
                        if stepColon == None:
                            step = 1
                        else:
                            step = None
                    else:
                        step = int(step)
                    ll[i] = substSep.join(nameValues[start:end:step])
                    #open("/tmp/hc", "a").write("------------ ll[i] (%s)\n" % str(ll[i]))
            elif substBracket == "{":
                # matching: substitute, match, flatten
                ll = [ hcronVariableSubstitution2(x, varInfo, depth+1) for x in ll ]
                #open("/tmp/hc", "a").write("---- ll (%s) nameValues (%s)\n" % (str(ll), nameValues))
                ll = [ el for x in ll for el in fnmatch.filter(nameValues, x) ]
                #open("/tmp/hc", "a").write("------ ll (%s)\n" % str(ll))

            value = substSep.join(ll)

        if op == "#" and nameValue != None:
            #open("/tmp/hc", "a").write("*** name (%s) nameValue (%s) sep (%s) value (%s) count (%s)\n" % (substName, nameValue, substSep, value, value.count(substSep)+1))
            value = str(value.count(substSep)+1)
    except:
        import traceback
        #open("/tmp/hc", "a").write("tackback ++++++++ (%s)\n" % traceback.format_exc())
        #print traceback.print_exc()
        pass

    return value

def load_assignments(st):
    """Load lines with the format name=value into a list of
    (name, value) tuples.
    """
    l = []

    for line in st.split("\n"):
        line = line.strip()
        if line.startswith("#") or line == "":
            continue
        name, value  = line.split("=", 1)
        l.append((name.strip(), value.strip()))

    return l

def eval_assignments(assignments, varInfo):
    """Evaluate assignments using the settings in varInfo and storing the
    results back to varInfo.
    """
    for name, value in assignments:
        varInfo[name] = hcronVariableSubstitution(value, varInfo)


