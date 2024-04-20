#===============================================================================
# MODULE simexception
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines simulation exception classes.
#===============================================================================
__all__ = ['SimException', 'SimError', 'SimInterruptException',
           'SimResourcePreemptionException', 'SimTimeOutException']
from simprovise.core.apidoc import apidoc, apidocskip

@apidoc
class SimException(Exception):
    """
    Base simulation exception class, with message formatting,
    derived from the built-in Exception class.
    
    :param name:  Exception name
    :type name:   `str`
    
    :param desc:  Exception description string
    :type desc:   str`
    
    :param *args: Argument values to be substituted into the
                  description string.

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
    Exception raised when a transaction wait is interrupted or otherwise
    ended prematurely and abnormally.  The interrupter may provide a
    reason. Note that this exception class is NOT derived from
    :class:`SimException`. It is expected for simulation models that
    that encorporate process interruption.
    
    :param reason: Reason for interruption, or None
    :type reason:  `str` or None
    
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