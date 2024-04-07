#===============================================================================
# MODULE simexception
#
# Copyright (C) 2014-2016 Howard Klein - All Rights Reserved
#
# Defines simulation exception classes.
#===============================================================================
__all__ = ['SimException', 'SimError', 'SimInterruptException',
           'SimResourcePreemptionException', 'SimTimeOutException']
from simprovise.core.apidoc import apidoc, apidocskip

@apidoc
class SimException(Exception):
    """
    Base simulation exception class, with message formatting

    Args:
        name (str): Exception name
        desc (str): Exception description
        *args:      Zero or more arguments, embedded into desc via format()
    """
    def __init__(self, name, desc='', *args):
        super().__init__(name, desc, *args)
        self.name_ = name
        try:
            self.desc_ = desc.format(*args)
        except IndexError:
            self.desc_ = desc + " (Insufficient number of description parameters)"


@apidoc
class SimError(SimException):
    """
    Subclass of SimException for simulation errors.
    """
    def __str__(self):
        return 'SimException Error (' + self.name_ +'): ' + self.desc_


@apidoc
class SimInterruptException(Exception):
    """
    Exception raised when a transaction wait is interrupted or otherwise ended
    prematurely and abnormally.  The interrupter may provide a reason.
    """
    def __init__(self, reason=None):
        super().__init__(reason)
        self.reason = reason

    def __str__(self):
        return 'SimInterruptException {0}'.format(self.reason)


@apidoc
class SimResourcePreemptionException(SimInterruptException):
    """
    Exception invoked when a wait is interrupted due to resource preemption
    """

@apidoc
class SimTimeOutException(SimInterruptException):
    """
    Exception invoked when a wait is interrupted due to a timeout (e.g.
    resource not acquired within specified time limit)
    """