#! /usr/bin/env python
#
# library.py

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

"""Library of routines, classes, etc. for hcron.
"""

# system imports
import os.path

# app imports
from hcron.constants import *
import hcron.globals as globals

#
# bitmasks makes for easy comparisons (bitwise-and), where each value
# is a bit (e.g., 0-5/2 == 0, 2, 4 -> 0b010101). further all ranges
# are adjusted to start at 0 (e.g., 2009-2012 -> 0-3)
#

WHEN_NAMES = [ "when_year", "when_month", "when_day", "when_hour", "when_minute", "when_dow" ]
WHEN_INDEXES = dict([ (key, i) for i, key in enumerate(WHEN_NAMES) ])

# ignore wasted 0 as required
WHEN_MIN_MAX = {
    "when_year": (2000, 2050),
    "when_month": (1, 12),
    "when_day": (1, 31),
    "when_hour": (0, 23),
    "when_minute": (0, 59),
    "when_dow": (0, 6),
}

WHEN_BITMASKS = dict([(key, 2**(mx-mn+1)-1) for key, (mn,mx) in WHEN_MIN_MAX.items() ])

def date_to_bitmasks(*y_m_d_h_m_dow):
    """Mark the bit positions for year, month, day, etc.
    """
    datemasks = []
    for i, whenName in enumerate(WHEN_NAMES):
        mn, mx = WHEN_MIN_MAX[whenName]
        datemasks.append(2**(y_m_d_h_m_dow[i]-mn))
    return datemasks

    # no when_year
    datemasks = [ 2**x for x in m_d_h_m_dow ]
    return datemasks

    datemasks = {}
    for i in xrange(len(m_d_h_m_dow)):
        datemasks[i] = 2**(m_d_h_m_dow[i]-1)
    return datemasks
    
def list_st_to_bitmask(st, minMax, fullBitmask):
    """Using offset allows one to support small, but arbitrary ranges
    as bitmasks. The following is easier to understand for offset==0
    (e.g., hours, minutes, seconds).
    """
    mask = 0
    mn, mx = minMax
    offset, mn, mx = mn, 0, mx-mn   # index everything to 0

    #print "offset (%s) mn (%s) mx (%s) minMax (%s)" % (offset, mn, mx, minMax)
    for el in st.split(","):
        if el == "*":
            mask = fullBitmask
        else:
            l = el.split("/", 1)
            if len(l) == 1:
                step = 1
                rng = l[0]
            else:
                rng, step = l
                step = int(step)

            if rng == "*":
                low, hi = mn, mx
            else:
                l = rng.split("-", 1)
                low = int(l[0])-offset
                if len(l) == 1:
                    hi = low
                else:
                    hi = int(l[1])-offset
            if low < mn or hi > mx:
                raise Exception("Out of range.")
            values = range(low, hi+1, step)

            for el in values:
                mask |= 2**int(el)

        if mask == fullBitmask:
            break

    return mask

# hcron-specific signature
def dir_walk(top, topdown=True, onerror=None, ignoreMatchFn=None):
    """This is a slightly modified version of os.walk (python v2.4).
    """
    from os.path import join, isdir, islink
    from os import listdir
    from posix import error

    try:
        names = listdir(top)
    except error, err:
        if onerror is not None:
            onerror(err)
        return

    # hcron-specific
    if ignoreMatchFn != None:
        names = [ name for name in names if not ignoreMatchFn(name) ]

    dirs, nondirs = [], []
    for name in names:
        if isdir(join(top, name)):
            dirs.append(name)
        else:
            nondirs.append(name)

    if topdown:
        yield top, dirs, nondirs
    for name in dirs:
        path = join(top, name)
        if not islink(path):
            for x in dir_walk(path, topdown, onerror, ignoreMatchFn):
                yield x
    if not topdown:
        yield top, dirs, nondirs

def copytree(src, dst, srcUid):
    """This is a modified version of shutil.copytree (python v2.6).
    * copier is owner
    * no stat information retained
    * symlinks are converted to (copyof) files
    * an error raises an exception
    """
    from os import listdir, makedirs
    from shutil import copy2

    makedirs(dst)

    try:
        for name in listdir(src):
            src2 = os.path.join(src, name)
            dst2 = os.path.join(dst, name)

            if os.path.isdir(src2):
                copytree(src2, dst2)
            else:
                seteuid(srcUid)
                x = open(src2, "r").read(CONFIG_MAX_EVENT_FILE_SIZE)
                seteuid(0)
                if len(x) < 5000:
                    open(dst2, "w+").write(x)
    except:
        seteuid(0)

def get_events_home(userName):
    """Returns the user-specific events/ directory path.
    """
    config = globals.config.get()
    eventsBasePath = (config.get("eventsBasePath") or "").strip()

    if eventsBasePath == "":
        path = os.path.expanduser("~%s/.hcron/%s/events" % (userName, HOST_NAME))
    else:
        path = os.path.join(eventsBasePath, userName, ".hcron/%s/events" % HOST_NAME)

    if path.startswith("~"):
        return None

    return path

def get_includes_home(userName):
    """Returns the user-specific includes/ directory path.
    """
    config = globals.config.get()
    eventsBasePath = (config.get("eventsBasePath") or "").strip()

    if eventsBasePath == "":
        path = os.path.expanduser("~%s/.hcron/%s/includes" % (userName, HOST_NAME))
    else:
        path = os.path.join(eventsBasePath, userName, ".hcron/%s/includes" % HOST_NAME)

    if path.startswith("~"):
        return None

    return path
    
def get_events_home_snapshot(userName):
    path = os.path.join(HCRON_EVENTS_SNAPSHOT_HOME, userName)

    return path
