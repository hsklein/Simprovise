#===============================================================================
# MODULE simresource_test
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Unit tests for SimResource and related classes
#===============================================================================
import unittest
import simprovise.core
from simprovise.core import *
from simprovise.core.agent import SimAgent, SimMsgType
from simprovise.core.location import SimStaticObject
from simprovise.core.simtime import Unit as tu

#print(globals().keys())
#print(locals().keys())

ONE_MIN = simtime.SimTime(1, tu.MINUTES)
TWO_MINS = simtime.SimTime(2, tu.MINUTES)
THREE_MINS = simtime.SimTime(3, tu.MINUTES)
FOUR_MINS = simtime.SimTime(4, tu.MINUTES)
EIGHT_MINS = simtime.SimTime(8, tu.MINUTES)
            

class RATestCaseBase(unittest.TestCase):
    """
    TestCase base class providing common setup
    """
    def setUp(self):
        SimDataCollector.reinitialize()
        SimClock.initialize()
        simevent.initialize()
        self.eventProcessor = simevent.EventProcessor()
        MockProcess.resumedProcess = None
        # Hack to allow recreation of static objects for each test case
        SimStaticObject.elements = {}
        
        self.location = MockLocation()
        self.source = MockSource()
        self.entities = []
        self.processes = []
        for i in range(5):
            process = MockProcess()
            process.executing(True)
            entity = MockEntity(self.source, process)
            self.processes.append(process)
            self.entities.append(entity)           
        
        self.process = self.processes[0]
        self.process1 = self.processes[1]
        self.process2 = self.processes[2]
        self.process3 = self.processes[3]
        self.process4 = self.processes[4]
        
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimStaticObject.elements = {}
    
        
class MockSource(SimEntitySource):
    def __init__(self):
        super().__init__("MockSource")

class MockEntity(SimEntity):
    ""
  
class MockProcess(SimProcess):
    resumedProcess = None
    def __init__(self, executing=False):
        super().__init__()
        self.waiting = False
        if executing:
            self.executing(True)
        #mockEntity = MockEntity(self)
        
    def executing(self, flag):
        self._executing = flag
 
        
class TestProcess1(SimProcess):
    """
    """
    assignedProcesses = []
    count = 0
    source = MockSource()
    
    @staticmethod
    def initialize():
        TestProcess1.assignedProcesses.clear()
        TestProcess1.count = 0
        
    @staticmethod
    def getPriority(msg):
        process = msg.msgData[0]
        return process.priority
    
    @staticmethod
    def pids():
        return [p.pid for p in TestProcess1.assignedProcesses]
    
    @staticmethod
    def assignmentTimes():
        return [p.assignmentTime for p in TestProcess1.assignedProcesses]
        
    def __init__(self, testcase, priority=1):
        super().__init__()
        self.testcase = testcase
        self.priority = priority
        TestProcess1.count += 1
        self.pid = TestProcess1.count
        self._assignment = None
        self.assignmentTime = None
        entity = MockEntity(TestProcess1.source, self)
        
    @property
    def assignment(self):
        return self._assignment
    
    @assignment.setter
    def assignment(self, value):
        self._assignment = value
        self.assignmentTime = SimClock.now()
        if value is not None:
            TestProcess1.assignedProcesses.append(self)
        
    @property
    def waiting(self): 
        return self.assignment is None
       
class MockLocation(SimLocation):
    def __init__(self):
        super().__init__("MockLocation")
        
class TestResource(SimSimpleResource):
    """    
    """
                

class ResourceAssignmentTests(RATestCaseBase):
    "Tests ResourceAssignments"
    
    def testInvalidAssignmentResources(self):
        "Test: Attempt to create a ResourceAssignment with an empty resource sequence raises an error"
        rsrc = SimSimpleResource("TestResource", self.location, capacity=1)
        self.assertRaises(SimError, lambda: SimResourceAssignment(self.process, rsrc, []))
        
    def testCountProperty(self):
        "Test:  ResourceAssignment count property returns length of resource list supplied to constructor"
        rsrc = SimSimpleResource("TestResource", self.location, capacity=2)
        ra = SimResourceAssignment(self.process, rsrc, (rsrc, rsrc))
        self.assertEqual(ra.count, 2)
        
    def testAgentProperty(self):
        "Test:  ResourceAssignment assignment agent property returns resource supplied to constructor"
        rsrc = SimSimpleResource("TestResource", self.location, capacity=2)
        ra = SimResourceAssignment(self.process, rsrc, (rsrc, rsrc))
        self.assertEqual(ra.assignment_agent, rsrc)
        
    def testResourcesProperty(self):
        "Test:  ResourceAssignment resources property returns resource sequence supplied to constructor as a tuple"
        rsrc = SimSimpleResource("TestResource", self.location, capacity=2)
        ra = SimResourceAssignment(self.process, rsrc, [rsrc, rsrc])
        self.assertEqual(ra.resources, (rsrc, rsrc))
        
    def testSingleResourceProperty(self):
        "Test:  ResourceAssignment resource property returns single resource supplied to constructor"
        rsrc = SimSimpleResource("TestResource", self.location, capacity=2)
        ra = SimResourceAssignment(self.process, rsrc, (rsrc,))
        self.assertEqual(ra.resource, rsrc)
        
    def testMultiCapacityResourceProperty(self):
        "Test:  ResourceAssignment resource property returns resource when initialized with multiple references to same resource"
        rsrc = SimSimpleResource("TestResource", self.location, capacity=2)
        ra = SimResourceAssignment(self.process, rsrc, (rsrc,rsrc))
        self.assertEqual(ra.resource, rsrc)
        
    def testMultipleResourceProperty(self):
        "Test:  ResourceAssignment resource property raises an Error when assignment is created with more than one distinct resource object"
        rsrc1 = SimSimpleResource("TestResource1", self.location, capacity=2)
        rsrc2 = SimSimpleResource("TestResource2", self.location)
        ra = SimResourceAssignment(self.process, rsrc1, (rsrc1,rsrc2))
        self.assertRaises(SimError, lambda: ra.resource)

class ResourceAssignmentSubtractTests(RATestCaseBase):
    "Tests ResourceAssignment subtract and subtractAll methods"
    def setUp(self):
        super().setUp()
        self.rsrc = SimSimpleResource("TestResource1", self.location, capacity=2)
        self.rsrc2 = SimSimpleResource("TestResource2", self.location)
        self.rsrc3 = SimSimpleResource("TestResource3", self.location)
        self.ra = SimResourceAssignment(self.process, self.rsrc, (self.rsrc, self.rsrc2))
        
    def testSubtractAll1(self):
        "Test:  after ResourceAssignment.subtractAll, count property is zero"
        self.ra.subtract_all()
        self.assertEqual(self.ra.count, 0)
        
    def testSubtractAll2(self):
        "Test:  after ResourceAssignment.subtractAll, resources property returns an empty tuple"
        self.ra.subtract_all()
        self.assertEqual(self.ra.resources, ())
        
    def testSubtractAll3(self):
        "Test:  after ResourceAssignment.subtractAll, resource property raises an Error"
        self.ra.subtract_all()
        self.assertRaises(SimError, lambda: self.ra.resource)
        
    def testSubtract1(self):
        "Test:  after ResourceAssignment.subtract((rsrc, rsrc2)), assignment count property is zero"
        self.ra.subtract((self.rsrc, self.rsrc2))
        self.assertEqual(self.ra.count, 0)
        
    def testSubtract2(self):
        "Test:  after ResourceAssignment.subtract(rsrc), resource property returns remaining resource"
        self.ra.subtract((self.rsrc,))
        self.assertEqual(self.ra.resource, self.rsrc2)                           
        
    def testSubtract3(self):
        "Test:  Attempt to subtract a resource not in the assignment raises an Error"
        self.assertRaises(SimError, lambda: self.ra.subtract((self.rsrc3,)))                          
        
    def testSubtract3(self):
        "Test:  Attempt to subtract a resource that has already been subtracted from the assignment raises an Error"
        self.ra.subtract((self.rsrc,))
        self.assertRaises(SimError, lambda: self.ra.subtract((self.rsrc,)))                          


