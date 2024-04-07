from simprovise.core import *
import unittest
import sys

class MockProcess(object):
    resumedProcess = None
    def __init__(self):
        self.waiting = False

    def waitUntilNotified(self):
        self.waitStart = SimClock.now()
        self.waiting = True

    def resume(self):
        MockProcess.resumedProcess = self
        self.waiting = False

class MockElement(object):
    def registerDataset(self, dset):
        pass


class SimInfiniteCounterTests(unittest.TestCase):
    "Tests for infinite capacity counter, not time-dependent"
    def setUp(self):
        SimClock.initialize();
        element = MockElement()
        self.counter = counter.SimCounter(element, 'Test')
        self.process = MockProcess()

    def testInfiniteFlag(self):
        "Test: isInfinite returns true"
        self.assertEqual(self.counter.isInfinite, True)

    def testCapacity(self):
        "Test: capacity of an infinite capacity counter is None"
        self.assertEqual(self.counter.capacity, None)

    def testSetCapacity1(self):
        "Test: capacity setter"
        self.counter.capacity = 42
        self.assertEqual(self.counter.capacity, 42)

    def testSetCapacity2(self):
        "Test: capacity setter - infinite to finite and back"
        self.counter.capacity = 42
        self.counter.capacity = SimCounter.infinite
        self.assertEqual(self.counter.capacity, None)

    def testSetCapacity3(self):
        "Test: capacity setter - infinite to finite and back via None"
        self.counter.capacity = 42
        self.counter.capacity = None
        self.assertEqual(self.counter.capacity, None)

    def testUtilization(self):
        "Test: utilization of an infinite counter is None"
        self.assertEqual(self.counter.utilization, None)

    def testInitialValue(self):
        "Test: initial value of counter is zero"
        self.assertEqual(self.counter.value, 0)

    def testInitialMean1(self):
        "Test: if clock has not advanced, mean value is None"
        self.assertEqual(self.counter.meanValue, None)

    def testInitialMean2(self):
        "Test: if clock has not advanced, mean value is None, even with an increment"
        self.counter.increment(self.process)
        self.assertEqual(self.counter.meanValue, None)

    def testIncrement1(self):
        "Test: value property after increment"
        self.counter.increment(self.process)
        self.assertEqual(self.counter.value, 1)

    def testIncrement2(self):
        "Test: value property after increment of 2"
        self.counter.increment(self.process, 2)
        self.assertEqual(self.counter.value, 2)

    def testIncrement3(self):
        "Test: value property after increment of 3"
        self.counter.increment(self.process)
        self.counter.increment(self.process, 3)
        self.assertEqual(self.counter.value, 4)

    def testDecrement1(self):
        "Test: value property after increment of 2, decrement of 1"
        self.counter.increment(self.process, 2)
        self.counter.decrement()
        self.assertEqual(self.counter.value, 1)

    def testDecrement2(self):
        "Test: value property after increment of 2, two decrements of 1"
        self.counter.increment(self.process, 2)
        self.counter.decrement()
        self.counter.decrement()
        self.assertEqual(self.counter.value, 0)

    def testDecrement2(self):
        "Test: value property after increment of 2, decrement of 2"
        self.counter.increment(self.process, 2)
        self.counter.decrement(2)
        self.assertEqual(self.counter.value, 0)

    def testDecrementBelowZero1(self):
        "Test: decrement throws after increment of 1, two decrements result is zero"
        self.counter.increment(self.process, 1)
        self.counter.decrement()
        self.assertEqual(self.counter.value, 0)

    def testDecrementBelowZero2(self):
        "Test: decrement more then current value results in zero value"
        self.counter.increment(self.process, 1)
        self.counter.decrement(2)
        self.assertEqual(self.counter.value, 0)
        #self.assertRaises(simexception.Error, lambda: self.counter.decrement(2))

    def testMean1(self):
        "Test: if counter is not incremented and any time passes, mean is zero"
        SimClock.advanceTo(simtime.SimTime(1))
        self.assertEqual(self.counter.meanValue, 0.0)

    def testMean2(self):
        "Test: if counter is incremented at time zero and any time passes, mean is 1"
        self.counter.increment(self.process)
        SimClock.advanceTo(simtime.SimTime(1))
        self.assertEqual(self.counter.meanValue, 1.0)

    def testMean3(self):
        "Test: counter is incremented at time zero, decremented at time 1, and clock advanced to time 2 - mean = 0.5"
        self.counter.increment(self.process)
        SimClock.advanceTo(simtime.SimTime(1))
        self.counter.decrement()
        SimClock.advanceTo(simtime.SimTime(2))
        self.assertEqual(self.counter.meanValue, 0.5)

    def testOverflow1(self):
        "Test: Attempt to increment by sys.maxsize raises an error"
        self.assertRaises(simexception.SimError,
                          lambda: self.counter.increment(self.process, sys.maxsize))

    def testOverflow2(self):
        "Test: Attempt to increment to or past sys.maxsize raises an error"
        self.counter.increment(self.process, sys.maxsize - 1)
        self.assertRaises(simexception.SimError, lambda: self.counter.increment(self.process))

    def testOverflow3(self):
        "Test: Attempt to increment to or past infinite (sys.maxsize) raises an error"
        self.counter.increment(self.process, sys.maxsize - 2)
        self.assertRaises(simexception.SimError, lambda: self.counter.increment(self.process, 2))

    def testOverflow4(self):
        "Test: Attempt to increment to one less than sys.maxsize is OK"
        self.counter.increment(self.process, sys.maxsize - 2)
        self.counter.increment(self.process)
        self.assertEqual(self.counter.value, sys.maxsize - 1)

    def testFloatIncrement(self):
        "Test: Attempt to increment by a non-integer raises an error"
        self.assertRaises(simexception.SimError, lambda: self.counter.increment(self.process, 1.1))

    def testFloatDecrement(self):
        "Test: Attempt to decrement by a non-integer raises an error"
        self.counter.increment(self.process, 2)
        self.assertRaises(simexception.SimError, lambda: self.counter.decrement(1.1))

    def testNegativeIncrement(self):
        "Test: Attempt to increment by a negative value raises an error"
        self.assertRaises(simexception.SimError, lambda: self.counter.increment(self.process, -1))

    def testNegativeDecrement(self):
        "Test: Attempt to decrement by a negative value raises an error"
        self.counter.increment(self.process, 2)
        self.assertRaises(simexception.SimError, lambda: self.counter.decrement(-1))

    def testZeroIncrement(self):
        "Test: Attempt to increment by zero raises an error"
        self.assertRaises(simexception.SimError, lambda: self.counter.increment(self.process, 0))

    def testZeroDecrement(self):
        "Test: Attempt to decrement by a zero raises an error"
        self.counter.increment(self.process, 2)
        self.assertRaises(simexception.SimError, lambda: self.counter.decrement(0))

    def testFloatCapacity(self):
        "Test: Attempt to set capacity to a non-integer raises an error"
        with self.assertRaises(SimError):
            self.counter.capacity = 1.2

    def testZeroCapacity(self):
        "Test: Attempt to set capacity to zero raises an error"
        with self.assertRaises(SimError):
            self.counter.capacity = 0

    def testNegativeCapacity(self):
        "Test: Attempt to set capacity to a negative integer raises an error"
        with self.assertRaises(SimError):
            self.counter.capacity = -1

    def testSetCapacityAfterIncrement(self):
        "Test: Attempt to set capacity after the counter has bee incremented raises an error"
        with self.assertRaises(SimError):
            self.counter.increment(self.process, 1)
            self.counter.capacity = 3


