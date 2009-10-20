#! /usr/bin/env python
#
# execute.py

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

"""Routines for handling command execution.
"""

# system imports
import os
import pwd
import signal
import subprocess

# app imports
from hcron.constants import *
import hcron.globals as globals
from hcron.logger import *

class RemoteExecuteException(Exception):
    pass

def alarmHandler(signum, frame):
    logAlarm()
    os._exit(0)

def __remoteExecute(remoteUserName, remoteHostName, command):
    """Switch to localUserName and remote execute a command at
    remoteUserName@remoteHostName.

    ssh options used with explanations from ssh man page:
    -f              requests ssh to go to background just before
                    command execution (implies -n)
    -l <login_name> specifies the user to log in as on the remote
                    machine              
    -n              redirects stdin from /dev/null (actually, prevents
                    reading from stdin)
    -t              force pseudo-tty allocation
    """
    config = globals.config.get()
    remoteShellType = config.get("remoteShellType", REMOTE_SHELL_TYPE)
    remoteShellExec = config.get("remoteShellExec", REMOTE_SHELL_EXEC)
    if remoteShellType == "ssh":
        args = [ remoteShellExec, "-f", "-t", "-l", remoteUserName, remoteHostName, command ]
    else:
        raise RemoteExecuteException("Unknown remote shell type (%s)." % remoteShellType)

    #args = [ "/bin/sleep", "100" ]
    #logMessage("debug", "args (%s)" % str(args))
    os.execv(args[0], args)

def remoteExecute(eventName, localUserName, remoteUserName, remoteHostName, command):
    """Securely execute a command at remoteUserName@remoteHostName from
    localUserName@localhost.
    """
    config = globals.config.get()

    allowLocalhost = config.get("allowLocalhost", False) 
    if remoteHostName in LOCAL_HOST_NAMES and not allowLocalhost:
        raise RemoteExecuteException("Execution on local host is not allowed.")

    localUid = pwd.getpwnam(localUserName).pw_uid
    if localUid == 0:
        raise RemoteExecuteException("Root user not allowed to execute.")

    logExecute(localUserName, remoteUserName, remoteHostName, eventName)
    if command.strip() != "":
        if os.fork() == 0:
            # child
            try:
                os.setuid(localUid)
                os.setsid()
                commandSpawnTimeout = globals.config.get().get("commandSpawnTimeout", COMMAND_SPAWN_TIMEOUT)
                signal.signal(signal.SIGALRM, alarmHandler)
                signal.alarm(commandSpawnTimeout)
                __remoteExecute(remoteUserName, remoteHostName, command)
            except Exception, detail:
                logMessage("error", "Execute failed  (%s)." % detail)

            os._exit(0)

    # parent

