#! /usr/bin/env python
#
# logger.py

"""This module provide routines for all supported logging operations.
"""

# system imports
from datetime import datetime
import logging

# app imports
from hcron.constants import *
import hcron.globals as globals

# globals
logger = None

def setupLogger():
    global logger

    config = globals.config.get()
    if config.get("useSyslog", False):
        handler = logging.SysLogHandler()
    else:
        logPath = config.get("logPath", HCRON_LOG_PATH)
        if not logPath.startswith("/"):
            logPath = os.path.join(HCRON_LOG_HOME, logPath)
        handler = logging.FileHandler(logPath)
    logger = logging.getLogger("")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info("Starting hcron logging...")

def getDatestamp():
    return datetime.today().isoformat()

def logAny(*args):
    """Get around chicken and egg problem with logger.
    """
    global logger, logAny

    if logger:
        logAny = logAny2

def logAny2(op, userName="", *args):
    global logger

    if args:
        extra = ":".join([ str(el) for el in args ])
    else:
        extra = ""
    logger.info("%s:%s:%s:%s" % (getDatestamp(), op, userName, extra))

def logMessage(typ, msg):
    logAny("message", "", typ, msg)

def logStart():
    logAny("start")

def logEnd():
    logAny("end")

def logLoadConfig():
    logAny("load-config")

def logLoadAllow():
    logAny("load-allow")

def logLoadEvents(userName, count, elapsed):
    logAny("load-events", userName, count, elapsed)

def logDiscardEvents(userName, count):
    logAny("discard-events", userName, count)

def logExecute(userName, asUser, host, eventName):
    logAny("execute", userName, asUser, host, eventName)

def logAlarm():
    logAny("alarm")

def logNotifyEmail(userName, addrs, eventName):
    logAny("notify-email", userName, addrs, eventName)

def logWork(count, elapsed):
    logAny("work", "", count, elapsed)

def logSleep(seconds):
    logAny("sleep", "", seconds)