CAP = 4

class SimFiniteCapacityCounterTests(unittest.TestCase):
    "Tests for finite capacity counter, not time-dependent"
    def setUp(self):
        SimClock.initialize();
        element = MockElement()
        self.counter = counter.SimCounter(element, 'Test', CAP)
        self.process = MockProcess()
        self.process2 = MockProcess()
        MockProcess.resumedProcess = None

    def testInfiniteFlag(self):
        "Test: isInfinite returns false"
        self.assertEqual(self.counter.isInfinite, False)

    def testCapacity(self):
        "Test: capacity of an finite capacity counter is CAP"
        self.assertEqual(self.counter.capacity, CAP)

    def testInitialValue(self):
        "Test: initial value of counter is zero"
        self.assertEqual(self.counter.value, 0)

    def testInitialMean1(self):
        "Test: if clock has not advanced, mean value is None"
        self.assertEqual(self.counter.meanValue, None)

    def testInitialMean2(self):
        "Test: if clock has not advanced, mean value is None, even with an increment"
        self.counter.increment(self.process)
        self.assertEqual(self.counter.meanValue, None)

    def testInitialUtilization(self):
        "Test: if clock has not advanced, utilization is None"
        self.assertEqual(self.counter.utilization, None)

    def testIncrement1(self):
        "Test: value property after increment"
        self.counter.increment(self.process)
        self.assertEqual(self.counter.value, 1)

    def testIncrement2(self):
        "Test: value property after increment of 2"
        self.counter.increment(self.process, 2)
        self.assertEqual(self.counter.value, 2)

    def testIncrement2a(self):
        "Test: waiting process count property after increment of 2 should be zero"
        self.counter.increment(self.process, 2)
        self.assertEqual(self.counter.waitingTransactionCount, 0)

    def testIncrement3(self):
        "Test: value property after increment of 1, 3"
        self.counter.increment(self.process)
        self.counter.increment(self.process, 3)
        self.assertEqual(self.counter.value, 4)

    def testIncrement4a(self):
        "Test: waiting process count property after increment of 4 (equal to capacity) should be zero"
        self.counter.increment(self.process, 4)
        self.assertEqual(self.counter.waitingTransactionCount, 0)

    def testIncrementPastCap1(self):
        "Test: value property after increment past capacity"
        self.counter.increment(self.process, CAP)
        self.counter.increment(self.process)
        self.assertEqual(self.counter.value, CAP)

    def testIncrementPastCap1a(self):
        "Test: waiting process count property after increment one past capacity should be one"
        self.counter.increment(self.process, CAP)
        self.counter.increment(self.process2)
        self.assertEqual(self.counter.waitingTransactionCount, 1)

    def testDecrement1(self):
        "Test: value property after increment of 2, decrement of 1"
        self.counter.increment(self.process, 2)
        self.counter.decrement()
        self.assertEqual(self.counter.value, 1)

    def testDecrement2(self):
        "Test: value property after increment of 2, two decrements of 1"
        self.counter.increment(self.process, 2)
        self.counter.decrement()
        self.counter.decrement()
        self.assertEqual(self.counter.value, 0)

    def testDecrement2(self):
        "Test: value property after increment of 2, decrement of 2"
        self.counter.increment(self.process, 2)
        self.counter.decrement(2)
        self.assertEqual(self.counter.value, 0)

    def testDecrementBelowZero1(self):
        "Test: decrement throws after increment of 1, two decrements result is zero"
        self.counter.increment(self.process, 1)
        self.counter.decrement()
        self.assertEqual(self.counter.value, 0)

    def testDecrementBelowZero2(self):
        "Test: decrement more then current value results in zero value"
        self.counter.increment(self.process, 1)
        self.counter.decrement(2)
        self.assertEqual(self.counter.value, 0)
        #self.assertRaises(simexception.Error, lambda: self.counter.decrement(2))

    def testMean1(self):
        "Test: if counter is not incremented and any time passes, mean is zero"
        SimClock.advanceTo(simtime.SimTime(1))
        self.assertEqual(self.counter.meanValue, 0.0)

    def testMean2(self):
        "Test: if counter is incremented at time zero and any time passes, mean is 1"
        self.counter.increment(self.process)
        SimClock.advanceTo(simtime.SimTime(1))
        self.assertEqual(self.counter.meanValue, 1.0)

    def testMean3(self):
        "Test: counter is incremented at time zero, decremented at time 1, and clock advanced to time 2 - mean = 0.5"
        self.counter.increment(self.process)
        SimClock.advanceTo(simtime.SimTime(1))
        self.counter.decrement()
        SimClock.advanceTo(simtime.SimTime(2))
        self.assertEqual(self.counter.meanValue, 0.5)

    def testIncrementAboveCapacity(self):
        "Test: increment of an amount greater than capacity raises an error"
        self.assertRaises(simexception.SimError, lambda: self.counter.increment(self.process, CAP+1))

