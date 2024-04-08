from simprovise.core import *
import unittest

class TestEntity(SimEntity):
    ""

class MockProcess(SimProcess):
    ""
        
class MockSource(SimEntitySource):
    def __init__(self, locationObj, animationObj=None):
        super().__init__("MockSource", locationObj, animationObj)

        
class SimEntityTests(unittest.TestCase):
    "Tests for infinite capacity counter, not time-dependent"
    def setUp(self):
        SimDataCollector.reinitialize()
        SimClock.initialize();
        #SimAnimatableObject.setAnimating(False)
        TestEntity.initializeElement("MockEntity")
        rootLoc = SimRootLocation()
        
        self.process = MockProcess()
        self.source = MockSource(rootLoc)#
        SimClock.advanceTo(simtime.SimTime(5))
        self.entity = TestEntity(self.source, self.process)
    
    def testCreateTime(self):
        "Test: createTime value equals time that the entity was instantiated"
        self.assertEqual(self.entity.create_time, SimClock.now())
    
    def testSourceAttribute(self):
        "Test: source attribute value"
        self.assertEqual(self.entity.source, self.source)
  
    def testProcessAttribute(self):
        "Test: process attribute value"
        self.assertEqual(self.entity.process, self.process)
    
    def testZeroProcessTime(self):
        "Test: at instantiation, process time is zero"
        self.assertEqual(self.entity.process_time, SimTime(0))
        
    def testProcessTime(self):
        "Test: process time is elapsed time since creation"
        SimClock.advanceTo(SimClock.now() + 5)
        self.assertEqual(self.entity.process_time, SimTime(5))
        
    def testProcessTimeAfterDestroy(self):
        "Test: process time is elapsed time between creation and destruction"
        SimClock.advanceTo(SimClock.now() + 5)
        self.entity.destroy()
        SimClock.advanceTo(SimClock.now() + 25)
        self.assertEqual(self.entity.process_time, SimTime(5))






def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SimEntityTests))
    return suite   

if __name__ == '__main__':
    unittest.main()