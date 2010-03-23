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
import time

# app imports
from hcron.constants import *
import hcron.globals as globals
from hcron.logger import *

# global
childPid = None

class RemoteExecuteException(Exception):
    pass

def alarm_handler(signum, frame):
    global childPid

    log_alarm()
    os.kill(childPid, signal.SIGKILL)

def remote_execute(eventName, localUserName, remoteUserName, remoteHostName, command, timeout=None):
    """Securely execute a command at remoteUserName@remoteHostName from
    localUserName@localhost within timeout time.

    Two approaches are coded below:
        1) poll+sleep
        2) signal+wait

    childPid is a module global, accessible to the alarm_handler.

    Return values:
    0   okay
    -1  error/failure
    """
    global childPid

    # setup
    config = globals.config.get()
    allowLocalhost = config.get("allowLocalhost", False) 
    localUid = pwd.getpwnam(localUserName).pw_uid
    remoteShellType = config.get("remoteShellType", REMOTE_SHELL_TYPE)
    remoteShellExec = config.get("remoteShellExec", REMOTE_SHELL_EXEC)
    timeout = timeout or globals.config.get().get("commandSpawnTimeout", COMMAND_SPAWN_TIMEOUT)
    command = command.strip()

    # validate
    if remoteHostName in LOCAL_HOST_NAMES and not allowLocalhost:
        raise RemoteExecuteException("Execution on local host is not allowed.")

    if localUid == 0:
        raise RemoteExecuteException("Root user not allowed to execute.")

    if remoteShellType != "ssh":
        raise RemoteExecuteException("Unknown remote shell type (%s)." % remoteShellType)

    # spawn
    retVal = -1
    if command != "":
        try:
            args = [ remoteShellExec, "-f", "-t", "-l", remoteUserName, remoteHostName, command ]
            childPid = os.fork()

            if childPid == 0:
                #
                # child
                #
                try:
                    os.setuid(localUid)
                    os.setsid()
                    os.execv(args[0], args)
                    #retVal = subprocess.call(args)
                except (OSError, Exception), detail:
                    os._exit(256)
                    retVal = 256

                os._exit(retVal)

                # NEVER REACHES HERE

            #
            # parent
            #
            if 0:
                # poll and wait
                while timeout > 0:
                    waitPid, waitStatus = os.waitpid(childPid, os.WNOHANG)

                    #if waitPid != 0 and os.WIFEXITED(waitStatus):
                    if waitPid != 0:
                        break

                    time.sleep(0.01)
                    timeout -= 0.01

                else:
                    os.kill(childPid, signal.SIGKILL)

            else:
                # signal and wait
                signal.signal(signal.SIGALRM, alarm_handler)
                signal.alarm(timeout)
                waitPid, waitStatus = os.waitpid(childPid, 0)
                signal.signal(signal.SIGALRM, signal.SIG_IGN) # cancel alarm

            if os.WIFSIGNALED(waitStatus):
                retVal = -1

            elif os.WIFEXITED(waitStatus):
                retVal = (os.WEXITSTATUS(waitStatus) == 255) and -1 or 0

        except Exception, detail:
            log_message("error", "Execute failed (%s)." % detail)

    log_execute(localUserName, remoteUserName, remoteHostName, eventName, retVal)

    return retVal

