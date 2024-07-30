#===============================================================================
# MODULE configuration_test
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Unit tests for configuration module and class SimConfigParser
#===============================================================================
import logging
import simprovise.core.configuration as simconfig
from simprovise.core import simtime

import unittest

class simconfigBasicTests(unittest.TestCase):
    "Tests for configuration module using simprovise.ini in test directory"

    def testBaseTimeUnit(self):
        "Test: base time unit is minutes"
        self.assertEqual(simconfig.get_base_timeunit(), simtime.Unit.MINUTES)
        
    def testLoggingEnabled(self):
        "Test: logging is enabled"
        self.assertTrue(simconfig.get_logging_enabled())
        
    def testLoggingLevel(self):
        "Test: default logging level is ERROR"
        self.assertEqual(simconfig.get_logging_level()[0], logging.ERROR)
        
    def testRandomStreams(self):
        "Test: maximum number of random number streams per run is 1500"
        self.assertEqual(simconfig.get_PRNstreams_per_run(), 1500)
        
    def testMaxReplications(self):
        "Test: maximum number of replications is 200"
        self.assertEqual(simconfig.get_max_replications(), 200)
        
    def testTraceEnabled(self):
        "Test: simtrace is not enabled"
        self.assertFalse(simconfig.get_trace_enabled())
        
    def testTraceType(self):
        "Test: simtrace type is table"
        self.assertEqual(simconfig.get_tracetype(), 'table')
        
    def testTraceMaxEvents(self):
        "Test: simtrace max event limit is 250"
        self.assertEqual(simconfig.get_trace_maxevents(), 250)
        
    def testTraceDestination(self):
        "Test: simtrace destination is file"
        self.assertEqual(simconfig.get_trace_destination(), 'file')
        
    def testReportDestination(self):
        "Test: output report destination is stdout"
        self.assertEqual(simconfig.get_output_report_destination(), 'stdout')
        

class simconfigDataCollectionTests(unittest.TestCase):
    """
    Data Collection configuration tests
    """
    def testLocation1Disabled(self):
        "Test: Location1 data collection disabled"
        self.assertTrue(simconfig.get_element_data_collection_disabled('Location1'))
    
    def testlocation1Disabled(self):
        "Test: location1 data collection is not disabled (disable is case-sensitive)"
        self.assertFalse(simconfig.get_element_data_collection_disabled('1ocation1'))
    
    def testLocation2ChildrenDisabled(self):
        "Test: data collection disabled for random child of Location2"
        self.assertTrue(simconfig.get_element_data_collection_disabled('Location2.XXXYY'))
    
    def testLocation2Enabled(self):
        "Test: data collection enabled for Location2 itself"
        self.assertFalse(simconfig.get_element_data_collection_disabled('Location2'))
    
    def testLocation2Enabled(self):
        "Test: data collection enabled for Location3 itself"
        self.assertFalse(simconfig.get_element_data_collection_disabled('Location3'))
    
    def testLocation3ChildrenNotAllDisabled(self):
        "Test: data collection not disabled for random child of Location3"
        self.assertFalse(simconfig.get_element_data_collection_disabled('Location3.XXXYY'))
        
    def testLocation3QueuesDisabled(self):
        "Test: data collection disabled for Queue children of Location3"
        self.assertTrue(simconfig.get_element_data_collection_disabled('Location3.Queue47'))
        
    def testEveryDownDatasetDisabled(self):
        "Test: data collection disabled any random dataset matching Down*"
        self.assertTrue(simconfig.get_dataset_data_collection_disabled('Location3.server', 'DownTime'))
        
    def testLocationPopulationDatasetDisabled1(self):
        "Test: data collection disabled any LocationX Population dataset"
        self.assertTrue(simconfig.get_dataset_data_collection_disabled('Location42', 'Population'))
        
    def testLocationPopulationDatasetDisabled2(self):
        "Test: data collection disabled any LocationX child Population dataset"
        self.assertTrue(simconfig.get_dataset_data_collection_disabled('Location42.server', 'Population'))
        
    def testOtherPopulationDatasetEnabled(self):
        "Test: data collection not disabled for other  Population dataset"
        self.assertFalse(simconfig.get_dataset_data_collection_disabled('Server', 'Population'))
        
    def testLocatio1QueueSizeDatasetDisabled1(self):
        "Test: data collection disabled any Location1 Queue Size dataset"
        self.assertTrue(simconfig.get_dataset_data_collection_disabled('Location1.Queue', 'Size'))
        
    def testLocatio1QueueSizeDatasetDisabled2(self):
        "Test: data collection disabled any Location1 Queue Size dataset"
        self.assertTrue(simconfig.get_dataset_data_collection_disabled('Location1.Queue31', 'Size'))
        
    def testLocatio1QueueszeDatasetEnabled(self):
        "Test: data collection not disabled any Location1 Queue size (lowercase) dataset"
        self.assertFalse(simconfig.get_dataset_data_collection_disabled('Location1.Queue31', 'size'))
        
        
def makeTestSuite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTest(loader.loadTestsFromTestCase(simconfigBasicTests))
    suite.addTest(loader.loadTestsFromTestCase(simconfigDataCollectionTests))
    return suite
        
if __name__ == '__main__':
    unittest.main()        