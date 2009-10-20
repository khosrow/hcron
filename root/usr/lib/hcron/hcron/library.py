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
import os.path

# app imports
from hcron.constants import *
import hcron.globals as globals

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

WHEN_INDEXES = {
    "when_month": 0,
    "when_day": 1,
    "when_hour": 2,
    "when_minute": 3,
    "when_dow": 4,
}

# ignore wasted 0 as required
WHEN_MIN_MAX = {
    "when_month": (1, 12),
    "when_day": (1, 31),
    "when_hour": (0, 23),
    "when_minute": (0, 59),
    "when_dow": (0, 6),
}

def dateToBitmasks(*m_d_h_m_dow):
    datemasks = [ 2**x for x in m_d_h_m_dow ]
    return datemasks

    datemasks = {}
    for i in xrange(len(m_d_h_m_dow)):
        datemasks[i] = 2**(m_d_h_m_dow[i]-1)
    return datemasks
    
def listStToBitmask(st, minMax, fullBitmask):
    mask = 0
    mn, mx = minMax
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
                low, hi = minMax
            else:
                l = rng.split("-", 1)
                low = int(l[0])
                if len(l) == 1:
                    hi = low
                else:
                    hi = int(l[1])
            if low < mn or hi > mx:
                raise Exception("Out of range.")
            values = range(low, hi+1, step)

            for el in values:
                mask |= 2**int(el)

        if mask == fullBitmask:
            break

    return mask