class SimSetFiniteCapacityCounterTests(unittest.TestCase):
    """
    Tests for finite capacity counter where capacity is specified via
    setter, not time-dependent
    """
    def setUp(self):
        SimClock.initialize();
        element = MockElement()
        self.counter = counter.SimCounter(element, 'Test')
        self.counter.capacity = CAP
        self.process = MockProcess()
        self.process2 = MockProcess()
        MockProcess.resumedProcess = None

    def testInfiniteFlag(self):
        "Test: isInfinite returns false"
        self.assertEqual(self.counter.isInfinite, False)

    def testCapacity(self):
        "Test: capacity of an finite capacity counter is CAP"
        self.assertEqual(self.counter.capacity, CAP)

    def testInitialValue(self):
        "Test: initial value of counter is zero"
        self.assertEqual(self.counter.value, 0)

    def testInitialMean1(self):
        "Test: if clock has not advanced, mean value is None"
        self.assertEqual(self.counter.meanValue, None)

    def testInitialMean2(self):
        "Test: if clock has not advanced, mean value is None, even with an increment"
        self.counter.increment(self.process)
        self.assertEqual(self.counter.meanValue, None)

    def testInitialUtilization(self):
        "Test: if clock has not advanced, utilization is None"
        self.assertEqual(self.counter.utilization, None)

    def testIncrement1(self):
        "Test: value property after increment"
        self.counter.increment(self.process)
        self.assertEqual(self.counter.value, 1)

    def testIncrement2(self):
        "Test: value property after increment of 2"
        self.counter.increment(self.process, 2)
        self.assertEqual(self.counter.value, 2)

    def testIncrement2a(self):
        "Test: waiting process count property after increment of 2 should be zero"
        self.counter.increment(self.process, 2)
        self.assertEqual(self.counter.waitingTransactionCount, 0)

    def testIncrement3(self):
        "Test: value property after increment of 1, 3"
        self.counter.increment(self.process)
        self.counter.increment(self.process, 3)
        self.assertEqual(self.counter.value, 4)

    def testIncrement4a(self):
        "Test: waiting process count property after increment of 4 (equal to capacity) should be zero"
        self.counter.increment(self.process, 4)
        self.assertEqual(self.counter.waitingTransactionCount, 0)

    def testIncrementPastCap1(self):
        "Test: value property after increment past capacity"
        self.counter.increment(self.process, CAP)
        self.counter.increment(self.process)
        self.assertEqual(self.counter.value, CAP)

    def testIncrementPastCap1a(self):
        "Test: waiting process count property after increment one past capacity should be one"
        self.counter.increment(self.process, CAP)
        self.counter.increment(self.process2)
        self.assertEqual(self.counter.waitingTransactionCount, 1)

    def testDecrement1(self):
        "Test: value property after increment of 2, decrement of 1"
        self.counter.increment(self.process, 2)
        self.counter.decrement()
        self.assertEqual(self.counter.value, 1)

    def testDecrement2(self):
        "Test: value property after increment of 2, two decrements of 1"
        self.counter.increment(self.process, 2)
        self.counter.decrement()
        self.counter.decrement()
        self.assertEqual(self.counter.value, 0)

    def testDecrement2(self):
        "Test: value property after increment of 2, decrement of 2"
        self.counter.increment(self.process, 2)
        self.counter.decrement(2)
        self.assertEqual(self.counter.value, 0)

    def testDecrementBelowZero1(self):
        "Test: decrement throws after increment of 1, two decrements result is zero"
        self.counter.increment(self.process, 1)
        self.counter.decrement()
        self.assertEqual(self.counter.value, 0)

    def testDecrementBelowZero2(self):
        "Test: decrement more then current value results in zero value"
        self.counter.increment(self.process, 1)
        self.counter.decrement(2)
        self.assertEqual(self.counter.value, 0)
        #self.assertRaises(simexception.Error, lambda: self.counter.decrement(2))

    def testMean1(self):
        "Test: if counter is not incremented and any time passes, mean is zero"
        SimClock.advanceTo(simtime.SimTime(1))
        self.assertEqual(self.counter.meanValue, 0.0)

    def testMean2(self):
        "Test: if counter is incremented at time zero and any time passes, mean is 1"
        self.counter.increment(self.process)
        SimClock.advanceTo(simtime.SimTime(1))
        self.assertEqual(self.counter.meanValue, 1.0)

    def testMean3(self):
        "Test: counter is incremented at time zero, decremented at time 1, and clock advanced to time 2 - mean = 0.5"
        self.counter.increment(self.process)
        SimClock.advanceTo(simtime.SimTime(1))
        self.counter.decrement()
        SimClock.advanceTo(simtime.SimTime(2))
        self.assertEqual(self.counter.meanValue, 0.5)

    def testIncrementAboveCapacity(self):
        "Test: increment of an amount greater than capacity raises an error"
        self.assertRaises(simexception.SimError, lambda: self.counter.increment(self.process, CAP+1))



