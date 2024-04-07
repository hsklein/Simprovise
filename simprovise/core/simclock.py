#===============================================================================
# MODULE simclock
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimClock class, which functions as a namespace for (static)
# methods that access/manipulate the global simulation clock.
#
# TODO The global simulation clock unit is SECONDS.  Should eventually allow
# for that to be configurable by the simulation model.
#===============================================================================
__all__ = ['SimClock']

from simprovise.core import simtime, SimTime, SimError
from simprovise.core.apidoc import apidoc, apidocskip

@apidoc
class SimClock(object):
    """
    SimClock defines a set of static methods that access and/or update
    the global simulation clock.
    """
    # _currentTime is the current simulated clock time
    _currentTime = SimTime(0, simtime.SECONDS)

    @staticmethod
    @apidocskip
    def initialize():
        """
        (Re)set the simulated clock to zero.
        TODO allow time unit to be specified.
        """
        SimClock._currentTime = simtime.SimTime(0, simtime.SECONDS)

    @staticmethod
    def units():
        """
        Return the unit value of the simulated clock - useful for defaults
        """
        return SimClock._currentTime.units

    @staticmethod
    def now():
        """
        Return a copy of (not reference to) the current simulated clock time.

        The copy ensures that client does not accidentally modify the clock
        by incrementing, decrementing or explicitly modifying attributes of
        the return value of now()

        Returns:
            SimTime: the current simulated clock time
        """
        return SimClock._currentTime.makeCopy()

    @staticmethod
    @apidocskip
    def advanceTo(newTime):
        """
        Advance the simulation clock to the specified new time.  (New time
        must be greater than or equal to the current time)
        """
        if newTime >= SimClock._currentTime:
            # ensure that we keep currentTime's units - otherwise we could just copy
            # newTime
            SimClock._currentTime = simtime.SimTime(0, simtime.SECONDS) + newTime
        else:
            errMsg = "Attempt to advance clock from {0} to {1}"
            raise SimError('InvalidClockAdvance', errMsg, SimClock._currentTime, newTime)


