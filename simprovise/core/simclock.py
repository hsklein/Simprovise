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

from simprovise.core import simtime, SimError
from simprovise.core.simtime import SimTime, Unit as tu
from simprovise.core.apidoc import apidoc, apidocskip

@apidoc
class SimClock(object):
    """
    SimClock defines a set of static methods that access and/or update
    the global simulation clock.
    """
    # _currentTime is the current simulated clock time
    _currentTime = SimTime(0, tu.SECONDS)

    @staticmethod
    @apidocskip
    def initialize():
        """
        (Re)set the simulated clock to zero.
        TODO allow time unit to be specified.
        """
        SimClock._currentTime = SimTime(0, tu.SECONDS)

    @staticmethod
    def now():
        """
        Return a copy of (not reference to) the current simulated clock time.

        The copy ensures that client does not accidentally modify the clock
        by incrementing, decrementing or explicitly modifying attributes of
        the return value of now()
        
        :return: The current simulated clock time
        :rtype:  :class:`~.simtime.SimTime`

        """
        return SimClock._currentTime.make_copy()

    @staticmethod
    @apidocskip
    def advance_to(newTime):
        """
        Advance the simulation clock to the specified new time.  (New time
        must be greater than or equal to the current time)
        """
        if newTime >= SimClock._currentTime:
            # ensure that we keep currentTime's units - otherwise we could just copy
            # newTime
            SimClock._currentTime = simtime.SimTime(0, tu.SECONDS) + newTime
        else:
            errMsg = "Attempt to advance clock from {0} to {1}"
            raise SimError('InvalidClockAdvance', errMsg, SimClock._currentTime, newTime)