class SimProcessResumeCounterTests(unittest.TestCase):
    "Tests on process resumption for a finite capacity counter"
    def setUp(self):
        SimClock.initialize();
        element = MockElement()
        self.counter = counter.SimCounter(element, 'Test', CAP)
        self.process = MockProcess()
        self.process2 = MockProcess()
        self.process3 = MockProcess()
        MockProcess.resumedProcess = None
        self.counter.increment(self.process, CAP)

    def testWaitingProcessCount1(self):
        "Test: waiting process count after increment to (but not past) capacity"
        self.assertEqual( self.counter.waitingTransactionCount, 0)

    def testWaitingProcessCount1a(self):
        "Test: process not waiting after increment to (but not past) capacity"
        self.assertEqual(self.process.waiting, False)

    def testWaitingProcessCount2(self):
        "Test: waiting process count after attempt to increment one past capacity"
        self.counter.increment(self.process2)
        self.assertEqual( self.counter.waitingTransactionCount, 1)

    def testWaitingProcessCount2a(self):
        "Test: waiting process count after attempt to increment one past capacity"
        self.counter.increment(self.process2)
        self.assertEqual(self.process2.waiting, True)

    def testWaitingProcessCount3(self):
        "Test: waiting process count after attempt to increment three past capacity"
        self.counter.increment(self.process2, 3)
        self.assertEqual(self.counter.waitingTransactionCount, 1)

    def testWaitingProcessCount4(self):
        "Test: waiting process count after two attempts to increment past capacity"
        self.counter.increment(self.process2)
        self.counter.increment(self.process3)
        self.assertEqual( self.counter.waitingTransactionCount, 2)

    def testWaitingProcessCount4a(self):
        "Test: two processes incremented past capacity - both should be waiting"
        self.counter.increment(self.process2)
        self.counter.increment(self.process3)
        self.assertEqual((self.process2.waiting, self.process3.waiting), (True, True))

    def testResumeAfterIncrement1(self):
        "Test: increment to capacity does not resume any processes"
        self.assertEqual( MockProcess.resumedProcess, None)

    def testResumeAfterIncrement2(self):
        "Test: increment past capacity does not resume any processes"
        self.counter.increment(self.process, 1)
        self.assertEqual( MockProcess.resumedProcess, None)

    def testResumeAfterDecrement1(self):
        "Test: decrement when counter is at capacity does not resume any processes"
        self.counter.decrement(1)
        self.assertEqual( MockProcess.resumedProcess, None)

    def testResumeAfterDencrement2(self):
        "Test: process2 increment one past capacity, followed by decrement - process2 is resumed"
        self.counter.increment(self.process2, 1)
        self.counter.decrement()
        self.assertEqual( MockProcess.resumedProcess, self.process2)

    def testResumeAfterDencrement3(self):
        "Test: process2 increment two past capacity, followed by decrement - NO process resumed"
        self.counter.increment(self.process2, 2)
        self.counter.decrement()
        self.assertEqual( MockProcess.resumedProcess, None)

    def testResumeAfterDencrement4(self):
        "Test: process2 increment two past capacity, followed by two decrements - process2 is resumed"
        self.counter.increment(self.process2, 2)
        self.counter.decrement()
        self.counter.decrement()
        self.assertEqual( MockProcess.resumedProcess, self.process2)

    def testResumeAfterDencrement5(self):
        "Test: process2 increment two past capacity, followed by decrement of two - process2 is resumed"
        self.counter.increment(self.process2, 2)
        self.counter.decrement(2)
        self.assertEqual( MockProcess.resumedProcess, self.process2)

    def testResumeAfterDencrement6(self):
        "Test: process2 increment two past capacity, followed by an additonal increment then a decrement - NO process resumed"
        self.counter.increment(self.process2, 2)
        self.counter.increment(self.process3, 1)
        self.counter.decrement()
        self.assertEqual( MockProcess.resumedProcess, None)

    def testResumeAfterDencrement7(self):
        "Test: process2 then process3 increment past capacity - second decrement resumes process3 last"
        self.counter.increment(self.process2)
        self.counter.increment(self.process3)
        self.counter.decrement()
        self.counter.decrement()
        self.assertEqual( MockProcess.resumedProcess, self.process3)

    def testResumeAfterDencrement8(self):
        "Test: process2 then process3 increment past capacity - decrement of two resumes both process 2 and 3"
        self.counter.increment(self.process2)
        self.counter.increment(self.process3)
        self.counter.decrement(2)
        self.assertEqual(self.counter.waitingTransactionCount, 0)

    def testResumeAfterDencrement8a(self):
        "Test: process2 then process3 increment past capacity - decrement of two resumes process3 last"
        self.counter.increment(self.process2)
        self.counter.increment(self.process3)
        self.counter.decrement(2)
        self.assertEqual( MockProcess.resumedProcess, self.process3)

    def testResumeAfterDencrement8b(self):
        "Test: process2 then process3 increment past capacity - one decrement of two resume both process 2 and 3 (in that order)"
        self.counter.increment(self.process2)
        self.counter.increment(self.process3)
        self.counter.decrement()
        resumedProc1 = MockProcess.resumedProcess
        self.counter.decrement()
        resumedProc2 = MockProcess.resumedProcess
        self.assertEqual( (resumedProc1, resumedProc2), (self.process2, self.process3))

    def testResumeAfterDencrement9(self):
        """
        Test:
        1.  process2 increment two past capacity
        2.  counter is decremented (now one less then capacity)
        3.  process3 increments by one
        Result - NO process resumed (process3 should NOT jump process2
        """
        self.counter.increment(self.process2, 2)
        self.counter.decrement()
        self.counter.increment(self.process3, 1)
        self.assertEqual( MockProcess.resumedProcess, None)

    def testResumeAfterDencrement10(self):
        """
        Test:
        1.  process2 increment two past capacity
        2.  counter is decremented (now one less then capacity)
        3.  process3 increments by one
        Result - value still below capacity because process2 is first in line to be resumed
        """
        self.counter.increment(self.process2, 2)
        self.counter.decrement()
        self.counter.increment(self.process3, 1)
        self.assertEqual(self.counter.value, CAP-1)

    def testResumeAfterDencrement10(self):
        """
        Test:
        1.  process2 increment two past capacity
        2.  counter is decremented (now one less then capacity)
        3.  process3 increments by one
        Result - both process2 and process 3 are waiting
        """
        self.counter.increment(self.process2, 2)
        self.counter.decrement()
        self.counter.increment(self.process3, 1)
        self.assertEqual((self.process2.waiting, self.process3.waiting), (True, True))

    def testResumeAfterDencrement11(self):
        """
        Test:
        1.  process2 increment two past capacity
        2.  counter is decremented (now one less then capacity)
        3.  process3 increments by one
        4.  another decrement
        Result - process2 is resumed, process3 is still waiting
        """
        self.counter.increment(self.process2, 2)
        self.counter.decrement()
        self.counter.increment(self.process3, 1)
        self.counter.decrement()
        self.assertEqual((self.process2.waiting, self.process3.waiting), (False, True))

    def testResumeAfterDencrement12(self):
        """
        Test:
        1.  process2 increment two past capacity
        2.  counter is decremented (now one less then capacity)
        3.  process3 increments by one
        4.  another decrement
        5.  yet another decrement
        Result - process3 is last resumed
        """
        self.counter.increment(self.process2, 2)
        self.counter.decrement()
        self.counter.increment(self.process3, 1)
        self.counter.decrement()
        self.counter.decrement()
        self.assertEqual(MockProcess.resumedProcess, self.process3)


