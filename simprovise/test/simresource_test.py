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

#print(globals().keys())
#print(locals().keys())
            

class RATestCaseBase(unittest.TestCase):
    """
    TestCase base class providing common setup
    """
    def setUp(self):
        SimDataCollector.reinitialize()
        SimClock.initialize()
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
        
    def waitForResponse(self, msg):
        self.waitUntilNotified()
        
    def waitUntilNotified(self):
        self.waitStart = SimClock.now()
        self.waiting = True
        
    def resume(self):
        MockProcess.resumedProcess = self
        self.waiting = False
        
    def executing(self, flag):
        self._executing = flag
 
class MockProcessAgent(SimAgent):
    """
    An agent class that interacts with a resource assignment agent like a
    SimProcess (by sending ResourceRequests and receiving
    ResourceAssignments) without invoking any waits like a real SimProcess.
    This facilitates a mock object that can mimic/test resource request
    queueing without the blocking infrastructure of an actual simulation run.
    
    The class assignedAgents attribute is a list of MockProcessAgent
    instances that have received assignments (in the same order as they
    were received); it's used by tests to validate that requests are
    fulfilled in the correct order. To make tracking a bit easier, each
    MockProcessAgent is assigned an id attribute (pid), which is just a
    sequence number incremented for each instance created.
    
    Static method initialize should be called by test setups to clear the
    assignedAgents list and reset the pid counter.
    
    Note a limitation - this class is not currently designed to allow
    a single instance to make multiple acquire() (or acquireFrom()) calls;
    only a single resource assignment is held. For testing a sequence of
    acquire/acquireFroms, we'd typically use separate MockProcessAgent
    instances.
    """
    assignedAgents = []
    count = 0
    
    @staticmethod
    def initialize():
        MockProcessAgent.assignedAgents.clear()
        MockProcessAgent.count = 0
        
    @staticmethod
    def getPriority(msg):
        process = msg.msgData[0]
        return process.priority
    
    @staticmethod
    def pids():
        return [mpa.pid for mpa in MockProcessAgent.assignedAgents]
        
    def __init__(self, priority=1):
        super().__init__() 
        self.priority = priority
        MockProcessAgent.count += 1
        self.pid = MockProcessAgent.count
        self.assignment = None
        self.register_handler(SimMsgType.RSRC_ASSIGNMENT, self.handleResourceAssignment)
        
    @property
    def waiting(self): 
        return self.assignment is None
                
    def acquire(self, resource, numrequested=1):
        """
        Mimics SimTransaction.acquire()
        """
        msgType = SimMsgType.RSRC_REQUEST
        msgData = (self, numrequested, resource)
        msg, responses = self.send_message(resource.assignment_agent,
                                          msgType, msgData)
        if responses:
            self.handleResourceAssignment(responses[0])
            return True
        else:
            return False
        
    def acquireFrom(self, agent, rsrcClass, numrequested=1):
        """
        Mimics SimTransaction.acquireFrom()
        """
        msgType = SimMsgType.RSRC_REQUEST
        msgData = (self, numrequested, rsrcClass)
        msg, responses = self.send_message(agent, msgType, msgData)
        if responses:
            self.handleResourceAssignment(responses[0])
            return True
        else:
            return False
            
    def handleResourceAssignment(self, msg):
        """
        Handle an assignment message from a resource assignment agent by:
        - setting the assignment attribute (a non-None value indicates that an
          assignment has been received), and
        - Adding this MockProcessAgent to the end of the assignedAgents list
        """
        assert msg.msgType == SimMsgType.RSRC_ASSIGNMENT, "Invalid message type passed to handleResourceAssignment()"
        self.assignment = msg.msgData
        MockProcessAgent.assignedAgents.append(self)
        
    def release(self, releaseSpec=None):
        """
        Mimic a SimTransaction.release()
        """
        assert self.assignment, "Cannot release prior to assignment"
        assignmentAgent = self.assignment.assignment_agent
        msgType = SimMsgType.RSRC_RELEASE
        msgData = (self.assignment, releaseSpec)
        self.send_message(assignmentAgent, msgType, msgData)

       
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
    "Tests ResourceAssignment subtract and subtractAll methods"
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
        self.assertEqual(self.rsrc1.inUse, 0)
        
    def testInUse1b(self):
        "Test:  Resource 1 has inUse property value of one after a single acquire() call"
        self.process.acquire(self.rsrc1, 1)
        self.assertEqual(self.rsrc1.inUse, 1)
        
    def testAvailable1a(self):
        "Test:  Resource 1 has initial available property value of one"
        self.assertEqual(self.rsrc1.available, 1)
        
    def testAvailable1b(self):
        "Test:  Resource 1 has available property value of zero after a single acquire() call"
        self.process.acquire(self.rsrc1, 1)
        self.assertEqual(self.rsrc1.available, 0)
        
    def testDown1(self):
        "Test:  Resource 1 has initial down property value of zero"
        self.assertEqual(self.rsrc1.down, 0)
    
    def testCapacity2(self):
        "Test:  Resource 2 has capacity of two"
        self.assertEqual(self.rsrc2.capacity, 2)
           
    def testInUse2a(self):
        "Test:  Resource 1 has initial inUse property value of zero"
        self.assertEqual(self.rsrc2.inUse, 0)
        
    def testInUse2b(self):
        "Test:  Resource 2 has inUse property value of two after a two acquire() calls"
        self.process.acquire(self.rsrc2, 1)
        self.process.acquire(self.rsrc2, 1)
        self.assertEqual(self.rsrc2.inUse, 2)
        
    def testInUse2c(self):
        "Test:  Resource 2 has inUse property value of two after an acquire(2) call"
        self.process.acquire(self.rsrc2, 2)
        self.assertEqual(self.rsrc2.inUse, 2)

    def testAvailable2a(self):
        "Test:  Resource 1 has initial available property value of two"
        self.assertEqual(self.rsrc2.available, 2)

    def testAvailable2b(self):
        "Test:  Resource 2 has available property value of one after an acquire call"
        self.process.acquire(self.rsrc2, 1)
        self.assertTrue(self.rsrc2.available, 1)

    def testAvailable2c(self):
        "Test:  Resource 2 has available property value of zero after acquire(2) call"
        self.process.acquire(self.rsrc2, 2)
        self.assertEqual(self.rsrc2.available, 0)
        
    def testDown2(self):
        "Test:  Resource 1 has initial down property value of zero"
        self.assertEqual(self.rsrc2.down, 0)
        
    def testCurrentAssignments(self):
        "Test: two acquisitions of a resource, both assignments returned by currentAssignments"
        assignment1 = self.process.acquire(self.rsrc2, 1)
        assignment2 = self.process.acquire(self.rsrc2, 1)
        assignments = set(self.rsrc2.current_assignments)
        self.assertEqual(assignments, set((assignment1, assignment2)))
   
        
