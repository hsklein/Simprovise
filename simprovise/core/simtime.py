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
_base_unit = SECONDS

_ERROR_NAME = "SimTime Error"

def base_unit():   
    """
    Return the base time unit for the model (SECONDS, MINUTES, HOURS)
    or None if simulated time for the model is dimensionless.
    
    This unit will be used for all database datasinks, and all simulated
    time output data will be converted to this unit before being
    written/stored by the output datasinks.
    
    :return: The base time unit or None if dimensionless
    :rtype:  simttime.SECONDS, simtime.MINUTES, simtime.HOURS or None
    """
    return _base_unit

def set_base_unit(unit):
    """
    Set the base unit for the model (SECONDS, MINUTES, HOURS) or None if
    simulated time for the model is dimensionless.
    
    TODO base_unit should probably be set tablevia environment variable
    and/or configuration file upon first call to base_unit()
    
    Regardless, changing the base_unit in code must be done carefully. Changing from a
    dimensioned base time unit (seconds, minutes or hours) to a dimension
    less setting is particularly fraught, since we cannot convert a SimTime
    object from one to the other.
    
    :param unit: simttime.SECONDS, simtime.MINUTES, simtime.HOURS or None
    :type unit:  int (range 0-2)
    """
    global _base_unit
    if unit in _UNITS or unit is None:
        _base_unit = unit
    else:
        msg = "Invalid unit {0} passed to set_base_unit - must be SECONDS, MINUTES, HOURS or None"
        raise SimError(_ERROR_NAME, msg, unit)

@apidoc
class SimTime(object):
    """
    A simulated time or interval; may be either dimensionless or in
    seconds, minutes or hours.
    
    The class also supports SimTime object arithmetic - adding/subtracting
    SimTime objects, multiplication/division of SimTime objects
    by a scalar, adding/subtracting scalars to/from a SimTime object. (The
    scalar is implicitly assumed to be in the units of the added-to
    SimTime)

    :param value: A numeric time length or another SimTime object
    :type value:  Numeric scalar or :class:`~.simtime.SimTime`
    
    :param units: Time unit (simtime.SECONDS, simtime.MINUTES or
                  simtime.HOURS) or None. If value is a
                  :class:`~.simtime.SimTime`, this is ignored.
                  If :func:`base_unit` is None (dimensionless), this
                  must be None. If the base_unit is set,
                  SECONDS/MINUTES/HOURS may be specified; with None
                  it will default to the base_unit
    :type units:  int (range 0-2) or None
                
    """
    __slots__ = ('_value', '_units')
    
    def __init__(self, value=0, units=None):
        if isinstance(value, (int, float)):
            # default units to the base unit if parameter not specified or None
            # Of course if the base unit is None (dimensionless time), that's
            # what we'll set.
            if units is None:
                units = _base_unit
            if units in _UNITS or units is None:
                self._units = units
            else:
                # TODO Allow units as string
                msg = "Invalid SimTime time unit passed to initializer: {0}"
                raise SimError(_ERROR_NAME, msg, units)
            self._value = value
        elif isinstance(value, SimTime):
            # validate and raise if invalid
            self._validate_units(value)                
            # pylint can't grok the idea that value is an int or SimTime
            # pylint: disable=E1101
            self._value = value._value
            self._units = value._units
        else:
            msg = "SimTime time value ({0}) in an invalid type {1}"
            raise SimError(_ERROR_NAME, msg, value, type(value))
        
    def _validate_units(self, simtime_obj):
        """
        Raise a SimError if a passed SimTime object has an invalid units member
        value. That member value must be None if the base unit is None (dimensionless)
        and a valid time unit (SECONDS, MINUTES or HOURS) otherwise.
        """
        units = simtime_obj.units
        if _base_unit is None:
            if units is not None:
                msg = "Cannot user or set the units ({0}) for a SimTime when the base time unit is None (dimensionless)"
                raise SimError(_ERROR_NAME, msg, units)
            else:
                return
        
        if not units in _UNITS:
            msg = "Invalid SimTime units ({0}) specified"
            raise SimError(_ERROR_NAME, msg, units)
 
    def __str__(self):
        repString = str(self._value) + ' ' + self.units_string()
        return repString

    def units_string(self):
        """
        Returns a string representation of the instance's units (singular or
        plural, depending on value)
        """
        if self._units is None:
            return ''
        elif self._units not in _UNITS:
            return 'Invalid Units'
        elif self._value == 1:
            return _UNITNAMES[self._units]
        else:
            return _UNITNAMES[self._units] + 's'

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

    def make_copy(self):
        "Make a copy of a time object - cheaper than using the copy module"
        return SimTime(self._value, self._units)

    def to_units(self, tounits):
        """
        Returns a new SimTime instance of the specified time units
        """
        if tounits in _UNITS:
            conversionFactor = 60**(self._units - tounits)
            return SimTime(self._value * conversionFactor, tounits)
        else:
            msg = "Invalid units constant ({0}) passed to SimTime.toUnits()"
            raise SimError(_ERROR_NAME, msg, tounits)

    def to_seconds(self):
        "Returns a new SimTime instance, in seconds"
        return self.to_units(SECONDS)

    def to_minutes(self):
        "Returns a new SimTime instance, in minutes"
        return self.to_units(MINUTES)

    def to_hours(self):
        "Returns a new SimTime instance, in hours"
        return self.to_units(HOURS)
    
    def to_scalar(self):
        """
        Returns the SimTime's scalar value, converted to :func:base_unit
        e.g., if the base unit is SECONDS and this SimTime is 2 minutes,
        (value 2, units MINUTES) to_scalar() returns 120
        """
        if _base_unit is None:
            assert self._units is None, "SimTime units set when base unit is None/Dimensionless"
            return self._value
        else:
            conversionFactor = 60**(self._units - _base_unit)
            return self._value * conversionFactor
            

    # Internal helper function used by math operators to convert 'other' interval to same
    # units as self.  If other is NOT a SimTime, we assume the same units as self
    # and just return other (which had better be or convert to a number)
    def _converted_other_value(self, other):
        if isinstance(other, self.__class__):
            self._validate_units(other)
            self._validate_units(self)
            if other._units is None:
                return other._value
            else:
                conversionFactor = 60**(other._units - self._units)
                return other._value * conversionFactor
        else:
            return other

    # Methods below all support SimTime arithmetic
    
    def __add__(self, other):
        return SimTime(self._value + self._converted_other_value(other), self._units)

    def __radd__(self, other):
        return SimTime(self._value + self._converted_other_value(other), self._units)

    def __sub__(self, other):
        return SimTime(self._value - self._converted_other_value(other), self._units)

    def __iadd__(self, other):
        self._value += self._converted_other_value(other)
        return self

    def __truediv__(self, other):
        return SimTime(float(self._value) / self._converted_other_value(other), self._units)

    def __rtruediv__(self, other):
        return SimTime(self._converted_other_value(other) / float(self._value), self._units)

    def __mul__(self, other):
        return SimTime(self._value * self._converted_other_value(other), self._units)

    def __rmul__(self, other):
        return SimTime(self._value * self._converted_other_value(other), self._units)

    def _compare(self, other):
        if other == 0:
            # Validate this SimTime (mostly for a change to dimensionless base unit)
            # before returning
            self._validate_units(self)
            return self._value

        if _base_unit is not None and not isinstance(other, self.__class__):
            msg = "Cannot compare time interval to ({0})"
            raise SimError(_ERROR_NAME, msg, other)

        otherValue = self._converted_other_value(other)
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

