#! /usr/bin/env python
#
# x.py

from hcron.library import listStToBitmask, WHEN_BITMASKS, WHEN_MIN_MAX

print bin(listStToBitmask("2009", WHEN_MIN_MAX.get("when_year"), WHEN_BITMASKS.get("when_year")))
print bin(listStToBitmask("*/2", WHEN_MIN_MAX.get("when_month"), WHEN_BITMASKS.get("when_month")))
print bin(listStToBitmask("1-4", WHEN_MIN_MAX.get("when_month"), WHEN_BITMASKS.get("when_month")))
print bin(listStToBitmask("1-4/2", WHEN_MIN_MAX.get("when_month"), WHEN_BITMASKS.get("when_month")))
print bin(listStToBitmask("5-12/2", WHEN_MIN_MAX.get("when_month"), WHEN_BITMASKS.get("when_month")))
print bin(listStToBitmask("*/2", WHEN_MIN_MAX.get("when_hour"), WHEN_BITMASKS.get("when_hour")))
print bin(listStToBitmask("0-23/2", WHEN_MIN_MAX.get("when_hour"), WHEN_BITMASKS.get("when_hour")))
print bin(listStToBitmask("0-23/2", WHEN_MIN_MAX.get("when_hour"), WHEN_BITMASKS.get("when_hour")))
print bin(listStToBitmask("0-2/2,4-5", WHEN_MIN_MAX.get("when_hour"), WHEN_BITMASKS.get("when_hour")))

