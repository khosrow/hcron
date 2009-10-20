#! /usr/bin/env python
#
# constants.py

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

"""Constants.
"""

# system imports
import os.path
import pwd
import socket
import sys

# constants
PROG_NAME = os.path.basename(sys.argv[0])

HCRON_HOME = os.path.realpath(os.path.join(os.path.dirname(sys.argv[0]), "..", ".."))
if HCRON_HOME.startswith("/usr"):
    HCRON_ETC_PATH = "/etc/hcron"
    HCRON_VAR_PATH = "/var"
else:
    HCRON_ETC_PATH = os.path.join(HCRON_HOME, "etc/hcron")
    HCRON_VAR_PATH = os.path.join(HCRON_HOME, "var")
# etc
HCRON_CONFIG_PATH = os.path.join(HCRON_ETC_PATH, "hcron.conf")
HCRON_ALLOW_PATH = os.path.join(HCRON_ETC_PATH, "hcron.allow")
# var/lib
HCRON_LIB_HOME = os.path.join(HCRON_VAR_PATH, "lib/hcron")
HCRON_ALLOWED_USERS_DUMP_PATH = os.path.join(HCRON_LIB_HOME, "allowedUsers.dump")
HCRON_CONFIG_DUMP_PATH = os.path.join(HCRON_LIB_HOME, "config.dump")
HCRON_EVENTS_DUMP_PATH = os.path.join(HCRON_LIB_HOME, "events.dump")
# var/log
HCRON_LOG_HOME = os.path.join(HCRON_VAR_PATH, "log/hcron")
HCRON_LOG_PATH = os.path.join(HCRON_LOG_HOME, "hcron.log")
# var/spool
HCRON_SPOOL_PATH = os.path.join(HCRON_VAR_PATH, "spool/hcron")
HCRON_SIGNAL_HOME = HCRON_SPOOL_PATH

HCRON_PID_FILE_PATH = os.path.join(HCRON_VAR_PATH, "run/hcron.pid")

HCRON_EVENT_DEFINITION_NAMES = [
    "as_user",
    "host",
    "command",
    "notify_email",
    "notify_message",
    "when_month",
    "when_day",
    "when_hour",
    "when_minute",
    "when_dow",
    "template_name",
]

HCRON_EVENT_DEFINITION = "\n".join([ "%s=" % name for name in HCRON_EVENT_DEFINITION_NAMES ])
HCRON_EVENT_DEFINITION_MAP = dict([ (name, "") for name in HCRON_EVENT_DEFINITION_NAMES ])

REMOTE_SHELL_TYPE = "ssh"
REMOTE_SHELL_EXEC = "/usr/bin/ssh"

COMMAND_SPAWN_TIMEOUT = 15
MAX_EVENTS_PER_USER = 25

MONTH_NAMES_MAP = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

DOW_NAMES_MAP = {
    "sun": 0,
    "mon": 1,
    "tue": 2,
    "wed": 3,
    "thu": 4,
    "fri": 5,
    "sat": 6,
}

CRONTAB_ALIASES_MAP = {
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
    "@monthly": "0 0 1 * *",
    "@weekly": "0 0 * * 0",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@hourly": "0 * * * *",
}

# at invocation
USER_ID = os.getuid()
USER_NAME = pwd.getpwuid(USER_ID).pw_name
HOST_NAME = socket.getfqdn()
SHORT_HOST_NAME = socket.gethostname()
LOCAL_HOST_NAMES = {
    "localhost": None,
    HOST_NAME: None,
    SHORT_HOST_NAME: None,
}

