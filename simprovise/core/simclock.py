#===============================================================================
# MODULE simclock
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimClock class, which functions as a namespace for (static)
# methods that access/manipulate the global simulation clock.
#
# This program is free software: you can redistribute it and/or modify it under 
# the terms of the GNU General Public License as published by the Free Software 
# Foundation, either version 3 of the License, or (at your option) any later 
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT 
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#===============================================================================
__all__ = ['SimClock']

from simprovise.core import simtime, SimError
from simprovise.core.simtime import SimTime, Unit as tu
from simprovise.core.apidoc import apidoc, apidocskip

@apidoc
class SimClock(object):
    """
    SimClock defines a set of static methods that access and/or update
    the global simulation clock. The methods that update or modify the
    clock's state should be called only by the simulation infrastructure,
    *NOT* modeling code.
    """
    # _currentTime is the current simulated clock time
    _currentTime = SimTime(0)
    _clockTimeUnit = None

    @staticmethod
    @apidocskip
    def initialize():
        """
        (Re)set the simulated clock to zero. Use the base unit.
        """
        SimClock._currentTime = SimTime(0)
        SimClock._clockTimeUnit = simtime.base_unit()

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
            SimClock._currentTime = newTime.to_units(SimClock._clockTimeUnit)
        else:
            errMsg = "Attempt to advance clock from {0} to {1}"
            raise SimError('InvalidClockAdvance', errMsg, SimClock._currentTime, newTime)