class ResourceAssignmentContainsTests(RATestCaseBase):
    "Tests ResourceAssignment contains() method"
    def setUp(self):
        super().setUp()
        self.rsrc1 = SimSimpleResource("TestResource1", self.location, capacity=1)
        self.rsrc2 = SimSimpleResource("TestResource2", self.location, capacity=2)
        self.rsrc3 = SimSimpleResource("TestResource3", self.location)
        
    def testContain1(self):
        "Test:  assignment with single resource contains that resource"
        ra = SimResourceAssignment(self.process, self.rsrc1, (self.rsrc1,))
        self.assertTrue(ra.contains((self.rsrc1,)))
        
    def testContain2(self):
        "Test:  assignment with single resource does not contain a different resource"
        ra = SimResourceAssignment(self.process, self.rsrc1, (self.rsrc1,))
        self.assertFalse(ra.contains((self.rsrc2,)))
        
    def testContain3(self):
        "Test:  assignment with single resource does not contain two if that resource"
        ra = SimResourceAssignment(self.process, self.rsrc1, (self.rsrc2,))
        self.assertFalse(ra.contains((self.rsrc2, self.rsrc2)))
        
    def testContain3(self):
        "Test:  assignment with two of same resource contains one of that resource"
        ra = SimResourceAssignment(self.process, self.rsrc1, (self.rsrc2, self.rsrc2))
        self.assertTrue(ra.contains((self.rsrc2,)))
        
    def testContain4(self):
        "Test:  assignment with two of same resource contains one of that resource"
        ra = SimResourceAssignment(self.process, self.rsrc1, (self.rsrc2, self.rsrc2))
        self.assertTrue(ra.contains((self.rsrc2, self.rsrc2)))
        
    def testContain5(self):
        "Test:  assignment with two of same resource does notcontain 3 of that resource"
        ra = SimResourceAssignment(self.process, self.rsrc1, (self.rsrc2, self.rsrc2))
        self.assertFalse(ra.contains((self.rsrc2,) * 3))
        
    def testContain6(self):
        "Test:  assignment with two of same resource does not contain a different resource"
        ra = SimResourceAssignment(self.process, self.rsrc1, (self.rsrc2, self.rsrc2))
        self.assertFalse(ra.contains((self.rsrc1, self.rsrc2)))
        
    def testContain7(self):
        "Test:  assignment with two different resource contains both of them"
        ra = SimResourceAssignment(self.process, self.rsrc1, (self.rsrc1, self.rsrc2))
        self.assertTrue(ra.contains((self.rsrc1, self.rsrc2)))
        
    def testContain8(self):
        "Test:  assignment with two different resource contains the first of them"
        ra = SimResourceAssignment(self.process, self.rsrc1, (self.rsrc1, self.rsrc2))
        self.assertTrue(ra.contains((self.rsrc1,)))
        
    def testContain9(self):
        "Test:  assignment with two different resource contains the 2nd of them"
        ra = SimResourceAssignment(self.process, self.rsrc1, (self.rsrc1, self.rsrc2))
        self.assertTrue(ra.contains((self.rsrc2,)))
        
    def testContain10(self):
        "Test:  assignment with two different resource does not contain two of the same"
        ra = SimResourceAssignment(self.process, self.rsrc1, (self.rsrc1, self.rsrc2))
        self.assertFalse(ra.contains((self.rsrc1, self.rsrc1)))
 
class TestProcessSRP(TestProcess1):
    """
    """
    def __init__(self, rsrc, numrequested=1):
        super().__init__(SimpleResourcePropertyTests)
        self.rsrc = rsrc
        self.numrequested = numrequested
        
    def run(self):
        self.assignment = self.acquire(self.rsrc, self.numrequested)
        self.wait_for(1)
        self.release(self.assignment)
        
class SimpleResourcePropertyTests(RATestCaseBase):
    "Tests SimpleResource class properties"
    def setUp(self):
        super().setUp()
        self.rsrc1 = SimSimpleResource("TestResource1", self.location)
        self.rsrc2 = SimSimpleResource("TestResource2", self.location, capacity=2)
        self.rsrc3 = SimSimpleResource("TestResource3", self.location, capacity=3)
        
    def testCapacity1(self):
        "Test:  Resource 1 has default capacity of one"
        self.assertEqual(self.rsrc1.capacity, 1)
        
    def testInUse1a(self):
        "Test:  Resource 1 has initial inUse property value of zero"
        self.assertEqual(self.rsrc1.in_use, 0)
        
    def testInUse1b(self):
        "Test:  Resource 1 has inUse property value of one after a single acquire() call"
        self.process = TestProcessSRP(self.rsrc1, 1)
        self.process.start()
        self.eventProcessor.process_events(0)
        self.assertEqual(self.rsrc1.in_use, 1)
        
    def testAvailable1a(self):
        "Test:  Resource 1 has initial available property value of one"
        self.assertEqual(self.rsrc1.available, 1)
        
    def testAvailable1b(self):
        "Test:  Resource 1 has available property value of zero after a single acquire() call"
        self.process = TestProcessSRP(self.rsrc1, 1)
        self.process.start()
        self.eventProcessor.process_events(0)
        self.assertEqual(self.rsrc1.available, 0)
        
    def testDown1(self):
        "Test:  Resource 1 has initial down property value of zero"
        self.assertFalse(self.rsrc1.down)
    
    def testCapacity2(self):
        "Test:  Resource 2 has capacity of two"
        self.assertEqual(self.rsrc2.capacity, 2)
           
    def testInUse2a(self):
        "Test:  Resource 1 has initial inUse property value of zero"
        self.assertEqual(self.rsrc2.in_use, 0)
        
    def testInUse2b(self):
        "Test:  Resource 2 has inUse property value of two after a two acquire() calls"
        self.process1 = TestProcessSRP(self.rsrc2, 1)
        self.process1.start()
        self.process2 = TestProcessSRP(self.rsrc2, 1)
        self.process2.start()
        self.eventProcessor.process_events(0)
        self.assertEqual(self.rsrc2.in_use, 2)
        
    def testInUse2c(self):
        "Test:  Resource 2 has inUse property value of two after an acquire(2) call"
        self.process = TestProcessSRP(self.rsrc2, 2)
        self.process.start()
        self.eventProcessor.process_events(0)
        self.assertEqual(self.rsrc2.in_use, 2)

    def testAvailable2a(self):
        "Test:  Resource 2 has initial available property value of two"
        self.assertEqual(self.rsrc2.available, 2)

    def testAvailable2b(self):
        "Test:  Resource 2 has available property value of one after an acquire call"
        self.process = TestProcessSRP(self.rsrc2, 1)
        self.process.start()
        self.eventProcessor.process_events(0)
        self.assertTrue(self.rsrc2.available, 1)

    def testAvailable2c(self):
        "Test:  Resource 2 has available property value of zero after acquire(2) call"
        self.process = TestProcessSRP(self.rsrc2, 2)
        self.process.start()
        self.eventProcessor.process_events(0)
        self.assertEqual(self.rsrc2.available, 0)
        
    def testDown2(self):
        "Test:  Resource 2 has initial down property value of zero"
        self.assertFalse(self.rsrc2.down)
        
    def testCurrentAssignments(self):
        "Test: two acquisitions of a resource, both assignments returned by current_assignments"
        self.process1 = TestProcessSRP(self.rsrc2, 1)
        self.process1.start()
        self.process2 = TestProcessSRP(self.rsrc2, 1)
        self.process2.start()
        self.eventProcessor.process_events(0)
        assignment1 = self.process1.assignment
        assignment2 = self.process2.assignment
        assignments = set(self.rsrc2.current_assignments())
        self.assertEqual(assignments, set((assignment1, assignment2)))
        
    def testCurrentTransactions(self):
        "Test: two processes acquire a resource, both processes returned by current_transactions"
        self.process1 = TestProcessSRP(self.rsrc2, 1)
        self.process1.start()
        self.process2 = TestProcessSRP(self.rsrc2, 1)
        self.process2.start()
        self.eventProcessor.process_events(0)
        txns = set(self.rsrc2.current_transactions())
        self.assertEqual(txns, set((self.process1, self.process2)))
   
        