class SimpleResourceBasicAcquireTests(RATestCaseBase):
    "Tests basic (no running simulation required) SimpleResource class acquire() functionality"
    def setUp(self):
        super().setUp()
        self.rsrc1 = SimSimpleResource("TestResource1", self.location)
        self.rsrc2 = SimSimpleResource("TestResource2", self.location, capacity=2)
        self.rsrc3 = SimSimpleResource("TestResource3", self.location, capacity=3)
        
    def testAssignment1(self):
        "Test: acquire() returns a resource assignment with correct process"
        ra = self.process.acquire(self.rsrc1)
        self.assertEqual(ra.transaction, self.process)
        
    def testAssignment1a(self):
        "Test: acquire(1) returns a resource assignment with correct count"
        ra = self.process.acquire(self.rsrc1)
        self.assertEqual(ra.count, 1)
        
    def testAssignment1b(self):
        "Test: acquire(1) returns a resource assignment with correct resource"
        ra = self.process.acquire(self.rsrc1)
        self.assertEqual(ra.resource, self.rsrc1)
        
    def testAssignment2(self):
        "Test: acquire(2) returns a resource assignment with correct count"
        ra = self.process.acquire(self.rsrc2, 2)
        self.assertEqual(ra.count, 2)
        
    def testAcquireGreaterThanCapacity(self):
        "Test: acquire(3) on a resource of capacity two raises an Error"
        self.assertRaises(SimError, lambda:  self.process.acquire(self.rsrc2, 3))
        
    def testAcquireZero(self):
        "Test: acquire(0) raises an Error"
        self.assertRaises(SimError, lambda:  self.process.acquire(self.rsrc2, 0))
        
    def testAcquireNonInt(self):
        "Test: acquire for a non-integer numRequested raises an Error"
        self.assertRaises(SimError, lambda:  self.process.acquire(self.rsrc2, 2.4))
        
    def testAcquireWhileNotExecuting(self):
        "Test: acquire() for a process that is not currently executing raises an Error"
        self.process.executing(False)
        self.assertRaises(AssertionError, lambda:  self.process.acquire(self.rsrc2, 1))

        
        
