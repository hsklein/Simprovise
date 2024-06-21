#===============================================================================
# MODULE counter
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimCounter class.
#===============================================================================
__all__ = ['SimCounter']

import collections, sys
from simprovise.core import SimError
from simprovise.core.simclock import SimClock
from simprovise.core.datacollector import SimTimeWeightedDataCollector
from simprovise.core.simlogging import SimLogging

from simprovise.core.apidoc import apidoc, apidocskip

logger = SimLogging.get_logger(__name__)
_ERROR_NAME = "SimCounter Error"


# TODOs
# 1.  For base case (FIFO increment), should __waitingProcesses be a deque?  (for efficiency) DONE
# 2.  Allow for a client-specified nextprocess() function, which returns an index
#     from _waitingProcesses, indicating the next process to increment (dynamic reprioritization)
#     Default function:  a lambda that returns 0  (FIFO)
#     An alternate would also allow for the return on None, indicating that no
#     process should be allowed to increment right now.  That approach might be
#     used to model a multiple capacity resource going (partially) down.
# 3.  Provide a means to use alternate data structures for __waitingProcesses -
#     e.g. a heap (heapq module) to create priroity queues.  (Under what circumstances -
#     e.g. list/deque size - is that going to create a noticable performance improvement?
# 4.  Consider removing the queue time measurement (or making it configurable) DONE