class TimeWeightTests(unittest.TestCase):
    "Test time-weighted statistics on a counter of capacity 4"
    def setUp(self):
        SimClock.initialize()
        element = MockElement()
        self.counter = counter.SimCounter(element, 'Test', CAP)
        self.process = MockProcess()
        SimClock.advanceTo(simtime.SimTime(1))
        self.counter.increment(self.process)
        SimClock.advanceTo(simtime.SimTime(2))
        self.counter.increment(self.process, 2)
        SimClock.advanceTo(simtime.SimTime(4))

    def testMean1(self):
        "Test: initial mean value is (1 + 2*3)/4"
        self.assertEqual(self.counter.meanValue, 1.75)

    def testMean2(self):
        "Test: increment without clock advance does not impact mean"
        initMean = self.counter.meanValue
        self.counter.increment(self.process)
        self.assertEqual(self.counter.meanValue, initMean)

    def testMean3(self):
        "Test: decrement without clock advance does not impact mean"
        initMean = self.counter.meanValue
        self.counter.decrement()
        self.assertEqual(self.counter.meanValue, initMean)

    def testUtil1(self):
        "Test: initial utilization value is 1.75/4"
        self.assertEqual(self.counter.utilization, 0.4375)

def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SimInfiniteCounterTests))
    suite.addTest(unittest.makeSuite(SimFiniteCapacityCounterTests))
    suite.addTest(unittest.makeSuite(SimSetFiniteCapacityCounterTests))
    suite.addTest(unittest.makeSuite(TimeWeightTests))
    return suite

if __name__ == '__main__':
    unittest.main()
