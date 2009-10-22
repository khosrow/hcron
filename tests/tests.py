#! /usr/bin/env python
#
# x.py

from hcron.library import listStToBitmask, WHEN_BITMASKS, WHEN_MIN_MAX

bitMaskTests = [
    (bin(listStToBitmask("2009", WHEN_MIN_MAX.get("when_year"), WHEN_BITMASKS.get("when_year"))), "0b1000000000"),
    (bin(listStToBitmask("*/2", WHEN_MIN_MAX.get("when_month"), WHEN_BITMASKS.get("when_month"))), "0b10101010101"),
    (bin(listStToBitmask("1-4", WHEN_MIN_MAX.get("when_month"), WHEN_BITMASKS.get("when_month"))), "0b1111"),
    (bin(listStToBitmask("1-4/2", WHEN_MIN_MAX.get("when_month"), WHEN_BITMASKS.get("when_month"))), "0b101"),
    (bin(listStToBitmask("5-12/2", WHEN_MIN_MAX.get("when_month"), WHEN_BITMASKS.get("when_month"))), "0b10101010000"),
    (bin(listStToBitmask("*/2", WHEN_MIN_MAX.get("when_hour"), WHEN_BITMASKS.get("when_hour"))), "0b10101010101010101010101"),
    (bin(listStToBitmask("0-23/2", WHEN_MIN_MAX.get("when_hour"), WHEN_BITMASKS.get("when_hour"))), "0b10101010101010101010101"),
    (bin(listStToBitmask("0-23/3", WHEN_MIN_MAX.get("when_hour"), WHEN_BITMASKS.get("when_hour"))), "0b1001001001001001001001"),
    (bin(listStToBitmask("0-2/2,4-5", WHEN_MIN_MAX.get("when_hour"), WHEN_BITMASKS.get("when_hour"))), "0b110101"),
]

for value, expected in bitMaskTests:
    print "%s: value (%s) expected (%s)" % (value == expected and "GOOD" or "FAIL", value, expected)
