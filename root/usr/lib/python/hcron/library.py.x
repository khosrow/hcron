#! /usr/bin/env python
#
# library.py

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
import logging
import os
import os.path
import pwd
import resource
import signal
import smtplib
import socket
import subprocess

# app imports
from hcron.constants import *
import hcron.globals as globals
from hcron.safeeval import safe_eval

#
# using bitmasks makes for easy comparisons (bitwise-and), but caution
# must be taken to account for different minimum values for each of the
# datetime components: 0 (hour, minute, dow), 1 (month, day). Thus, the
# for the 1 minimum components, the rightmost position is wasted.
#
WHEN_BITMASKS = {
    "when_month": 2**13-1,
    "when_day": 2**32-1,
    "when_hour": 2**25-1,
    "when_minute": 2**61-1,
    "when_dow": 2**8-1,
}

WHEN_INDEX = {
    "when_month": 0,
    "when_day": 1,
    "when_hour": 2,
    "when_minute": 3,
    "when_dow": 4,
}

def dateToBitmasks(*m_d_h_m_dow):
    datemasks = [ 2**x for x in m_d_h_m_dow ]
    return datemasks

    datemasks = {}
    for i in xrange(len(m_d_h_m_dow)):
        datemasks[i] = 2**(m_d_h_m_dow[i]-1)
    return datemasks
    
def listStToBitmask(st, fullBitmask):
    mask = 0
    for el in st.split(","):
        if el == "*":
            mask = fullBitmask
        else:
            mask |= 2**int(el)
    return mask

def setupLogger():
    config = globals.config.get()
    if config.get("useSyslog", False):
        handler = logging.SysLogHandler()
    else:
        logPath = config.get("logPath", HCRON_LOG_PATH)
        if not logPath.startswith("/"):
            logPath = os.path.join(HCRON_LOG_HOME, logPath)
        handler = logging.FileHandler(logPath)
    globals.logger = logging.getLogger("")
    globals.logger.addHandler(handler)
    globals.logger.setLevel(logging.INFO)
    globals.logger.info("Starting hcron logging...")

class RemoteExecuteException(Exception):
    pass

def sendEmailNotification(fromUserName, toAddr, subject, content):
    globals.logger.info("sendEmailNotification")
    config = globals.config.get()
    smtpServer = config.get("smtpServer", "localhost")

    globals.logger.info("smtpServer (%s)" % smtpServer)

    fromAddr = "%s@%s" % (fromUserName, HOST_NAME)
    message = """From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n%s""" % \
        (fromAddr, toAddr, subject, content)
    #globals.logger.info("message (%s)" % message)
    try:
        m = smtplib.SMTP(smtpServer)
        m.sendmail(fromAddr, toAddr, message)
        m.quit()
        globals.logger.info("Email sent from (%s) to (%s)" % (fromAddr, toAddr))
    except Exception, detail:
        globals.logger.info("problem sending email (%s)" % detail)
        pass

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

    args = [ "sleep", "10" ]
    globals.logger.info("args (%s)" % str(args))
    os.execv(args[0], args)

def remoteExecute(localUserName, remoteUserName, remoteHostName, command):
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

    if os.fork() == 0:
        # child
        try:
            os.setuid(localUid)
            os.setsid()
            commandSpawnTimeout = globals.config.get().get("commandSpawnTimeout", COMMAND_SPAWN_TIMEOUT)
            resource.setrlimit(resource.RLIMIT_CPU, (commandSpawnTimeout, commandSpawnTimeout))
            __remoteExecute(remoteUserName, remoteHostName, command)
        except Exception, detail:
            globals.logger.info("Failed to call (%s)." % detail)
            pass

        os._exit(0)

    # parent