class SimpleResourceBasicReleaseTests(RATestCaseBase):
    "Tests basic (no running simulation required) SimpleResource class release() functionality"
    def setUp(self):
        super().setUp()
        MockProcessAgent.assignedAgents.clear()
        self.rsrc1 = SimSimpleResource("TestResource1", self.location)
        self.rsrc2 = SimSimpleResource("TestResource2", self.location, capacity=2)
        self.rsrc3 = SimSimpleResource("TestResource3", self.location, capacity=3)
        
    def testReleaseAll1(self):
        "Test: acquire() followed by release results in resource inUse property value of zero"
        ra = self.process.acquire(self.rsrc1)
        self.process.release(ra)
        self.assertEqual(self.rsrc1.inUse, 0)
        
    def testReleaseAll2(self):
        "Test: acquire() followed by release results in resource available property value equal to capacity"
        ra = self.process.acquire(self.rsrc2, 2)
        self.process.release(ra)
        self.assertEqual(self.rsrc2.available, self.rsrc2.capacity)
       
    #============================================================================================
    # TODO Tests commented out pending (re) implementation of partial resource assignment release 
    #============================================================================================
    def testAssignment2(self):
        "Test: acquire(2) followed by release(1) results in resource assignment with count of one"
        ra = self.process.acquire(self.rsrc2, 2)
        self.process.release(ra, self.rsrc2)
        self.assertEqual(ra.count, 1)
    
    def testAssignment2a(self):
        "Test: acquire(2) followed by release(1) (int argument) results in resource assignment with count of one"
        ra = self.process.acquire(self.rsrc2, 2)
        self.process.release(ra, 1)
        self.assertEqual(ra.count, 1)
        
    def testAcquire2Release1(self):
        "Test: acquire(2) followed by a release(1) results in resource with inUse of 1"
        ra = self.process.acquire(self.rsrc2, 2)
        self.process.release(ra, self.rsrc2)
        self.assertEqual(self.rsrc2.inUse, 1)
        
    def testAcquire2Release2A(self):
        "Test: acquire(2) followed by twp release(1) calls results in resource with inUse of 0"
        ra = self.process.acquire(self.rsrc2, 2)
        self.process.release(ra, self.rsrc2)
        self.process.release(ra, self.rsrc2)
        self.assertEqual(self.rsrc2.inUse, 0)
        
    def testAcquire2Release2B(self):
        "Test: acquire(2) followed by release(2) calls results in resource with inUse of 0"
        ra = self.process.acquire(self.rsrc2, 2)
        self.process.release(ra, 2)
        self.assertEqual(self.rsrc2.inUse, 0)
        
    def testAcquire2Release2C(self):
        "Test: acquire(2) followed by release(rsrc, rsrc) calls results in resource with inUse of 0"
        ra = self.process.acquire(self.rsrc2, 2)
        self.process.release(ra, (self.rsrc2, self.rsrc2))
        self.assertEqual(self.rsrc2.inUse, 0)
        
    def testAcquire2Release2Assignment(self):
        "Test: acquire(2) followed by twp release(1) (resource instance) calls results in resource with count of 0"
        ra = self.process.acquire(self.rsrc2, 2)
        self.process.release(ra, self.rsrc2)
        self.process.release(ra, self.rsrc2)
        self.assertEqual(ra.count, 0)
        
    def testAcquire2Release2AssignmentA(self):
        "Test: acquire(2) followed by twp release(1) calls results in resource with count of 0"
        ra = self.process.acquire(self.rsrc2, 2)
        self.process.release(ra, 1)
        self.process.release(ra, 1)
        self.assertEqual(ra.count, 0)
        
    def testReleaseMoreThanAssigned(self):
        "Test: acquire(1) followed by release(2) raises an error"
        ra = self.process.acquire(self.rsrc2, 1)
        self.assertRaises(SimError, lambda:  self.process.release(ra, 2))
        
    def testReleaseMoreThanAssigned2(self):
        "Test: acquire(1) followed by two release(1) calls raises an error"
        ra = self.process.acquire(self.rsrc2, 1)
        self.process.release(ra, 1)
        self.assertRaises(SimError, lambda:  self.process.release(ra, 1))
        
    def testReleaseMoreThanAssigned3(self):
        "Test: acquire(1) followed by release(2) raises an error"
        ra = self.process.acquire(self.rsrc2, 1)
        self.assertRaises(SimError, lambda:  self.process.release(ra, (self.rsrc2, self.rsrc2)))
        
    def testReleaseWrongResource(self):
        "Test: acquire(1) followed by release() on wrong resource raises an error"
        ra = self.process.acquire(self.rsrc1, 1)
        self.assertRaises(SimError, lambda:  self.process.release(ra, self.rsrc2))
        
        
