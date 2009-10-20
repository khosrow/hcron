#! /usr/bin/env python
#
# file.py

# GPL--start
# This file is part of hcron
# Copyright (C) 2008 Environment/Environnement Canada
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
import os
import os.path
import pwd
import stat
import sys

# app imports
from hcron.constants import *
import hcron.globals as globals
from hcron.logger import *
from hcron.safeeval import safe_eval

class TrackableFile:
    def __init__(self, path):
        self.path = path
        self.contents = None
        self.mtime = None
        self.load()

    def load(self):
        pass

    def isModified(self):
        if self.path:
            mtime = os.stat(self.path)[stat.ST_MTIME]
            return mtime != self.mtime

    def getModifiedTime(self):
        return self.mtime

    def get(self):
        return self.contents

class ConfigFile(TrackableFile):
    def load(self):
        d = {}

        try:
            mtime = os.stat(self.path)[stat.ST_MTIME]
            st = open(self.path, "r").read()
            d = safe_eval(st)
            logLoadConfig()
        except Exception, detail:
            logMessage("error", "Cannot load config file (%s)." % self.path)
            sys.exit(-1)

        self.contents = d
        self.mtime = mtime

class AllowedUsersFile(TrackableFile):
    def load(self):
        allowedUsers = []
        try:
            mtime = os.stat(self.path)[stat.ST_MTIME]
            st = open(self.path, "r").read()

            for line in st.split("\n"):
                line = line.strip()
                if line.startswith("#") or line == "":
                    continue

                userName = line
                if userName != "":
                    allowedUsers.append(userName)

            logLoadAllow()
        except Exception, detail:
                logMessage("error", "Cannot load allow file (%s)." % self.path)

        self.contents = list(set(allowedUsers))
        self.mtime = mtime

class old_AllowedUsersFile(TrackableFile):
    def load(self):
        allowedUsers = []
        if USER_ID == 0:
            try:
                mtime = os.stat(self.path)[stat.ST_MTIME]
                st = open(self.path, "r").read()
                for line in st.split("\n"):
                    line = line.strip()
                    if line.startswith("#") or line == "":
                        continue
                    userName = line
                    if userName != "":
                        allowedUsers.append(userName)
                logLoadAllow()
            except Exception, detail:
                logMessage("error", "Cannot load allow file (%s)." % self.path)
        else:
            allowedUsers = [ USER_NAME ]

        self.contents = allowedUsers
        self.mtime = mtime

class SignalHome(TrackableFile):
    def load(self):
        try:
            self.mtime = os.stat(self.path)[stat.ST_MTIME]
        except Exception, detail:
            logMessage("error", "Cannot stat signal directory (%s)." % self.path)
            raise

class PidFile:
    def __init__(self, path):
        self.path = path

    def create(self):
        try:
            pid = open(self.path, "r").read()
            logMessage("error", "Cannot create pid file (%s)." % self.path)
        except Exception, detail:
            logMessage("info", "Creating pid file (%s)." % self.path)
            pid = os.getpid()
            open(self.path, "w").write("%s" % pid)
        return int(pid)

    def remove(self):
        try:
            logMessage("info", "Removing pid file (%s)." % self.path)
            os.remove(self.path)
        except Exception, detail:
            logMessage("error", "Cannot remove pid file (%s)." % self.path)
