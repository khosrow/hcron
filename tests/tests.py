#! /usr/bin/env python
#
# x.py

from hcron.library import listStToBitmask, WHEN_BITMASKS, WHEN_MIN_MAX

print listStToBitmask("*/2", WHEN_MIN_MAX.get("when_month"), WHEN_BITMASKS.get("when_month"))
print listStToBitmask("1-4/2", WHEN_MIN_MAX.get("when_month"), WHEN_BITMASKS.get("when_month"))
print listStToBitmask("1-4/2", WHEN_MIN_MAX.get("when_month"), WHEN_BITMASKS.get("when_month"))
print listStToBitmask("*/2", WHEN_MIN_MAX.get("when_hour"), WHEN_BITMASKS.get("when_hour"))
print listStToBitmask("0-23/2", WHEN_MIN_MAX.get("when_hour"), WHEN_BITMASKS.get("when_hour"))
print listStToBitmask("0-23/2", WHEN_MIN_MAX.get("when_hour"), WHEN_BITMASKS.get("when_hour"))
print listStToBitmask("0-2/2,4-5", WHEN_MIN_MAX.get("when_hour"), WHEN_BITMASKS.get("when_hour"))