class SimpleResourceAcquireQueueingTests(RATestCaseBase):
    """
    Tests SimpleResource class acquisition from multiple processes, including
    queued (unfulfilled) acquisition requests. Uses the MockProcessAgent to
    simulate queueing without any actual simulation or other blocking of
    queued requests.
    
    If SimpleResource acquire() requests are fulfilled in priority (as
    opposed to FIFO) order, they should end up in the following order:
    1,3,5,4,2.
    """
    def setUp(self):
        super().setUp()
        MockProcessAgent.initialize()
        self.process1 = MockProcessAgent(2)
        self.process2 = MockProcessAgent(3)
        self.process3 = MockProcessAgent(1)
        self.process4 = MockProcessAgent(2)
        self.process5 = MockProcessAgent(1)
        self.rsrc = SimSimpleResource("TestResource1", self.location)
             
    def testAccquire1(self):
        "Test: first acquire() on resource with capacity 1 does not result in a wait"
        self.process1.acquire(self.rsrc)
        self.assertFalse(self.process1.waiting)
        
    def testAccquire2(self):
        "Test: second acquire() on resource with capacity 1 does result in a wait"
        self.process1.acquire(self.rsrc)
        self.process2.acquire(self.rsrc)
        self.assertTrue(self.process2.waiting)
        
    def testAccquire3(self):
        "Test: 3 acquires, one release, process2 is not waiting"
        self.process1.acquire(self.rsrc)
        self.process2.acquire(self.rsrc)
        self.process3.acquire(self.rsrc)
        self.process1.release()
        self.assertFalse(self.process2.waiting)
        
    def testAccquire4(self):
        "Test: 4 acquires, one release, assigned processes are [1, 2]"
        self.process1.acquire(self.rsrc)
        self.process2.acquire(self.rsrc)
        self.process3.acquire(self.rsrc)
        self.process1.release()
        self.assertEqual(MockProcessAgent.pids(), [1,2])
        
    def testAccquire5(self):
        "Test: 5 acquires, 4 releases, assigned processes are [1,2,3,4,5]"
        self.process1.acquire(self.rsrc)
        self.process2.acquire(self.rsrc)
        self.process3.acquire(self.rsrc)
        self.process4.acquire(self.rsrc)
        self.process5.acquire(self.rsrc)
        self.process1.release()
        self.process2.release()
        self.process3.release()
        self.process4.release()
        self.assertEqual(MockProcessAgent.pids(), [1,2,3,4,5])
        
    def testAccquire6(self):
        "Test: using priority 5 acquires, 4 releases, assigned processes are [1,3,5,4,2]"
        self.rsrc.register_priority_func(SimMsgType.RSRC_REQUEST, 
                                       MockProcessAgent.getPriority)
        self.process1.acquire(self.rsrc)
        self.process2.acquire(self.rsrc)
        self.process3.acquire(self.rsrc)
        self.process4.acquire(self.rsrc)
        self.process5.acquire(self.rsrc)
        MockProcessAgent.assignedAgents[-1].release()
        MockProcessAgent.assignedAgents[-1].release()
        MockProcessAgent.assignedAgents[-1].release()
        MockProcessAgent.assignedAgents[-1].release()
        self.assertEqual(MockProcessAgent.pids(), [1,3,5,4,2])
        
    def testAccquire7(self):
        "Test: resource capacity 3: 5 acquires, 2 releases, assigned processes are [1,2,3,4,5]"
        self.rsrc = SimSimpleResource("TestResource2", self.location, capacity=3)
        self.process1.acquire(self.rsrc)
        self.process2.acquire(self.rsrc)
        self.process3.acquire(self.rsrc)
        self.process4.acquire(self.rsrc)
        self.process5.acquire(self.rsrc)
        self.process1.release()
        self.process2.release()
        self.assertEqual(MockProcessAgent.pids(), [1,2,3,4,5])
        
    def testAccquire8(self):
        "Test: resource capacity 3: acquires with num requested up to 2"
        self.rsrc = SimSimpleResource("TestResource2", self.location, capacity=3)
        self.process1.acquire(self.rsrc)
        self.process2.acquire(self.rsrc, 2)
        self.process3.acquire(self.rsrc, 2)
        self.process4.acquire(self.rsrc)
        self.process5.acquire(self.rsrc)
        self.process1.release()
        self.assertEqual(MockProcessAgent.pids(), [1,2])
        
    def testAccquire9(self):
        "Test: resource capacity 3: acquires with num requested up to 2, one more release"
        self.rsrc = SimSimpleResource("TestResource2", self.location, capacity=3)
        self.process1.acquire(self.rsrc)
        self.process2.acquire(self.rsrc, 2)
        self.process3.acquire(self.rsrc, 2)
        self.process4.acquire(self.rsrc)
        self.process5.acquire(self.rsrc)
        self.process1.release()
        self.process2.release()
        self.assertEqual(MockProcessAgent.pids(), [1,2,3,4])
        
    def testAccquire10(self):
        "Test: using priority 5 acquires, 1 release, capacity 4 resource"
        self.rsrc = SimSimpleResource("TestResource2", self.location, capacity=4)
        self.rsrc.register_priority_func(SimMsgType.RSRC_REQUEST, 
                                       MockProcessAgent.getPriority)
        self.process1.acquire(self.rsrc, 4)
        self.process2.acquire(self.rsrc, 1)
        self.process3.acquire(self.rsrc, 2)
        self.process4.acquire(self.rsrc, 2)
        self.process5.acquire(self.rsrc, 1)
        MockProcessAgent.assignedAgents[0].release() # 1
        self.assertEqual(MockProcessAgent.pids(), [1,3,5])


