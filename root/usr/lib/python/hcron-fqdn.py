#! /usr/bin/env python
#
# hcron-fqdn.py

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

"""Simply print the fully qualified host name of the executing machine.
"""

# system imports
import socket

if __name__ == "__main__":
    try:
        print socket.getfqdn()
    except Exception, detail:
        print "Error: Could not determine the fully qualified host name."
        sys.exit(-1)
