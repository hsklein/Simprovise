"""
testutils - utility functions, classes for model testing
"""

import simtime

def fixedSimTimeGenerator(timelist, timeunits):
    while True:
        for t in timelist:
            yield simtime.SimTime(t, timeunits)