class BasicResourcePoolTests(RATestCaseBase):
    """
    Tests basic usage of a resource pool, without any simulated queueing
    """
    def setUp(self):
        super().setUp()
        self.rsrc1 = SimSimpleResource("TestResource1", self.location)
        self.rsrc2 = SimSimpleResource("TestResource2", self.location, capacity=2)
        self.rsrc3 = TestResource("TestResource3", self.location, capacity=2)
        self.rsrc4 = SimSimpleResource("TestResource4", self.location, capacity=2)
        self.pool = SimResourcePool(self.rsrc1, self.rsrc2, self.rsrc3, self.rsrc4)
        
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
        ra = self.process1.acquire_from(self.pool, SimResource)
        self.assertEqual(ra.resource, self.rsrc1)
             
    def testacquire2(self):
        "Test: Acquire three of any resource from the pool, followed by 2"
        self.process1.acquire_from(self.pool, SimResource, 3)
        ra = self.process1.acquire_from(self.pool, SimResource, 2)
        expected = (self.rsrc3, self.rsrc3)
        self.assertEqual(ra.resources, expected)
             
    def testacquire3(self):
        "Test: Acquire all seven resources in the pool"
        ra = self.process1.acquire_from(self.pool, SimResource, 7)
        self.assertEqual(len(ra.resources), 7)
             
    def testacquire4(self):
        "Test: Acquire a TestResource"
        ra = self.process1.acquire_from(self.pool, TestResource, 1)
        expected = (self.rsrc3,)
        self.assertEqual(ra.resources, expected)
             
    def testavailable2(self):
        "Test: Acquire three of any resource from the pool, followed by 2 - available "
        self.process1.acquire_from(self.pool, SimResource, 3)
        self.process2.acquire_from(self.pool, SimResource, 2)
        self.assertEqual(self.pool.available(), 2)
             
    def testavailable3(self):
        "Test: Acquire three of any resource from the pool, followed by 2 - available TestResources "
        self.process1.acquire_from(self.pool, SimResource, 3)
        self.process2.acquire_from(self.pool, SimResource, 2)
        self.assertEqual(self.pool.available(TestResource), 0)
             
    def testavailableresources32(self):
        "Test: Acquire three of any resource from the pool, followed by 2 - availableResources "
        self.process1.acquire_from(self.pool, SimResource, 3)
        self.process2.acquire_from(self.pool, SimResource, 2)
        self.assertEqual(self.pool.available_resources(), [self.rsrc4])
             
    def testcurrentAssignments32(self):
        "Test: Acquire three of any resource from the pool, followed by 2 - currentAssignments "
        ra1 = self.process1.acquire_from(self.pool, SimResource, 3)
        ra2 = self.process2.acquire_from(self.pool, SimResource, 2)
        self.assertEqual(set(self.pool.current_assignments()), set([ra1, ra2]))
             
    def testcurrentTransactions32(self):
        "Test: Acquire three of any resource from the pool, followed by 2 - currentTransactions "
        ra1 = self.process1.acquire_from(self.pool, SimResource, 3)
        ra2 = self.process2.acquire_from(self.pool, SimResource, 2)
        expected = (self.process1, self.process2)
        self.assertEqual(set(self.pool.current_transactions()), set(expected))
             
    def testacquiremorethanpoolsize1(self):
        "Test: Acquire 8 of any resource (bigger than the pool) raises "
        self.assertRaises(SimError, 
                          lambda: self.process1.acquire_from(self.pool, SimResource, 8))
             
    def testacquiremorethanpoolsize2(self):
        "Test: Acquire 3 of TestResource (bigger than the pool) raises "
        self.assertRaises(SimError, 
                          lambda: self.process1.acquire_from(self.pool, TestResource, 3))



