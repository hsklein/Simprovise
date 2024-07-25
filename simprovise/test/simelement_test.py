#===============================================================================
# MODULE simelement_test
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#

# Unit tests for SimElement classes
#===============================================================================
import os
import unittest
from simprovise.core import simtime, simevent, SimError
#from simprovise.core.simrandom import SimDistribution
from simprovise.core.simclock import SimClock
from simprovise.core.simtime import SimTime, Unit as tu
from simprovise.core.model import SimModel
from simprovise.modeling.location import SimStaticObject, SimLocation
from simprovise.modeling.entity import SimEntity
from simprovise.core.datacollector import SimUnweightedDataCollector
from simprovise.core.datasink import DataSink
from simprovise.core.simelement import SimClassElement

class MockEntity1(SimEntity):
    ""
    
class MockEntity2(SimEntity):
    ""
    
class MockEntity3(SimEntity):
    ""

        
class TestDataSink(DataSink):
    def __init__(self, datacollector):
        self.datacollector = datacollector
        datacollector.dataset.datasink = self
        self.values = []
     
    @property   
    def dataset_id(self):
        return self.datacollector.name
                
    def put(self, value):
        self.values.append(value)
        
    def flush(self):
        pass

    def initialize_batch(self, batchnum):
        pass

    def finalize_batch(self, batchnum):
        pass            
        
class TestStaticObject(SimStaticObject):
    def __init__(self, name):
        super().__init__(name)
        self.dataCollector1 = SimUnweightedDataCollector(self, "TestData1", int)
        self.dataCollector2 = SimUnweightedDataCollector(self, "TestData2", int)
        self.datasink1 = TestDataSink(self.dataCollector1)
        self.datasink2 = TestDataSink(self.dataCollector2)
        
    def add_values(self, value):
        "Add passed value to both datasets"
        self.dataCollector1.add_value(value)
        self.dataCollector2.add_value(value)
        
class TestClassElement(SimClassElement):
    def __init__(self, cls):
        super().__init__(cls)
        self.dataCollector1 = SimUnweightedDataCollector(self, "TestClassData1", int)
        self.dataCollector2 = SimUnweightedDataCollector(self, "TestClassData2", int)
        self.datasink1 = TestDataSink(self.dataCollector1)
        self.datasink2 = TestDataSink(self.dataCollector2)
        assert self.datasets[0] == self.dataCollector1.dataset
        assert self.datasets[1] == self.dataCollector2.dataset
        
    def add_values(self, value):
        "Add passed value to both datasets"
        self.dataCollector1.add_value(value)
        self.dataCollector2.add_value(value)


class SimElementDataCollectionTests(unittest.TestCase):
    """
    """
    def setUp(self):
        SimClock.initialize()
        simevent.initialize()
        self.eventProcessor = simevent.EventProcessor()
        self.makeElements()
        self.elements = (self.element1, self.element2, self.element3)
        self.element2.datasets[1].disable_data_collection()
        self.element3.disable_data_collection()
        self.values_to_put = [3, 5, 7, 11, 13, 17]
        for val in self.values_to_put:
            for e in self.elements:
                e.add_values(val)
                
    def makeElements(self):
        self.element1 = TestStaticObject("TestElement1")
        self.element2 = TestStaticObject("TestElement2")
        self.element3 = TestStaticObject("TestElement3")
        
                
    def tearDown(self):
        # Hack to allow recreation of static objects for each test case
        SimModel.model().clear_registry_partial()

    def testIsEnabledElement1(self):
        "Test: after setup, element 1 data collection is enabled"
        self.assertTrue(self.element1.data_collection_enabled)

    def testIsEnabledElement2(self):
        "Test: after setup, element 2 data collection is enabled"
        self.assertTrue(self.element2.data_collection_enabled)

    def testIsEnabledElement3(self):
        "Test: after setup, element 3 data collection is not eabled"
        self.assertFalse(self.element3.data_collection_enabled)

    def testAreEnabledElement1Datasets(self):
        "Test: after setup, element 1 datasets are all enabled"
        for i in range(2):
            with self.subTest(i=i):               
                self.assertTrue(self.element1.datasets[i].data_collection_enabled)

    def testIsEnabledElement2Dataset1(self):
        "Test: after setup, element 2 data collection is not eabled"
        self.assertTrue(self.element2.datasets[0].data_collection_enabled)

    def testIsNotEnabledElement2Dataset1(self):
        "Test: after setup, element 2 data collection is not eabled"
        self.assertFalse(self.element2.datasets[1].data_collection_enabled)

    def testAreNotEnabledElement3Datasets(self):
        "Test: after setup, element 3 datasets are all enabled"
        for i in range(2):
            with self.subTest(i=i):               
                self.assertFalse(self.element3.datasets[i].data_collection_enabled)

    def testElement1DatasetValues(self):
        "Test: after setup, element 1 datasets both have all values"
        element = self.element1
        datasinks = (element.datasink1, element.datasink2)
        expected_values = (self.values_to_put, self.values_to_put)
        for i in range(2):
            with self.subTest(i=i):
                self.assertEqual(datasinks[i].values, expected_values[i])

    def testElement2DatasetValues(self):
        "Test: after setup, element 2: first dataset has all values, second has none"
        element = self.element2
        datasinks = (element.datasink1, element.datasink2)
        expected_values = (self.values_to_put, [])
        for i in range(2):
            with self.subTest(i=i):
                self.assertEqual(datasinks[i].values, expected_values[i])

    def testElement3DatasetValues(self):
        "Test: after setup, element 3: both datasets are empty"
        element = self.element3
        datasinks = (element.datasink1, element.datasink2)
        expected_values = ([], [])
        for i in range(2):
            with self.subTest(i=i):
                self.assertEqual(datasinks[i].values, expected_values[i])

class SimClassElementDataCollectionTests(SimElementDataCollectionTests):
    """
    """
    def makeElements(self):
        self.element1 = TestClassElement(MockEntity1)
        self.element2 = TestClassElement(MockEntity2)
        self.element3 = TestClassElement(MockEntity3)


def makeTestSuite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTest(loader.loadTestsFromTestCase(SimElementDataCollectionTests))
    suite.addTest(loader.loadTestsFromTestCase(SimClassElementDataCollectionTests))
    return suite

if __name__ == '__main__':
    unittest.main(verbosity=1)