@apidoc
class SimCounter(object):
    """
    SimCounter implements both infinite and finite capacity counters, and
    collects counter statistics. Primary public methods are :meth:`increment` and
    :meth:`decrement`. increment() calls may block (for simulated time) on finite
    capacity counters, so such increment() calls must also include the
    :class:`~.transaction.SimTransaction` (:class:`~.process.SimProcess`)
    on which the increment is being called - if increment blocks, the
    transaction will be paused, and then resumed once the counter can be
    successfully incremented by the requested amount.

    In most cases, the modeler would like to collect counter values during
    the simulation as part of their output analysis. In order to do that, the
    counter must be assigned to a data collection element object (e.g. resource
    or location) and be associated with a dataset for that element. If
    both `element` and `name` are specified via initializer, that dataset
    will be created (and counter data collected) automatically.

    :param element:   The data collection element object which owns the counter
    :type element:    :class:`~.simelement.SimElement`
    
    :param name:      The name of the dataset containing counter values.
                      Dataset names must be unique within the element.
    :type name:       str
    
    :param capacity:  The capacity of the counter (> 0) or None if the
                      capacity is infinite
    :type capacity:   int  > 0 or None
    
    :param normalize: If True, the time-weighted data collector associated
                      with this counter will collect values normalized into
                      the range (0.0, 1.0) - i.e., the collected values will
                      be the counter value divided by the counter capacity. If 
                      the capacity is infinite or one, normalize is ignored.
    :type normalize:  bool
                      
    """
    infinite = sys.maxsize
    __slots__ = ('__value', '__capacity', '__waitingTransactions',
                 '__datacollector', '__normalize', '__normalizer')

    def __init__(self, element, name, capacity=None, *, normalize=False):
        """
        When normalize is True, the time-weighted data collector associated
        with this counter will collect values normalized into the range (0.0,
        1.0) - i.e., the collected values will be the counter value divided
        by the counter capacity. If the capacity is infinite or one,
        normalize is ignored.
        """
        self.__normalize = normalize
        self.__normalizer = None
        self.__capacity = None
        self.__datacollector = None # needed to set capacity
        if capacity is not None and capacity > 0 and capacity < SimCounter.infinite:
            self.capacity = capacity
        else:
            self.capacity = SimCounter.infinite
        self.__value = 0
        self.__waitingTransactions = collections.deque()
        # TODO should we use a null data collector when element and/or name
        # is null/None?

        # Set up a floating point data collector if normalizing, int if not.
        # Since we don't know the final capacity at this point, we can't
        # use that to determine the collector's type. (if we knew the
        # capacity was one or infinite, we could use an int collector
        # regardless of normalization)
        if normalize:
            self.__datacollector = SimTimeWeightedDataCollector(element, name, float)
        else:
            self.__datacollector = SimTimeWeightedDataCollector(element, name, int)

        self.__datacollector.add_value(0)

        # TODO - Measure queue (wait) size via a member counter?
        # TODO should utilization be tracked as a separate data collector?

    def __str__(self):
        return self.__class__.__name__ + ' ' + str(self.__datacollector.name)

    @property
    def is_infinite(self):
        """
        Returns `True` if the counter has infinite capacity, `False` otherwise.
        """
        return self.__capacity == SimCounter.infinite

    @property
    def capacity(self):
        """
        Returns the (integer) capacity for finite capacity counters, None for
        infinite capacity counters.
        """
        if self.__capacity == SimCounter.infinite:
            return None
        else:
            return self.__capacity

    @capacity.setter
    def capacity(self, value):
        """
        Capacity setter. New value must be a positive integer, or None (which
        will be interpreted as infinite.) Raises on an invalid value. Also
        raises if the counter has already been incremented at least once.
        """
        if value is None:
            value = SimCounter.infinite

        if type(value) is not int:
            errmsg = "Invalid Counter capacity: new value: {0} is not an integer"
            raise SimError(_ERROR_NAME, errmsg, value)

        if value < 1:
            errmsg = "Invalid Counter capacity: new value: {0} is not a positive integer"
            raise SimError(_ERROR_NAME, errmsg, value)

        if self.__datacollector and self.__datacollector.entries() > 1:
            errmsg = "Invalid Counter capacity: new value: {0} cannot be set after the counter is incremented"
            raise SimError(_ERROR_NAME, errmsg, value)

        self.__capacity = value
        if self.__normalize and not self.is_infinite and self.capacity > 1:
            self.__normalizer = self.capacity
        else:
            self.__normalizer = 1

    @property
    def value(self):
        """
        Returns the current counter (integer) value
        """
        return self.__value

    @property
    @apidocskip
    def waiting_transaction_count(self): return len(self.__waitingTransactions)

    def increment(self, txn=None, amount=1):
        """
        Increment the counter by a specified amount, which defaults to one.
        If the counter is of finite capacity, this method will block if the
        requested capacity is not available; for that reason, finite capacity
        counters must be incremented using a :class:`~.transaction.SimTransaction`
        (:class:`~.process.SimProcess`), specified via the txn argument, which will
        get blocked if the requested capacity is not immediately available.

        Blocked increment() requests are fulfilled on a first come/first
        served basis.


        :param txn:    The transaction/process incrementing the counter.
                       Required if the counter has finite capacity.
        :type txn:     :class:`~.transaction.SimTransaction`
 
        :param amount: The amount to increment the counter by. Must be in
                       range (1-counter capacity). Defaults to 1.
        :type amount:  int

        """
        #print("incrementing ", self, self.__datacollector.dataset.element_id)
        if type(amount) is not int:
            errmsg = "Invalid Counter increment: increment amount: {0} is not an integer"
            raise SimError(_ERROR_NAME, errmsg, amount)

        if amount > self.__capacity or amount <= 0:
            errmsg = "Invalid Counter increment: increment amount: {0} capacity: {1}"
            raise SimError(_ERROR_NAME, errmsg, amount, self.__capacity)

        if self.is_infinite and SimCounter.infinite - self.__value <= amount:
            errmsg = "Overflow on infinite capacity counter; current value: {0} increment amount: {1}"
            raise SimError(_ERROR_NAME, errmsg, self.__value, amount)

        if not txn and not self.is_infinite:
            errmsg = "Finite capacity counters can only be incremented by transactions"
            raise SimError(_ERROR_NAME, errmsg)

        # increment if there is room AND there are no processes already in
        # the queue. (There might be room if a previous increment request was
        # for a higher amount)
        if not self.__waitingTransactions and (self.__value + amount) <= self.__capacity:
            self.__value += amount
            self.__datacollector.add_value(self.__value/self.__normalizer)
            logger.debug('%s: incrementing by %d (no wait) current value: %d waiting transaction count: %d',
                         self, amount, self.__value, len(self.__waitingTransactions))
        else:
            self.__waitingTransactions.append((txn, amount, SimClock.now()))
            logger.debug('%s: increment by %d : waiting. current value: %d waiting transaction count: %d',
                         self, amount, self.__value,
                         len(self.__waitingTransactions))
            txn.wait_until_notified()

    def decrement(self, amount=1):
        """
        Decrement the counter by the specified amount (which defaults to one).
        This action never blocks.  If the decrement amount is greater than the
        counter's current value, the amount will be changed to that current
        value - i.e., the counter will be decremented to zero. Raises if the
        amount is not a positive integer
 
        :param amount: The amount to decrement the counter by. Must be a
                       positive integer. Defaults to 1.
        :type amount:  int

        """
        if type(amount) is not int:
            errmsg = "Invalid Counter decrement: increment amount: {0} is not an integer"
            raise SimError(_ERROR_NAME, errmsg, amount)

        if amount <= 0:
            errmsg = "Invalid Counter decrement: decrement amount: {0}"
            raise SimError(_ERROR_NAME, errmsg, amount)

        if amount <= self.__value:
            self.__value -= amount
        else:
            self.__value = 0
        self.__datacollector.add_value(self.__value/self.__normalizer)

        logger.debug('%s: decremented by %d to %d', self, amount, self.__value)

        # Find the next waiting process, if any - if there is sufficient
        # capacity to do that process's requested increment, do the
        # increment, resume the process and repeat until we there are no more
        # waiting processes, or we cannot resume the next process. (The loop
        # handles the case where a decrement amount > 1 may allow more than
        # one process to be resumed.)
        while True:
            if len(self.__waitingTransactions) > 0:
                transaction = self.__waitingTransactions[0][0]
                amount = self.__waitingTransactions[0][1]
                availableCapacity = self.__capacity - self.__value
                logger.debug('%s: amount: %d, available capacity: %d',
                             self, amount, availableCapacity)
                if amount <= availableCapacity:
                    self.__value += amount
                    self.__waitingTransactions.popleft()
                    transaction.resume()
                    continue
            break


        self.__datacollector.add_value(self.__value/self.__normalizer)

    @property
    @apidocskip
    def datasink(self):
        "Returns the counter's datasink"
        return self.__datacollector.datasink


class SimNullCounter(object):
    """
    SimNullCounter implements the SimCounter interface - increment() and
    decrement() - with no-ops
    """
    def increment(self, process=None, amount=1):
        pass

    def decrement(self, amount=1):
        pass