class SimpleResourceBasicAcquireTests(RATestCaseBase):
    "Tests basic SimpleResource class acquire() functionality"
    def setUp(self):
        super().setUp()
        self.rsrc1 = SimSimpleResource("TestResource1", self.location)
        self.rsrc2 = SimSimpleResource("TestResource2", self.location, capacity=2)
        self.rsrc3 = SimSimpleResource("TestResource3", self.location, capacity=3)
        self.process1 = TestProcessSRP(self.rsrc1, 1)
        self.process1.start()
        self.process2 = TestProcessSRP(self.rsrc2, 2)
        self.process2.start()
        self.eventProcessor.process_events(0)
        
    def testAssignment1(self):
        "Test: acquire() returns a resource assignment with correct process"
        ra = self.process1.assignment
        self.assertEqual(ra.process, self.process1)
        
    def testAssignment1a(self):
        "Test: acquire(1) returns a resource assignment with correct count"
        ra = self.process1.assignment
        self.assertEqual(ra.count, 1)
        
    def testAssignment1b(self):
        "Test: acquire(1) returns a resource assignment with correct resource"
        ra = self.process1.assignment
        self.assertEqual(ra.resource, self.rsrc1)
        
    def testAssignment2(self):
        "Test: acquire(2) returns a resource assignment with correct count"
        ra = self.process2.assignment
        self.assertEqual(ra.count, 2)
        
    def testAcquireGreaterThanCapacity(self):
        "Test: acquire(3) on a resource of capacity two raises an Error"
        self.assertRaises(SimError, lambda:  self.process3.acquire(self.rsrc2, 3))
        
    def testAcquireZero(self):
        "Test: acquire(0) raises an Error"
        self.assertRaises(SimError, lambda:  self.process3.acquire(self.rsrc2, 0))
        
    def testAcquireNonInt(self):
        "Test: acquire for a non-integer numRequested raises an Error"
        self.assertRaises(SimError, lambda:  self.process3.acquire(self.rsrc2, 2.4))
        
    def testAcquireWhileNotExecuting(self):
        "Test: acquire() for a process that is not currently executing raises an Error"
        self.process.executing(False)
        self.assertRaises(AssertionError, lambda:  self.process.acquire(self.rsrc2, 1))

        
 
class TestProcessBasicRelease(TestProcess1):
    """
    """
    def __init__(self, rsrc, nacquire, nrelease=None):
        super().__init__(SimpleResourcePropertyTests)
        self.rsrc = rsrc
        self.nacquire = nacquire
        self.nrelease = nrelease
        
    def run(self):
        self.assignment = self.acquire(self.rsrc, self.nacquire)
        self.wait_for(ONE_MIN)
        self.release(self.assignment, self.nrelease)
        self.wait_for(EIGHT_MINS)
 
class TestProcessBasicRelease2(TestProcessBasicRelease):
    """
    """    
    def run(self):
        self.assignment = self.acquire(self.rsrc, self.nacquire)
        self.wait_for(ONE_MIN)
        for i in range(self.nrelease):
            self.release(self.assignment, 1)
        self.wait_for(EIGHT_MINS)
        
        
class SimpleResourceBasicReleaseTests(RATestCaseBase):
    "Tests basic SimpleResource class release() functionality"
    def setUp(self):
        super().setUp()
        self.rsrc1 = SimSimpleResource("TestResource1", self.location)
        self.rsrc2 = SimSimpleResource("TestResource2", self.location, capacity=2)
        self.rsrc3 = SimSimpleResource("TestResource3", self.location, capacity=3)
        
    def testReleaseAll1(self):
        "Test: acquire() followed by release results in resource inUse property value of zero"
        self.process1 = TestProcessBasicRelease(self.rsrc1, 1, 1)
        self.process1.start()
        self.eventProcessor.process_events(ONE_MIN)
        self.assertEqual(self.rsrc1.in_use, 0)
        
    def testReleaseAll2(self):
        "Test: acquire() followed by release results in resource available property value equal to capacity"
        self.process1 = TestProcessBasicRelease(self.rsrc2, 2)
        self.process1.start()
        self.eventProcessor.process_events(ONE_MIN)
        self.assertEqual(self.rsrc2.available, self.rsrc2.capacity)
        
    def testReleaseAll3(self):
        "Test: acquire() followed by release results in resource inUse property value of zero"
        self.process1 = TestProcessBasicRelease(self.rsrc1, 1, 1)
        self.process1.start()
        self.eventProcessor.process_events(ONE_MIN)
        self.process1.release(self.process1.assignment)
        self.assertEqual(self.rsrc1.in_use, 0)
       
    def testAssignment2(self):
        "Test: acquire(2) followed by release(1) results in resource assignment with count of one"
        self.process1 = TestProcessBasicRelease(self.rsrc2, 2, self.rsrc2)
        self.process1.start()
        self.eventProcessor.process_events(ONE_MIN)
        self.assertEqual(self.process1.assignment.count, 1)
    
    def testAssignment2a(self):
        "Test: acquire(2) followed by release(1) (int argument) results in resource assignment with count of one"
        self.process1 = TestProcessBasicRelease(self.rsrc2, 2, 1)
        self.process1.start()
        self.eventProcessor.process_events(ONE_MIN)
        self.assertEqual(self.process1.assignment.count, 1)
        
    def testAcquire2Release1(self):
        "Test: acquire(2) followed by a release(1) results in resource with inUse of 1"
        self.process1 = TestProcessBasicRelease(self.rsrc2, 2, self.rsrc2)
        self.process1.start()
        self.eventProcessor.process_events(ONE_MIN)
        self.assertEqual(self.rsrc2.in_use, 1)
        
    def testAcquire2Release2A(self):
        "Test: acquire(2) followed by tw0 release(1) calls results in resource with inUse of 0"
        self.process1 = TestProcessBasicRelease2(self.rsrc2, 2, 2)
        self.process1.start()
        self.eventProcessor.process_events(ONE_MIN)
        self.assertEqual(self.rsrc2.in_use, 0)
        
    def testAcquire2Release2B(self):
        "Test: acquire(2) followed by release(2) calls results in resource with inUse of 0"
        self.process1 = TestProcessBasicRelease(self.rsrc2, 2, 2)
        self.process1.start()
        self.eventProcessor.process_events(ONE_MIN)
        self.assertEqual(self.rsrc2.in_use, 0)
        
    def testAcquire2Release2C(self):
        "Test: acquire(2) followed by release(rsrc, rsrc) calls results in resource with inUse of 0"
        self.process1 = TestProcessBasicRelease(self.rsrc2, 2, (self.rsrc2, self.rsrc2))
        self.process1.start()
        self.eventProcessor.process_events(ONE_MIN)
        self.assertEqual(self.rsrc2.in_use, 0)
        
    def testAcquire2Release2Assignment(self):
        "Test: acquire(2) followed by tw release(1) (resource instance) calls results in resource with count of 0"
        self.process1 = TestProcessBasicRelease(self.rsrc2, 2, (self.rsrc2, self.rsrc2))
        self.process1.start()
        self.eventProcessor.process_events(ONE_MIN)
        self.assertEqual(self.process1.assignment.count, 0)
        
    def testAcquire2Release2AssignmentA(self):
        "Test: acquire(2) followed by twp release(1) calls results in resource with count of 0"
        self.process1 = TestProcessBasicRelease2(self.rsrc2, 2, 2)
        self.process1.start()
        self.eventProcessor.process_events(ONE_MIN)
        self.assertEqual(self.process1.assignment.count, 0)
        
    def testReleaseMoreThanAssigned(self):
        "Test: acquire(1) followed by release(2) raises an error"
        self.process1 = TestProcessBasicRelease(self.rsrc2, 1)
        self.process1.start()
        self.eventProcessor.process_events(0)
        ra = self.process1.assignment
        self.assertRaises(SimError, lambda:  self.process1.release(ra, 2))
        
    def testReleaseMoreThanAssigned2(self):
        "Test: acquire(1) followed by two release(1) calls raises an error"
        self.process1 = TestProcessBasicRelease(self.rsrc2, 1, 1)
        self.process1.start()
        self.eventProcessor.process_events(ONE_MIN)
        self.assertRaises(SimError, lambda: self.process1.release(self.process1.assignment, 1))
        
    def testReleaseMoreThanAssigned3(self):
        "Test: acquire(1) followed by release(2) raises an error"
        self.process1 = TestProcessBasicRelease(self.rsrc2, 1)
        self.process1.start()
        self.eventProcessor.process_events(0)
        ra = self.process1.assignment
        self.assertRaises(SimError, lambda:  self.process1.release(ra, (self.rsrc2, self.rsrc2)))
        
    def testReleaseWrongResource(self):
        "Test: acquire(1) followed by release() on wrong resource raises an error"
        self.process1 = TestProcessBasicRelease(self.rsrc2, 1)
        self.process1.start()
        self.eventProcessor.process_events(0)
        ra = self.process1.assignment
        self.assertRaises(SimError, lambda:  self.process1.release(ra, self.rsrc1))

class TestProcess1a(TestProcess1):
    """
    """
    def run(self):
        self.assignment = self.acquire(self.testcase.rsrc)
        self.wait_for(TWO_MINS)
        self.release(self.assignment)

        
