#===============================================================================
# MODULE simentity_test
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Unit tests for SimEntity class
#===============================================================================
import unittest
import logging
from simprovise.core import *
from simprovise.core.location import SimStaticObject
from simprovise.core.simevent import EventProcessor

class TestEntity(SimEntity):
    ""

class MockProcess(SimProcess):
    ""
    processTime = SimTime(5)
    processStarts = []
    def run(self):
        MockProcess.processStarts.append(SimClock.now())
        self.wait_for(MockProcess.processTime)
        
        
class MockSource(SimEntitySource):
    def __init__(self, parentlocation=None):
        super().__init__("MockSource", parentlocation)

            
def reinitialize():
    SimDataCollector.reinitialize()
    SimClock.initialize()
    MockProcess.processStarts.clear()
    # Hack to allow recreation of static objects for each test case
    SimStaticObject.elements = {}
        
class SimEntityTests(unittest.TestCase):
    "Tests for basic SimEntity functionality"
    def setUp(self):
        reinitialize()
        self.rootLoc = SimLocation.root_location()
        
        self.process = MockProcess()
        self.source = MockSource()
        SimClock.advance_to(simtime.SimTime(5))
        self.entity = TestEntity(self.source, self.process)
        self.entityElement = SimModel.model().get_entity_element(TestEntity)
    
    def testCreateTime(self):
        "Test: createTime value equals time that the entity was instantiated"
        self.assertEqual(self.entity.create_time, SimClock.now())
    
    def testCreateTimeAfterClockAdvance(self):
        "Test: createTime value equals time that the entity was instantiated after clock advance"
        createTime = SimClock.now()
        SimClock.advance_to(SimClock.now() + 5)
        self.assertEqual(self.entity.create_time, createTime)
    
    def testSourceAttribute(self):
        "Test: source attribute value"
        self.assertEqual(self.entity.source, self.source)
    
    def testSourceAttribute(self):
        "Test: source location is root"
        self.assertIs(self.source.parent_location, self.rootLoc)
  
    def testProcessAttribute(self):
        "Test: process attribute value"
        self.assertEqual(self.entity.process, self.process)
    
    def testZeroProcessTime(self):
        "Test: at instantiation, process time is zero"
        self.assertEqual(self.entity.process_time, SimTime(0))
        
    def testProcessTime(self):
        "Test: process time is elapsed time since creation"
        SimClock.advance_to(SimClock.now() + 5)
        self.assertEqual(self.entity.process_time, SimTime(5))
        
    def testProcessTimeAfterDestroy(self):
        "Test: process time is elapsed time between creation and destruction"
        SimClock.advance_to(SimClock.now() + 5)
        self.entity.destroy()
        SimClock.advance_to(SimClock.now() + 25)
        self.assertEqual(self.entity.process_time, SimTime(5))
        
    def testEntityElement(self):
        "Test: entity element attribute is the entity element obtained from SimModel"
        self.assertIs(self.entity.element, self.entityElement)

        
class SimEntitySourceTests(unittest.TestCase):
    "Tests for basic SimEntity functionality"
    def setUp(self):
        #SimLogging.set_level(logging.DEBUG, 'simprovise.core.simevent')
        reinitialize()
        MockProcess.processTime = SimTime(1, simtime.MINUTES)
        self.eventProcessor = EventProcessor() # also calls simevent.initialize()
        self.source = MockSource()
    
    def testOneEntityGenerator(self):
        """
        One entity generator creating entity every 10 seconds
        Running for 10 seconds results in 2 events processed (One entity
        generation, one transaction start)
        """
        self.source.add_entity_generator(TestEntity, MockProcess,
                                         SimDistribution.constant, SimTime(10))
        self.source.final_initialize()              
        eventsProcessed = self.eventProcessor.process_events(SimTime(10))
        self.assertEqual(eventsProcessed, 2)
    
    def testOneEntityGenerator2(self):
        """
        One entity generator creating entity every 10 seconds
        Running for 10 seconds results in one execution of MockProcess
        run() method
        """
        self.source.add_entity_generator(TestEntity, MockProcess,
                                         SimDistribution.constant, SimTime(10))
        self.source.final_initialize()              
        eventsProcessed = self.eventProcessor.process_events(SimTime(10))
        self.assertEqual(len(MockProcess.processStarts), 1)
     
    def testTwoEntityGenerators(self):
        """
        Two entity generators: one creating entity every 5 seconds, the other
        every 10
        Running for 10 seconds results in 6 events processed (Three entity
        generation, three transaction start)
        """
        self.source.add_entity_generator(TestEntity, MockProcess,
                                         SimDistribution.constant, SimTime(5))
        self.source.add_entity_generator(TestEntity, MockProcess,
                                         SimDistribution.constant, SimTime(10))
        self.source.final_initialize()              
        eventsProcessed = self.eventProcessor.process_events(SimTime(10))
        self.assertEqual(eventsProcessed, 6)





def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SimEntityTests))
    suite.addTest(unittest.makeSuite(SimEntitySourceTests))
    return suite   

if __name__ == '__main__':
    unittest.main()