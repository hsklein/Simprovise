#===============================================================================
# MODULE crcutils
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Utility function to calculate CRC checksum for a file, in order to test
# output file generation functions.
#===============================================================================
import zlib

def crc32(filename):
    """
    Basically lifted from:
    https://stackoverflow.com/questions/1742866/compute-crc-of-file-in-python
    """
    checksum = 0
    with open(filename, 'rb') as f:       
        while True:
            s = f.read(65536)
            if not s:
                break
            checksum = zlib.crc32(s, checksum)
            
    return checksum