class SimpleResourceAcquireQueueingTests(RATestCaseBase):
    """
    Tests SimpleResource class acquisition from multiple processes, including
    queued (unfulfilled) acquisition requests. 
    
    If SimpleResource acquire() requests are fulfilled in priority (as
    opposed to FIFO) order, they should end up in the following order:
    3, 5, 1, 4, 2
    """
    def setUp(self):
        super().setUp()
        #simevent.initialize()
        #self.eventProcessor = simevent.EventProcessor()        
        TestProcess1.initialize()
        self.process1 = TestProcess1a(self, 2)
        self.process2 = TestProcess1a(self, 3)
        self.process3 = TestProcess1a(self, 1)
        self.process4 = TestProcess1a(self, 2)
        self.process5 = TestProcess1a(self, 1)
        self.rsrc = SimSimpleResource("TestResource1", self.location)
        self.process1.start()
        self.process2.start()
        self.process3.start()
        self.process4.start()
        self.process5.start()
             
    def testAccquire1(self):
        "Test: first acquire() on resource with capacity 1 does not result in a wait"
        self.eventProcessor.process_events(0)
        self.assertFalse(self.process1.waiting)
        
    def testAccquire2(self):
        "Test: second acquire() on resource with capacity 1 does result in a wait"
        self.eventProcessor.process_events(0)
        self.assertTrue(self.process2.waiting)
        
    def testAccquire3(self):
        "Test: 3 acquires, one release, process2 is not waiting"
        self.eventProcessor.process_events(TWO_MINS)
        self.assertFalse(self.process2.waiting)
        
    def testAccquire4(self):
        "Test: 4 acquires, one release at 2 mimic, assigned processes are [1, 2]"
        self.eventProcessor.process_events(TWO_MINS)
        self.assertEqual(TestProcess1.pids(), [1,2])
        
    def testAccquire5(self):
        "Test: 5 acquires, 4 releases, assigned processes are [1,2,3,4,5]"
        self.eventProcessor.process_events(EIGHT_MINS)
        self.assertEqual(TestProcess1.pids(), [1,2,3,4,5])
        
    def testAccquire6(self):
        "Test: using priority 5 acquires, 4 releases, assigned processes are [3,5,1,4,2]"
        self.rsrc.register_priority_func(SimMsgType.RSRC_REQUEST, 
                                       TestProcess1.getPriority)
        self.eventProcessor.process_events(EIGHT_MINS)
        self.assertEqual(TestProcess1.pids(), [3,5,1,4,2])
        
    def testAccquire7(self):
        "Test: resource capacity 3: 5 acquires, 2 releases, assigned processes are [1,2,3,4,5]"
        self.rsrc = SimSimpleResource("TestResource2", self.location, capacity=3)
        self.eventProcessor.process_events(FOUR_MINS)
        self.assertEqual(TestProcess1.pids(), [1,2,3,4,5])
        

class TestProcess1b(TestProcess1):
    """
    """
    def run(self):
        self.runfunc()


class BasicResourcePoolTests(RATestCaseBase):
    """
    Tests basic usage of a resource pool
    """
    def setUp(self):
        super().setUp()
        self.rsrc1 = SimSimpleResource("TestResource1", self.location)
        self.rsrc2 = SimSimpleResource("TestResource2", self.location, capacity=2)
        self.rsrc3 = TestResource("TestResource3", self.location, capacity=2)
        self.rsrc4 = SimSimpleResource("TestResource4", self.location, capacity=2)
        self.pool = SimResourcePool(self.rsrc1, self.rsrc2, self.rsrc3, self.rsrc4)
        TestProcess1.initialize()
        self.process1 = TestProcess1b(BasicResourcePoolTests)
        self.process2 = TestProcess1b(BasicResourcePoolTests)
        
        
    def testadd1(self):
        "Test: add a resource to the pool, confirm new pool size"
        initialsize = self.pool.poolsize()
        resource = SimSimpleResource("TestResource5", self.location, capacity=2)
        self.pool.add_resource(resource)
        self.assertEqual(self.pool.poolsize(), initialsize + 2)
        
    def testadd2(self):
        "Test: re-adding a resource to the pool raises an error"
        self.assertRaises(SimError, lambda: self.pool.add_resource(self.rsrc2))
          
    def testadd3(self):
        "Test: putting a resource in two pools raises an error"
        pool2 = SimResourcePool()
        self.assertRaises(SimError, lambda: pool2.add_resource(self.rsrc2))
             
    def testpoolsize1(self):
        "Test: Total pool size is 7"
        self.assertEqual(self.pool.poolsize(), 7)
             
    def testpoolsize2(self):
        "Test: Pool size for SimSimpleResources is 7"
        self.assertEqual(self.pool.poolsize(SimSimpleResource), 7)
             
    def testpoolsize3(self):
        "Test: Pool size for TestResources is 2"
        self.assertEqual(self.pool.poolsize(TestResource), 2)
             
    def testInitialAvailable1(self):
        "Test: Total available (initially) is 7"
        self.assertEqual(self.pool.available(), 7)
             
    def testInitialAvailable2(self):
        "Test: Total available (initially) of SimSimpleResources is 7"
        self.assertEqual(self.pool.available(SimSimpleResource), 7)
             
    def testInitialAvailable3(self):
        "Test: Total available (initially) if TestResources is 2"
        self.assertEqual(self.pool.available(TestResource), 2)
             
    def testresources1(self):
        "Test: Total resources in pool"
        expected = [self.rsrc1, self.rsrc2, self.rsrc3, self.rsrc4]
        self.assertEqual(self.pool.resources(), expected)
             
    def testresources2(self):
        "Test: Total SimSimpleResource resources in pool"
        expected = [self.rsrc1, self.rsrc2, self.rsrc3, self.rsrc4]
        self.assertEqual(self.pool.resources(SimSimpleResource), expected)
             
    def testresources3(self):
        "Test: Total TestResource resources in pool"
        expected = [self.rsrc3,]
        self.assertEqual(self.pool.resources(TestResource), expected)
             
    def testavailableresources1(self):
        "Test: Total (initial) available resources in pool"
        expected = [self.rsrc1, self.rsrc2, self.rsrc3, self.rsrc4]
        self.assertEqual(self.pool.available_resources(), expected)
             
    def testavailableresources2(self):
        "Test: (initial) TestResource available resources in pool"
        expected = [self.rsrc3,]
        self.assertEqual(self.pool.available_resources(TestResource), expected)
             
    def testcurrentAssignments1(self):
        "Test: Total (initial) current assignments in pool is empty"
        self.assertEqual(list(self.pool.current_assignments()), [])
             
    def testcurrentAssignments2(self):
        "Test: (initial) current assignments involving TestResource in pool is empty"
        self.assertEqual(list(self.pool.current_assignments(TestResource)), [])
             
    def testcurrenttransactions1(self):
        "Test: Total (initial) current assignments in pool is empty"
        self.assertEqual(self.pool.current_transactions(), [])
             
    def testcurrenttransactions2(self):
        "Test: TestResource (initial) current assignments in pool is empty"
        self.assertEqual(self.pool.current_transactions(TestResource), [])
             
    def testacquire1(self):
        "Test: Acquire one of any resource from the pool - should be the first"
        def runfunc():
            process = self.process1
            process.assignment = process.acquire_from(self.pool, SimResource)
            process.wait_for(ONE_MIN)
            
        self.process1.runfunc = runfunc
        self.process1.start()
        self.eventProcessor.process_events(0)        
        self.assertEqual(self.process1.assignment.resource, self.rsrc1)
             
    def testacquire2(self):
        "Test: Acquire three of any resource from the pool, followed by 2"
        def runfunc():
            process = self.process1
            process.assignment = process.acquire_from(self.pool, SimResource, 3)
            process.assignment = process.acquire_from(self.pool, SimResource, 2)
            process.wait_for(ONE_MIN)
            
        self.process1.runfunc = runfunc
        self.process1.start()
        self.eventProcessor.process_events(0)        
        expected = (self.rsrc3, self.rsrc3)
        self.assertEqual(self.process1.assignment.resources, expected)
             
    def testacquire3(self):
        "Test: Acquire all seven resources in the pool"
        def runfunc():
            process = self.process1
            process.assignment = process.acquire_from(self.pool, SimResource, 7)
            process.wait_for(ONE_MIN)
            
        self.process1.runfunc = runfunc
        self.process1.start()
        self.eventProcessor.process_events(0)        
        self.assertEqual(len(self.process1.assignment.resources), 7)
             
    def testacquire4(self):
        "Test: Acquire a TestResource"
        def runfunc():
            process = self.process1
            process.assignment = process.acquire_from(self.pool, TestResource, 1)
            process.wait_for(ONE_MIN)
            
        self.process1.runfunc = runfunc
        self.process1.start()
        self.eventProcessor.process_events(0)
        expected = (self.rsrc3, )
        self.assertEqual(self.process1.assignment.resources, expected)
             
             
    def testacquire5(self):
        "Test: Acquire a specific resource from the pool"
        def runfunc():
            process = self.process1
            process.assignment = process.acquire(self.rsrc1)
            process.wait_for(ONE_MIN)
            
        self.process1.runfunc = runfunc
        self.process1.start()
        self.eventProcessor.process_events(0)
        expected = (self.rsrc1, )
        self.assertEqual(self.process1.assignment.resources, expected)

    def testavailable2(self):
        "Test: Acquire three of any resource from the pool, followed by 2 - available "
        def runfunc():
            process = self.process1
            process.assignment = process.acquire_from(self.pool, SimResource, 3)
            process.assignment = process.acquire_from(self.pool, SimResource, 2)
            process.wait_for(ONE_MIN)
            
        self.process1.runfunc = runfunc
        self.process1.start()
        self.eventProcessor.process_events(0)        
        self.assertEqual(self.pool.available(), 2)
             
    def testavailable3(self):
        "Test: Acquire three of any resource from the pool, followed by 2 - available TestResources "
        def runfunc():
            process = self.process1
            process.assignment = process.acquire_from(self.pool, SimResource, 3)
            process.assignment = process.acquire_from(self.pool, SimResource, 2)
            process.wait_for(ONE_MIN)
            
        self.process1.runfunc = runfunc
        self.process1.start()
        self.eventProcessor.process_events(0)        
        self.assertEqual(self.pool.available(TestResource), 0)
             
    def testavailableresources32(self):
        "Test: Acquire three of any resource from the pool, followed by 2 - availableResources "
        def runfunc():
            process = self.process1
            process.assignment = process.acquire_from(self.pool, SimResource, 3)
            process.assignment = process.acquire_from(self.pool, SimResource, 2)
            process.wait_for(ONE_MIN)
            
        self.process1.runfunc = runfunc
        self.process1.start()
        self.eventProcessor.process_events(0)        
        self.assertEqual(self.pool.available_resources(), [self.rsrc4])
             
    def testcurrentAssignments32(self):
        "Test: Acquire three of any resource from the pool, followed by 2 - currentAssignments "
        def runfunc1():
            process1 = self.process1
            process1.assignment = process1.acquire_from(self.pool, SimResource, 3)
            process1.wait_for(ONE_MIN)
            
        def runfunc2():
            process2 = self.process2
            process2.assignment = process2.acquire_from(self.pool, SimResource, 2)
            process2.wait_for(ONE_MIN)
            
        self.process1.runfunc = runfunc1
        self.process2.runfunc = runfunc2
        self.process1.start()
        self.process2.start()
        self.eventProcessor.process_events(0)        
        ra1 = self.process1.assignment
        ra2 = self.process2.assignment
        self.assertEqual(set(self.pool.current_assignments()), set([ra1, ra2]))
             
    def testcurrentTransactions32(self):
        "Test: Acquire three of any resource from the pool, followed by 2 - currentTransactions "
        def runfunc1():
            process1 = self.process1
            process1.assignment = process1.acquire_from(self.pool, SimResource, 3)
            process1.wait_for(ONE_MIN)
            
        def runfunc2():
            process2 = self.process2
            process2.assignment = process2.acquire_from(self.pool, SimResource, 2)
            process2.wait_for(ONE_MIN)
            
        self.process1.runfunc = runfunc1
        self.process2.runfunc = runfunc2
        self.process1.start()
        self.process2.start()
        self.eventProcessor.process_events(0)        
        ra1 = self.process1.assignment
        ra2 = self.process2.assignment
        expected = (self.process1, self.process2)
        self.assertEqual(set(self.pool.current_transactions()), set(expected))
             
    def testacquiremorethanpoolsize1(self):
        "Test: Acquire 8 of any resource (bigger than the pool) raises "
        def runfunc():
            process = self.process1
            process.exception = None
            try:
                process.assignment = process.acquire_from(self.pool, SimResource, 8)
            except Exception as e:
                process.exception = e
            process.wait_for(ONE_MIN)
            
        self.process1.runfunc = runfunc
        self.process1.start()
        self.eventProcessor.process_events(0)        
        self.assertTrue(isinstance(self.process1.exception, SimError))
             
    def testacquiremorethanpoolsize2(self):
        "Test: Acquire 3 of TestResource (bigger than the pool) raises "
        def runfunc():
            process = self.process1
            process.exception = None
            try:
                process.assignment = process.acquire_from(self.pool, TestResource, 3)
            except Exception as e:
                process.exception = e
            process.wait_for(ONE_MIN)
            
        self.process1.runfunc = runfunc
        self.process1.start()
        self.eventProcessor.process_events(0)        
        self.assertTrue(isinstance(self.process1.exception, SimError))