class BasicResourcePoolReleaseTests(RATestCaseBase):
    """
    Tests basic usage of a resource pool, without any simulated queueing
    """
    def setUp(self):
        super().setUp()
        self.rsrc1 = SimSimpleResource("TestResource1", self.location)
        self.rsrc2 = SimSimpleResource("TestResource2", self.location, capacity=2)
        self.rsrc3 = TestResource("TestResource3", self.location, capacity=2)
        self.rsrc4 = SimSimpleResource("TestResource4", self.location, capacity=2)
        self.pool = SimResourcePool(self.rsrc1, self.rsrc2, self.rsrc3, self.rsrc4)
        self.ra1 = self.process1.acquire_from(self.pool, SimSimpleResource, 2)
        self.ra2 = self.process2.acquire_from(self.pool, TestResource, 1)
                          
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


class ResourcePoolQueueingTests(RATestCaseBase):
    """
    Tests SimResourcePool resource acquisition from multiple processes,
    including queued (unfulfilled) acquisition requests. Uses the
    MockProcessAgent to simulate queueing without any actual simulation or
    other blocking of queued requests.
    
    If acquireFrom() requests are fulfilled in priority (as opposed to FIFO)
    order, they should end up in the following order: 1,3,5,4,2.
    """
    def setUp(self):
        super().setUp()
        MockProcessAgent.initialize()
        self.process1 = MockProcessAgent(2)
        self.process2 = MockProcessAgent(3)
        self.process3 = MockProcessAgent(1)
        self.process4 = MockProcessAgent(2)
        self.process5 = MockProcessAgent(1)
        self.rsrc1 = SimSimpleResource("TestResource1", self.location)
        self.rsrc2 = SimSimpleResource("TestResource2", self.location, capacity=2)
        self.rsrc3 = SimSimpleResource("TestResource3", self.location, capacity=2)
        self.rsrc4 = TestResource("TestResource4", self.location, capacity=2)
        self.pool = SimResourcePool(self.rsrc1, self.rsrc2, self.rsrc3, self.rsrc4)
             
    def testacquireFIFOnorelease(self):
        """
        Test: Acquire two resources for each process. Without any releases,
        the first three process will be assigned
        """
        self.process1.acquireFrom(self.pool, SimSimpleResource, 2)
        self.process2.acquireFrom(self.pool, SimSimpleResource, 2)
        self.process3.acquireFrom(self.pool, SimSimpleResource, 2)
        self.process4.acquireFrom(self.pool, SimSimpleResource, 2)
        self.process5.acquireFrom(self.pool, SimSimpleResource, 2)
        self.assertEqual(MockProcessAgent.pids(), [1,2,3])
             
    def testacquireFIFOrelease1(self):
        """
        Test: Acquire two resources for each process. Release the
        first process's assignment; four process requests are fulfilled
        """
        self.process1.acquireFrom(self.pool, SimSimpleResource, 2)
        self.process2.acquireFrom(self.pool, SimSimpleResource, 2)
        self.process3.acquireFrom(self.pool, SimSimpleResource, 2)
        self.process4.acquireFrom(self.pool, SimSimpleResource, 2)
        self.process5.acquireFrom(self.pool, SimSimpleResource, 2)
        self.process1.release()
        self.assertEqual(MockProcessAgent.pids(), [1,2,3,4])
             
    def testacquireFIFOrelease1a(self):
        """
        Test: Acquire two resources for each process. Release one of the
        resources for the first process's assignment; four process requests
        are fulfilled
        """
        self.process1.acquireFrom(self.pool, SimSimpleResource, 2)
        self.process2.acquireFrom(self.pool, SimSimpleResource, 2)
        self.process3.acquireFrom(self.pool, SimSimpleResource, 2)
        self.process4.acquireFrom(self.pool, SimSimpleResource, 2)
        self.process5.acquireFrom(self.pool, SimSimpleResource, 2)
        self.process1.release(1)
        self.assertEqual(MockProcessAgent.pids(), [1,2,3,4])
             
    def testacquireFIFOrelease3(self):
        """
        Test: Acquire two resources for each process. Release one of the
        resources for the processes 1-3; all requests are fulfilled
        """
        self.process1.acquireFrom(self.pool, SimSimpleResource, 2)
        self.process2.acquireFrom(self.pool, SimSimpleResource, 2)
        self.process3.acquireFrom(self.pool, SimSimpleResource, 2)
        self.process4.acquireFrom(self.pool, SimSimpleResource, 2)
        self.process5.acquireFrom(self.pool, SimSimpleResource, 2)
        self.process1.release(1)
        self.process2.release(1)
        self.process3.release(1)
        self.assertEqual(MockProcessAgent.pids(), [1,2,3,4,5])
             
    def testacquireFIFOTestResource(self):
        """
        Test - acquireFrom() "blocks" on request for third Test Resource.
        The last request for a SimSimpleResource is not fulfilled (even
        though there are such resources available) Since the last TestResource
        request is ahead in line.
        """
        self.process1.acquireFrom(self.pool, SimSimpleResource, 1)
        self.process2.acquireFrom(self.pool, TestResource, 2)
        self.process3.acquireFrom(self.pool, SimSimpleResource, 1)
        self.process4.acquireFrom(self.pool, TestResource, 1)
        self.process5.acquireFrom(self.pool, SimSimpleResource, 1)
        self.assertEqual(MockProcessAgent.pids(), [1,2,3])
             
    def testacquirePriorityrelease1(self):
        """
        Test: Using a priority queue, request TestResources; after the first
        request, requests are fulfilled in priority order
        """
        self.pool.register_priority_func(SimMsgType.RSRC_REQUEST, 
                                       MockProcessAgent.getPriority)
        self.process1.acquireFrom(self.pool, TestResource, 2)
        self.process2.acquireFrom(self.pool, TestResource)
        self.process3.acquireFrom(self.pool, TestResource)
        self.process4.acquireFrom(self.pool, TestResource)
        self.process5.acquireFrom(self.pool, TestResource)
        self.process1.release()
        self.assertEqual(MockProcessAgent.pids(), [1,3,5])
             
    def testacquirePriorityrelease2(self):
        """
        Test: Using a priority queue, request TestResources; after the first
        request, requests are fulfilled in priority order - so an earlier
        (but lower priority) request for an available SimSimpleResource 
        is not fulfilled.
        """
        self.pool.register_priority_func(SimMsgType.RSRC_REQUEST, 
                                       MockProcessAgent.getPriority)
        self.process1.acquireFrom(self.pool, TestResource, 2)
        self.process2.acquireFrom(self.pool, TestResource)
        self.process3.acquireFrom(self.pool, TestResource)
        self.process4.acquireFrom(self.pool, SimSimpleResource)
        
        # After process1 releases, process3 is assigned a TestResource,
        # but process5 (the next in the priority queue) is not. So the
        # request from process4 is not fulfilled.
        self.process5.acquireFrom(self.pool, TestResource, 2) 
        self.process1.release()
        self.assertEqual(MockProcessAgent.pids(), [1,3])

              
        
def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ResourceAssignmentTests))
    suite.addTest(unittest.makeSuite(ResourceAssignmentSubtractTests))
    suite.addTest(unittest.makeSuite(ResourceAssignmentContainsTests))
    suite.addTest(unittest.makeSuite(SimpleResourcePropertyTests))
    suite.addTest(unittest.makeSuite(SimpleResourceBasicAcquireTests))
    suite.addTest(unittest.makeSuite(SimpleResourceBasicReleaseTests))
    suite.addTest(unittest.makeSuite(SimpleResourceAcquireQueueingTests))
    suite.addTest(unittest.makeSuite(BasicResourcePoolTests))
    suite.addTest(unittest.makeSuite(BasicResourcePoolReleaseTests))
    suite.addTest(unittest.makeSuite(ResourcePoolQueueingTests))
    return suite        

if __name__ == '__main__':
    unittest.main()
 