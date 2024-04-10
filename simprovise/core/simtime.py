#===============================================================================
# MODULE simtime
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimTime class and time unit constants
#===============================================================================
__all__ = ['SimTime']

# TODO - recode in terms of builtin timedelta class? - problem is with potential
# customization of day, week and year length.
from simprovise.core import SimError, SimLogging
from simprovise.core.apidoc import apidoc, apidocskip

logger = SimLogging.get_logger(__name__)

# TimeUnit constants
SECONDS = 0
MINUTES = 1
HOURS = 2

_UNITS = (SECONDS, MINUTES, HOURS)
_UNITNAMES = ('second', 'minute', 'hour')

_ERROR_NAME = "SimTime Error"

@apidoc
class SimTime(object):
    """
    A simulated time or interval, in seconds, minutes or hours.

    Args:
        value (scalar or :class:`~.simtime.SimTime`)
        units: Time unit if value is not a :class:`~.simtime.SimTime`
        
    """
    __slots__ = ('_value', '_units')

    def __init__(self, value=0, units=SECONDS):
        if isinstance(value, (int, float)):
            if units in _UNITS:
                self._units = units
            else:
                # TODO Allow units as string
                raise SimError('InvalidSimTimeUnit', 'Invalid time unit: ' + str(units))
            self._value = value
        elif isinstance(value, SimTime):
            # pylint can't grok the idea that value is an int or SimTime
            # pylint: disable=E1101
            self._value = value._value
            self._units = value._units
        else:
            raise SimError('InvalidSimTimeValue', str(value) + ' is an invalid value type: ' + str(type(value)))

    def __str__(self):
        repString = str(self._value) + ' ' + self.unitsString()
        return repString

    def unitsString(self):
        """
        Returns a string representation of the instance's units (singular or
        plural, depending on value)
        """
        if self._value == 1:
            return _UNITNAMES[self._units]
        else:
            return _UNITNAMES[self._units] + 's'


    def getValue(self): return self._value
    def getUnits(self): return self._units

    @property
    def value(self):
        """
        Time scalar value (without units)
        """
        return self._value

    @property
    def units(self):
        """
        Time units
        """
        return self._units

    def makeCopy(self):
        "Make a copy of a time object - cheaper than using the copy module"
        return SimTime(self._value, self._units)

    def toUnits(self, tounits):
        """
        Returns a new SimTime instance of the specified time units
        """
        if tounits in _UNITS:
            conversionFactor = 60**(self._units - tounits)
            return SimTime(self._value * conversionFactor, tounits)
        else:
            msg = "Invalid units constant ({0}) passed to SimTime.toUnits()"
            raise SimError(_ERROR_NAME, msg, tounits)

    def toSeconds(self):
        "Returns a new SimTime instance, in seconds"
        return self.toUnits(SECONDS)

    def toMinutes(self):
        "Returns a new SimTime instance, in minutes"
        return self.toUnits(MINUTES)

    def toHours(self):
        "Returns a new SimTime instance, in hours"
        return self.toUnits(HOURS)

    def seconds(self):
        "Returns the time in seconds - a scalar, not a SimTime"
        conversionFactor = 60**(self._units - SECONDS)
        return self._value * conversionFactor

    #value = property(getValue, None, None, "Time scalar value (without units) - read-only")
    #units = property(getUnits, None, None, "Time units - read-only")

    # Internal helper function used by math operators to convert 'other' interval to same
    # units as self.  If other is NOT a SimTime, we assume the same units as self
    # and just return other (which had better be or convert to a number)
    def _convertedOtherValue(self, other):
        if isinstance(other, self.__class__):
            conversionFactor = 60**(other._units - self._units)
            return other._value * conversionFactor
        else:
            return other

    def __add__(self, other):
        return SimTime(self._value + self._convertedOtherValue(other), self._units)

    def __radd__(self, other):
        return SimTime(self._value + self._convertedOtherValue(other), self._units)

    def __sub__(self, other):
        return SimTime(self._value - self._convertedOtherValue(other), self._units)

    def __iadd__(self, other):
        self._value += self._convertedOtherValue(other)
        return self

    def __truediv__(self, other):
        return SimTime(float(self._value) / self._convertedOtherValue(other), self._units)

    def __rtruediv__(self, other):
        return SimTime(self._convertedOtherValue(other) / float(self._value), self._units)

    def __mul__(self, other):
        return SimTime(self._value * self._convertedOtherValue(other), self._units)

    def __rmul__(self, other):
        return SimTime(self._value * self._convertedOtherValue(other), self._units)

    def _compare(self, other):
        if other == 0:
            return self._value

        if not isinstance(other, self.__class__):
            raise SimError('InvalidSimTimeCompare', 'Cannot compare time interval to ' + str(other))

        otherValue = self._convertedOtherValue(other)
        diff = self._value - otherValue
        return diff

    def __eq__(self, other):
        return self._compare(other) == 0

    def __ne__(self, other):
        return self._compare(other) != 0

    def __lt__(self, other):
        return self._compare(other) < 0

    def __le__(self, other):
        return self._compare(other) <= 0

    def __gt__(self, other):
        return self._compare(other) > 0

    def __ge__(self, other):
        return self._compare(other) >= 0

    def __hash__(self):
        "for hashing, return the time value converted to seconds and truncated, if necessary"
        conversionFactor = 60**(self._units - SECONDS)
        return int(self._value * conversionFactor)

    @apidocskip
    def serialize(self):
        """
        Converts aSimTime value to a (JSON) serializable format -
        tuple('SimTime', value, units)
        """
        return ['SimTime', self.value, self.units]

    @staticmethod
    @apidocskip
    def deserialize(obj):
        """
        If a passed object is of the SimTime serialization format (method above)
        deserialize it to a SimTime object.  Otherwise, return the original object
        """
        # We'll accept both tuples and lists
        if not isinstance(obj, tuple) and not isinstance(obj, list): return obj

        if len(obj) != 3: return obj
        if obj[0] != 'SimTime': return obj
        return SimTime(obj[1], obj[2])