class BasicResourcePoolReleaseTests(RATestCaseBase):
    """
    Tests basic usage of a resource pool
    """
    def setUp(self):
        super().setUp()
        self.rsrc1 = SimSimpleResource("TestResource1", self.location)
        self.rsrc2 = SimSimpleResource("TestResource2", self.location, capacity=2)
        self.rsrc3 = TestResource("TestResource3", self.location, capacity=2)
        self.rsrc4 = SimSimpleResource("TestResource4", self.location, capacity=2)
        self.pool = SimResourcePool(self.rsrc1, self.rsrc2, self.rsrc3, self.rsrc4)
        TestProcess1.initialize()
        self.process1 = TestProcess1b(self)
        self.process2 = TestProcess1b(self)
        
        def runfunc1():
            process1 = self.process1
            process1.assignment = process1.acquire_from(self.pool, SimSimpleResource, 2)
            process1.wait_for(ONE_MIN)
            
        def runfunc2():
            process2 = self.process2
            process2.assignment = process2.acquire_from(self.pool, TestResource, 1)
            process2.wait_for(ONE_MIN)
            
        self.process1.runfunc = runfunc1
        self.process2.runfunc = runfunc2
        self.process1.start()
        self.process2.start()
        self.eventProcessor.process_events(0)        
        self.ra1 = self.process1.assignment
        self.ra2 = self.process2.assignment        
                           
    def testavailable1(self):
        "Test: Total available is 6 following release of assignment 1"
        self.process1.release(self.ra1)
        self.assertEqual(self.pool.available(), 6)
             
    def testavailable2(self):
        "Test: TestResource available is 1 following release of assignment 1"
        self.process1.release(self.ra1)
        self.assertEqual(self.pool.available(TestResource), 1)
                          
    def testavailable3(self):
        "Test: Total available is 5 following partial release of assignment2"
        self.process1.release(self.ra1, self.rsrc1)
        self.assertEqual(self.pool.available(), 5)
                          
    def testavailable4(self):
        "Test: Total available is 6 following partial release (n=1) of assignment 1"
        self.process1.release(self.ra1, 1)
        self.assertEqual(self.pool.available(), 5)
                          
    def testavailable5(self):
        "Test: Total available is 6 following explicit n=2 release of assignment 1"
        self.process1.release(self.ra1, 2)
        self.assertEqual(self.pool.available(), 6)
                           
    def testavailable6(self):
        "Test: Total available is 2 following release of assignment2"
        self.process2.release(self.ra2)
        self.assertEqual(self.pool.available(TestResource), 2)
             
    def testavailableresources1(self):
        "Test: Total (initial) available resources in pool after partial release of assignment 2"
        self.process1.release(self.ra1, self.rsrc2)
        expected = [self.rsrc2, self.rsrc3, self.rsrc4]
        self.assertEqual(self.pool.available_resources(), expected)
             
    def testavailableresources2(self):
        "Test: Total (initial) available resources in pool after partial release of assignment 2"
        self.process1.release(self.ra1, self.rsrc1)
        expected = [self.rsrc1, self.rsrc2, self.rsrc3, self.rsrc4]
        self.assertEqual(self.pool.available_resources(), expected)
             
    def testcurrentAssignments1(self):
        "Test: Total current assignments after release of assignment 1"
        self.process1.release(self.ra1)
        expected = (self.ra2,)
        self.assertEqual(set(self.pool.current_assignments()), set(expected))
             
    def testcurrentAssignments2(self):
        "Test: Total current assignments after partial release of assignment 1"
        self.process1.release(self.ra1, self.rsrc2)
        expected = (self.ra1, self.ra2)
        self.assertEqual(set(self.pool.current_assignments()), set(expected))
             
    def testcurrentTransactions1(self):
        "Test: Total current transactions after release of assignment 1"
        self.process1.release(self.ra1)
        expected = (self.process2,)
        self.assertEqual(set(self.pool.current_transactions()), set(expected))
             
    def testcurrentTransactions2(self):
        "Test: Total current transactions after partial release of assignment 1"
        self.process1.release(self.ra1, self.rsrc2)
        expected = (self.process1, self.process2)
        self.assertEqual(set(self.pool.current_transactions()), set(expected))


class TestProcess1c(TestProcess1):
    """
    """
    def run(self):
        if self.runfunc is not None:
            self.runfunc()
        else:
            if self.wait is None:
                self.wait = TWO_MINS
            self.assignment = self.acquire_from(self.testcase.pool, SimSimpleResource, 2)
            self.wait_for(self.wait)
            self.release(self.assignment)
            
            

class ResourcePoolQueueingTests(RATestCaseBase):
    """
    Tests SimResourcePool resource acquisition from multiple processes,
    including queued (unfulfilled) acquisition requests.
    
    If acquireFrom() requests are fulfilled in priority (as opposed to FIFO)
    order, they should end up in the following order: 1,3,5,4,2.
    """
    def setUp(self):
        super().setUp()
        TestProcess1.initialize()
        self.process1 = TestProcess1c(self, 2)
        self.process2 = TestProcess1c(self, 3)
        self.process3 = TestProcess1c(self, 1)
        self.process4 = TestProcess1c(self, 2)
        self.process5 = TestProcess1c(self, 1)
        self.process = [self.process1, self.process2, self.process3, self.process4, self.process5]
        
        for i in range(5):
            self.process[i].runfunc = None
            self.process[i].wait = None
                
        self.rsrc1 = SimSimpleResource("TestResource1", self.location)
        self.rsrc2 = SimSimpleResource("TestResource2", self.location, capacity=2)
        self.rsrc3 = SimSimpleResource("TestResource3", self.location, capacity=2)
        self.rsrc4 = TestResource("TestResource4", self.location, capacity=2)
        self.rsrc = [self.rsrc1, self.rsrc2, self.rsrc3, self.rsrc4]
        self.pool = SimResourcePool(self.rsrc1, self.rsrc2, self.rsrc3, self.rsrc4)
             
    def testacquireFIFOnorelease(self):
        """
        Test: Acquire two resources for each process. Without any releases,
        the first three process will be assigned
        """
        self.process1.start()
        self.process2.start()
        self.process3.start()
        self.process4.start()
        self.process5.start()
        self.eventProcessor.process_events(0)        
        self.assertEqual(TestProcess1.pids(), [1,2,3])
             
    def testacquireFIFOnorelease2(self):
        """
        Test: Acquire one SimSimpleResource for process1, 2 for the rest, no releases: first 4 assigned
        """
        def runfunc():
            p = self.process1
            p.assignment = p.acquire_from(self.pool, SimSimpleResource, 1)
            p.wait_for(TWO_MINS)
            p.release(p.assignment)
            
        self.process1.runfunc = runfunc
        self.process1.start()
        self.process2.start()
        self.process3.start()
        self.process4.start()
        self.process5.start()
        self.eventProcessor.process_events(0)        
        self.assertEqual(TestProcess1.pids(), [1,2,3, 4])
             
    def testacquireFIFOrelease1(self):
        """
        Test: Acquire two resources for each process. Release the
        first process's assignment; four process requests are fulfilled
        """
        def runfunc1():
            self.process1.assignment = self.process1.acquire_from(self.pool, SimSimpleResource, 2)
            self.process1.wait_for(ONE_MIN)
            self.process1.release(self.process1.assignment)
            
        self.process1.runfunc = runfunc1
        self.process1.start()
        self.process2.start()
        self.process3.start()
        self.process4.start()
        self.process5.start()
        self.eventProcessor.process_events(ONE_MIN)        
        self.assertEqual(TestProcess1.pids(), [1,2,3,4])
             
    def testacquireFIFOrelease1a(self):
        """
        Test: Acquire two resources for each process. Release one of the
        resources for the first process's assignment; four process requests
        are fulfilled
        """
        def runfunc1():
            self.process1.assignment = self.process1.acquire_from(self.pool, SimSimpleResource, 2)
            self.process1.wait_for(ONE_MIN)
            self.process1.release(self.process1.assignment, 1)
            self.process1.wait_for(ONE_MIN)
            self.process1.release(self.process1.assignment)
            
        self.process1.runfunc = runfunc1
        self.process1.start()
        self.process2.start()
        self.process3.start()
        self.process4.start()
        self.process5.start()
        self.eventProcessor.process_events(ONE_MIN)        
        self.assertEqual(TestProcess1.pids(), [1,2,3,4])
             
    def testacquireFIFOrelease3(self):
        """
        Test: Acquire two resources for each process. Release one of the
        resources for the processes 1-3; all requests are fulfilled
        """
        def runfunc(process):
            process.assignment = process.acquire_from(self.pool, SimSimpleResource, 2)
            process.wait_for(ONE_MIN)
            process.release(process.assignment, 1)
            process.wait_for(ONE_MIN)
            process.release(process.assignment)
            
        def runfunc1(): runfunc(self.process1)
        def runfunc2(): runfunc(self.process2)
        def runfunc3(): runfunc(self.process3)
            
        self.process1.runfunc = runfunc1
        self.process2.runfunc = runfunc2
        self.process3.runfunc = runfunc3
        self.process1.start()
        self.process2.start()
        self.process3.start()
        self.process4.start()
        self.process5.start()
        self.eventProcessor.process_events(ONE_MIN)        
        self.assertEqual(TestProcess1.pids(), [1,2,3,4,5])
             
    def testacquireFIFOTestResource(self):
        """
        Test - acquire_from() blocks on request for third Test Resource.
        Since the last request is for a superclass of TestResource (and
        such a resource is available) it is assigned, since the higher
        priority process wants just the TestResource subclass.
        """
        def runfunc(process, rsrc_cls, n):
            process.assignment = process.acquire_from(self.pool, rsrc_cls, n)
            process.wait_for(ONE_MIN)
            
        def f1(): runfunc(self.process1, SimSimpleResource, 1)
        def f2(): runfunc(self.process2, TestResource,2)
        def f3(): runfunc(self.process3, SimSimpleResource, 1)
        def f4(): runfunc(self.process4, TestResource, 1)
        def f5(): runfunc(self.process5, SimSimpleResource, 1)
        
        runfuncs = [f1, f2, f3, f4, f5]
        for i in range(5):
            self.process[i].runfunc = runfuncs[i]
            self.process[i].start()
            
        self.eventProcessor.process_events(0)        
        self.assertEqual(TestProcess1.pids(), [1,2,3,5])
             
    def testacquirePriorityrelease1(self):
        """
        Test: Using a priority queue, request TestResources; after the first
        request, requests are fulfilled in priority order
        """
        def runfunc(process, rsrc_cls, n, wait=TWO_MINS):
            process.assignment = process.acquire_from(self.pool, rsrc_cls, n)
            process.wait_for(wait)
            process.release(process.assignment)
            
        def f1(): runfunc(self.process1, TestResource, 2)
        def f2(): runfunc(self.process2, TestResource, 1)
        def f3(): runfunc(self.process3, TestResource, 1, ONE_MIN)
        def f4(): runfunc(self.process4, TestResource, 1)
        def f5(): runfunc(self.process5, TestResource, 1)           
        runfuncs = [f1, f2, f3, f4, f5]
        
        self.pool.register_priority_func(SimMsgType.RSRC_REQUEST, 
                                         TestProcess1.getPriority)
        for i in range(5):
            self.process[i].runfunc = runfuncs[i]
            self.process[i].start()
            
        self.eventProcessor.process_events(ONE_MIN)
        self.assertEqual(TestProcess1.pids(), [3,5])
             
    def testacquirePriorityrelease2(self):
        """
        Test: Using a priority queue, request TestResources; after the first
        request, requests are fulfilled in priority order - so an earlier
        (but lower priority) request for an available SimSimpleResource 
        is not fulfilled.
        """
        self.pool.register_priority_func(SimMsgType.RSRC_REQUEST, 
                                       TestProcess1.getPriority)
                
        def runfunc(process, rsrc_cls, n, wait=TWO_MINS):
            process.assignment = process.acquire_from(self.pool, rsrc_cls, n)
            process.wait_for(wait)
            process.release(process.assignment)
            
        def f1(): runfunc(self.process1, TestResource, 1)
        def f2(): runfunc(self.process2, TestResource, 1)
        def f3(): runfunc(self.process3, TestResource, 1, ONE_MIN)
        def f4(): runfunc(self.process4, SimSimpleResource, 1)
        def f5(): runfunc(self.process5, TestResource, 2)
        
        runfuncs = [f1, f2, f3, f4, f5]
        for i in range(5):
            self.process[i].runfunc = runfuncs[i]
            self.process[i].start()
            
        self.eventProcessor.process_events(ONE_MIN)
        
        # After process3 releases, process5 is assigned a TestResource,
        # but process1 (the next in the priority queue, due to being
        # queued before process4) is not. Because process4 requested a
        # class for which resources are available (SimSimpleResource),
        # it is assigned, thanks to the process_queued_requests()
        # algorithm implemented by SimResourcePool.      
        self.assertEqual(TestProcess1.pids(), [3, 4, 5]) 
 
    def testacquireSpecificResource1(self):
        """
        Test: A specified resource can be acquired from a pool
        """
        def runfunc(process, rsrc, wait):
            process.assignment = process.acquire(rsrc)
            process.wait_for(wait)
            process.release(process.assignment)
            
        def f1(): runfunc(self.process1, self.rsrc1, TWO_MINS)
        self.process1.runfunc = f1
        self.process1.start()
        self.eventProcessor.process_events(ONE_MIN)        
        
        self.assertIs(self.process1.assignment.resource, self.rsrc1)
 
    def testacquireSpecificResource2(self):
        """
        Test: acquisition of specific TestResource for process5 fails because higher priority process blocked acquiring superclass
        """
        def runfunc5():
            process = self.process5
            process.assignment = process.acquire(self.rsrc4)
            process.wait_for(TWO_MINS)
            process.release(process.assignment)
            
        self.process5.runfunc = runfunc5
        for i in range(5):           
            self.process[i].start()
            
        self.eventProcessor.process_events(0)        
        self.assertEqual(TestProcess1.pids(), [1,2,3])
 
    def testacquireResourceSubclass1(self):
        """
        Test: acquisition of any TestResource for process5 fails because higher priority process blocked acquiring superclass
        """
        def runfunc5():
            process = self.process5
            process.assignment = process.acquire_from(self.pool, TestResource)
            process.release(process.assignment)
            
        self.process5.runfunc = runfunc5
        for i in range(5):           
            self.process[i].start()
            
        self.eventProcessor.process_events(0)        
        self.assertEqual(TestProcess1.pids(), [1,2,3])
 
    def testacquireResourceSubclass2(self):
        """
        Test: acquisition of any superclass SimSimpleResource not blocked higher priority processes blocked acquiring subclass TestResource
        """
        def runfunc(process):
            process.assignment = process.acquire_from(self.pool, TestResource)
            process.wait_for(TWO_MINS)
            process.release(process.assignment)
            
        def f1(): runfunc(self.process1)
        def f2(): runfunc(self.process2)
        def f3(): runfunc(self.process3)
        def f4(): runfunc(self.process4)
        f = [f1, f2, f3, f4]
                      
        for i in range(4):
            self.process[i].runfunc = f[i]
            self.process[i].start()
        
        self.process5.start()
                        
        self.eventProcessor.process_events(0)        
        self.assertEqual(TestProcess1.pids(), [1,2,5])

    
class ResourcePoolRequestProcessingTests(unittest.TestCase):
    """
    Test potential race conditions that occur with simulated simultaneous
    events, e.g. that if two processes attempt to acquire the same resource
    at the same simulated  time, the higher one gets it even if the lower
    priority process called acquire() first
    """
    def setUp(self):
        simevent.initialize()
        SimClock.initialize()
        SimStaticObject.elements = {}        
        self.eventProcessor = simevent.EventProcessor()        
                 
        rsrc = SimSimpleResource("TestResource")
        rsrc.register_priority_func(SimMsgType.RSRC_REQUEST, 
                                    TestProcess2.getPriority)
        TestProcess2.rsrc = rsrc
        
        rsrc2 = SimSimpleResource("TestResource2")
        rsrc2.register_priority_func(SimMsgType.RSRC_REQUEST, 
                                    TestProcess2.getPriority)
        TestProcess2.rsrc2 = rsrc2
        
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimStaticObject.elements = {}    

class TestProcess2(SimProcess):
    rsrc = None
    rsrc2 = None
    #source = MockSource()
    
    def __init__(self, priority=1, rsrc=None, *, timeout=None):
        super().__init__()
        self.priority = priority
        self.rsrc = rsrc
        if rsrc is None:
            self.rsrc = TestProcess2.rsrc
        self.wait_before_acquire = 0
        self.exception = None
        self.waitdone_time = None
        self.timeout = timeout
        self.has_resource = False
        self.completed = False
        entity = MockEntity(TestProcess1.source, self)
        
    def run(self):
        try:
            self.runimpl()
        except Exception as e:
            self.exception = e
        finally:
            self.waitdone_time = SimClock.now()
    
    def runimpl(self):
        if self.wait_before_acquire > 0:         
            self.wait_for(self.wait_before_acquire)
        assignment = self.acquire(self.rsrc, timeout=self.timeout)
        self.has_resource = True
        self.wait_for(TWO_MINS)
        self.release(assignment)
        self.completed = True    
                
    @staticmethod
    def getPriority(msg):
        process = msg.msgData[0]
        return process.priority


class TestProcess2a(TestProcess2):
    def runimpl(self):
        try:
            assignment = self.acquire(TestProcess2.rsrc, timeout=self.timeout)
            self.has_resource = True
            self.rsrc = TestProcess2.rsrc
            self.wait_for(TWO_MINS)
            self.release(assignment)
            self.completed = True
        except SimTimeOutException:
            assignment = self.acquire(TestProcess2.rsrc2, timeout=0)
            self.has_resource = True
            self.rsrc = TestProcess2.rsrc2
            self.wait_for(TWO_MINS)
            self.release(assignment)
            self.completed = True
    
class AcquireTimeoutTests(unittest.TestCase):
    """
    Test potential race conditions that occur with simulated simultaneous
    events, e.g. that if two processes attempt to acquire the same resource
    at the same simulated  time, the higher one gets it even if the lower
    priority process called acquire() first
    """
    def setUp(self):
        simevent.initialize()
        SimClock.initialize()
        SimStaticObject.elements = {}        
        self.eventProcessor = simevent.EventProcessor()        
                 
        rsrc = SimSimpleResource("TestResource")
        rsrc.register_priority_func(SimMsgType.RSRC_REQUEST, 
                                    TestProcess2.getPriority)
        TestProcess2.rsrc = rsrc
        
        rsrc2 = SimSimpleResource("TestResource2")
        rsrc2.register_priority_func(SimMsgType.RSRC_REQUEST, 
                                    TestProcess2.getPriority)
        TestProcess2.rsrc2 = rsrc2
        
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimStaticObject.elements = {}
        
    def testNoTimeout1(self):
        """
        Test: process with timeout of zero doesn't timeout if it acquires resource right away
        """
        p = TestProcess2(priority=2, timeout=0)
        p.start()
        self.eventProcessor.process_events(until_time=ONE_MIN)
        self.assertEqual(p.exception, None)
        
    def testNoTimeout2(self):
        """
        Test: process with timeout > 0 doesn't timeout if it acquires resource right away
        """
        p = TestProcess2(priority=2, timeout=ONE_MIN)
        p.start()
        self.eventProcessor.process_events(until_time=ONE_MIN)
        self.assertEqual(p.exception, None)
        
    def testNoTimeout3(self):
        """
        Test: Advancing clock doesn't effect same test as NoTimeout2
        """
        p = TestProcess2(priority=2, timeout=ONE_MIN)
        SimClock.advance_to(TWO_MINS)
        p.start()
        self.eventProcessor.process_events(until_time=FOUR_MINS)
        self.assertEqual(p.exception, None)
        
    def testTimeout1(self):
        """
        Test: low priority process with timeout 0 times out when not acquiring resource
        """
        p1 = TestProcess2(priority=2, timeout=0)
        p1.start()
        p2 = TestProcess2(priority=1, timeout=0)
        p2.start()
        self.eventProcessor.process_events(until_time=ONE_MIN)
        self.assertIsInstance(p1.exception, SimTimeOutException)
        
    def testTimeout2(self):
        """
        Test: low priority process with timeout > 0 times out when not acquiring resource
        """
        p1 = TestProcess2(priority=2, timeout=ONE_MIN)
        p1.start()
        p2 = TestProcess2(priority=1, timeout=0)
        p2.start()
        self.eventProcessor.process_events(until_time=ONE_MIN)
        self.assertIsInstance(p1.exception, SimTimeOutException)
        
    def testNoTimeout4(self):
        """
        Test: low priority process doesn't time out with timeout = service time of higher priority procsss
        """
        p1 = TestProcess2(priority=2, timeout=TWO_MINS)
        p1.start()
        p2 = TestProcess2(priority=1, timeout=0)
        p2.start()
        self.eventProcessor.process_events(until_time=EIGHT_MINS)
        self.assertEqual(p1.exception, None)
        
    def testNoTimeout5(self):
        """
        Test: NoTimeout4 with clock advance before process starts
        """
        SimClock.advance_to(TWO_MINS)
        p1 = TestProcess2(priority=2, timeout=TWO_MINS)
        p1.start()
        p2 = TestProcess2(priority=1, timeout=0)
        p2.start()
        self.eventProcessor.process_events(until_time=EIGHT_MINS)
        self.assertEqual(p1.exception, None)
        
    def testTimeout3(self):
        """
        Test: priority one process p3 times out due to p2
        """
        p1 = TestProcess2(priority=2, timeout=TWO_MINS)
        p1.start()
        p2 = TestProcess2(priority=1, timeout=0)
        p2.start()
        p3 = TestProcess2(priority=1, timeout=ONE_MIN)
        p3.start()
        self.eventProcessor.process_events(until_time=EIGHT_MINS)
        self.assertIsInstance(p3.exception, SimTimeOutException)
        
    def testTimeout4(self):
        """
        Test: Same scenario as timeout3 - p1 does not timeout
        """
        p1 = TestProcess2(priority=2, timeout=TWO_MINS)
        p1.start()
        p2 = TestProcess2(priority=1, timeout=0)
        p2.start()
        p3 = TestProcess2(priority=1, timeout=ONE_MIN)
        p3.start()
        self.eventProcessor.process_events(until_time=EIGHT_MINS)
        self.assertEqual(p1.exception, None)
        
    def testTimeout5(self):
        """
        Test: Same scenario as timeout3, but p2 has two minute TO - p1 does timeout
        """
        p1 = TestProcess2(priority=2, timeout=TWO_MINS)
        p1.start()
        p2 = TestProcess2(priority=1, timeout=0)
        p2.start()
        p3 = TestProcess2(priority=1, timeout=TWO_MINS)
        p3.start()
        self.eventProcessor.process_events(until_time=EIGHT_MINS)
        self.assertIsInstance(p1.exception, SimTimeOutException)
    
    def testTimeoutAlternateRsrc1(self):
        """
        Test: p1 handles timeout by acquiring alternate resource
        """
        p1 = TestProcess2a(priority=2, timeout=0)
        p1.start()
        p2 = TestProcess2(priority=1, timeout=0)
        p2.start()
        self.eventProcessor.process_events(until_time=EIGHT_MINS)
        self.assertIs(p1.rsrc, TestProcess2.rsrc2)
   
    def testTimeoutAlternateRsrc2(self):
        """
        Test: Priority 1 process (p2) gets rsrc; priority 2 process (p1) times out
        immediately attempting to acquire rsrc, acquires rsrc2 instead; priority 3
        process (p3) attempts to acquire rsrc2 straight away, but times out
        because p2 got it first.
        (This is the race condition not handled by initial implementation with
        timeout event of lower priority than resource assign event)
        """
        #print("******** test timeout alt rsrc2 *********")
        p1 = TestProcess2a(priority=2, timeout=0)
        p1.start()
        p2 = TestProcess2(priority=1, timeout=0)
        p2.start()
        p3 = TestProcess2(priority=3, rsrc=TestProcess2.rsrc2, timeout=0)
        p3.start()
        
        self.eventProcessor.process_events(until_time=EIGHT_MINS)
        self.assertIsInstance(p3.exception, SimTimeOutException)
   
    def testTimeoutAlternateRsrc3(self):
        """
        Test: Variation on testTimeoutAlternateRsrc2(self) - p1 times out
        on attempt to acquire rsrc at one minute, p3 waits one minute
        before attempting to acquire rsrc2. Should behave identically to
        the above.
        """
        #print("******** test timeout alt rsrc2 *********")
        p1 = TestProcess2a(priority=2, timeout=ONE_MIN)
        p1.start()
        p2 = TestProcess2(priority=1, timeout=0)
        p2.start()
        p3 = TestProcess2(priority=3, rsrc=TestProcess2.rsrc2, timeout=0)
        p3.wait_before_acquire = ONE_MIN
        p3.start()
        
        self.eventProcessor.process_events(until_time=EIGHT_MINS)
        self.assertIsInstance(p3.exception, SimTimeOutException)


class AssignmentRaceConditionTests(unittest.TestCase):
    """
    Test potential race conditions that occur with simulated simultaneous
    events, e.g. that if two processes attempt to acquire the same resource
    at the same simulated  time, the higher one gets it even if the lower
    priority process called acquire() first
    """
    def setUp(self):
        simevent.initialize()
        SimClock.initialize()
        SimStaticObject.elements = {}
        
        self.eventProcessor = simevent.EventProcessor()        
        #self.location = MockLocation()
        #self.source = MockSource()
        self.processes = []
        for i in range(5):
            process = TestProcess2(priority=i)
            self.processes.append(process)
         
        self.process0 = self.processes[0]
        self.process1 = self.processes[1]
        self.process2 = self.processes[2]
        self.process3 = self.processes[3]
        self.process4 = self.processes[4]
        
        rsrc = SimSimpleResource("TestResource")
        rsrc.register_priority_func(SimMsgType.RSRC_REQUEST, 
                                    TestProcess2.getPriority)
        TestProcess2.rsrc = rsrc
        
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimStaticObject.elements = {}
        
    def testConcurrentRequests1(self):
        """
        Test start process 1 then 2, run < 2 minutes, both are executing
        """
        self.process1.start()
        self.process0.start()
        self.eventProcessor.process_events(until_time=ONE_MIN)
        self.assertTrue(self.process0.is_executing and self.process1.is_executing)
        
    def testConcurrentRequests2(self):
        """
        Test start process 1 then 0, run < 2 minutes, higher priority process0 has
        a resource, 1 does not
        """
        self.process1.start()
        self.process0.start()
        self.eventProcessor.process_events(until_time=ONE_MIN)
        self.assertTrue(self.process0.has_resource and not self.process1.has_resource)
        
    def testConcurrentRequestsAfterRelease(self):
        """
        Test start process 2 then 1, run < 2 minutes, process2 has a resource, 1 does not
        """
        self.process1.wait_before_acquire = TWO_MINS
        self.process2.wait_before_acquire = TWO_MINS
        self.process2.start()
        self.process1.start()
        self.process0.start()
        self.eventProcessor.process_events(until_time=TWO_MINS)
        self.assertTrue(self.process1.has_resource and not self.process2.has_resource)
       
        
def makeTestSuite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTest(loader.loadTestsFromTestCase(ResourceAssignmentTests))
    suite.addTest(loader.loadTestsFromTestCase(ResourceAssignmentSubtractTests))
    suite.addTest(loader.loadTestsFromTestCase(ResourceAssignmentContainsTests))
    suite.addTest(loader.loadTestsFromTestCase(SimpleResourcePropertyTests))
    suite.addTest(loader.loadTestsFromTestCase(SimpleResourceBasicAcquireTests))
    suite.addTest(loader.loadTestsFromTestCase(SimpleResourceBasicReleaseTests))
    suite.addTest(loader.loadTestsFromTestCase(SimpleResourceAcquireQueueingTests))
    suite.addTest(loader.loadTestsFromTestCase(BasicResourcePoolTests))
    suite.addTest(loader.loadTestsFromTestCase(BasicResourcePoolReleaseTests))
    suite.addTest(loader.loadTestsFromTestCase(ResourcePoolQueueingTests))
    suite.addTest(loader.loadTestsFromTestCase(AcquireTimeoutTests))
    suite.addTests(loader.loadTestsFromTestCase(AssignmentRaceConditionTests))
    return suite        

if __name__ == '__main__':
    suite = makeTestSuite()
    unittest.main()
 