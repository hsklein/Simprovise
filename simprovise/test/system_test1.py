import os, Simalytix
from Simalytix.RunControl import *
from simprovise.configuration import *
from simprovise.core import *
from Simalytix.Database import *
from Simalytix import Simulation
import logging
import unittest

MODEL_DEFAULTS_PATH = os.path.join(os.path.dirname(Simalytix.__file__),
                                   'Configuration', 'default.simdef')

TEST_MODEL1_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'systest1.simdef')

TEST_MODELSCRIPT1_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     'systest1_model.py')

def executeSingleReplication(modelpath, dbMgr):
    #SimLogging.setLevel(logging.WARN)
    #SimAnimatableObject.setAnimating(False)
    model = SimModel(MODEL_DEFAULTS_PATH)
    model.load(modelpath)
    warmupLength = SimTime(40)
    batchLength = SimTime(300)
    nBatches = 2
    replicator = SimReplicator(model, warmupLength, batchLength, nBatches)
    replicationParameters = SimReplicationParameters()
    replicationParameters.set_replication_range(1, 1)
    replicator.execute_replications(replicationParameters, async=False)
    #dbMgr = SimDatabaseManager()
    dbMgr.open_existing_database(model, replicator.output_dbpath)

def printOutput(dbMgr):
    for dset in dbMgr.current_datasets():
        summaryData = SimSummaryData(dbMgr.database, 1, dset.elementID, batch=1)
        sumdata = summaryData.getData(dset)
        print(dset.elementID, dset.name, sumdata.count, sumdata.mean,
              sumdata.min, sumdata.max)

class ReplicatorTests(unittest.TestCase):
    dbMgr = None
    model = None
    _warmupLength = SimTime(40)
    _batchLength = SimTime(300)
    _nBatches = 2

    @classmethod
    def setUpClass(cls):
        #SimAnimatableObject.setAnimating(False)
        cls.model = SimModel(MODEL_DEFAULTS_PATH)
        cls.model.load(TEST_MODEL1_PATH)
        replicator = SimReplicator(cls.model, cls._warmupLength,
                                   cls._batchLength, cls._nBatches)
        replicationParameters = SimReplicationParameters()
        replicationParameters.set_replication_range(1, 1)
        replicator.execute_replications(replicationParameters, async=False)
        cls.dbMgr = SimDatabaseManager()
        cls.dbMgr.open_existing_database(cls.model, replicator.output_dbpath, isTemporary=True)

    @classmethod
    def tearDownClass(cls):
        cls.dbMgr.close_output_database()

    @property
    def model(self):
        return self.__class__.model

    @property
    def dbMgr(self):
        return self.__class__.dbMgr

    @property
    def warmupLength(self): return self.__class__._warmupLength

    @property
    def batchLength(self): return self.__class__._batchLength

    def summaryDsetData(self, elementID, datasetName, run=1, batch=None):
        summarydata = SimSummaryData(self.dbMgr.database, run, elementID, batch)
        dset = self.dbMgr.database.get_dataset(elementID, datasetName)
        return summarydata.getData(dset)

    def getMedian(self, elementID, datasetName, run=1, batch=None):
        pctileData = SimPercentileData(self.dbMgr.database)
        dset = self.dbMgr.database.get_dataset(elementID, datasetName)
        percentiles = pctileData.getPercentiles(dset, run, batch)
        return percentiles[50]


    def test_datasets1(self):
        "Test that model datasets (elementID/dataset name) match output database datasets"
        model_dsets = set((dset.elementID, dset.name) for dset in self.model.datasets)
        db_dsets = set((dset.elementID, dset.name) for dset in self.dbMgr.current_datasets())
        self.assertEqual(model_dsets, db_dsets)

    def test_runs(self):
        "Test that output database has just run 1"
        self.assertEqual(self.dbMgr.database.runs(), [1])

    def test_batchcount1(self):
        "Test that run 1 last batch is 2"
        self.assertEqual(self.dbMgr.database.last_batch(1), 2)

    def test_batchcount2(self):
        "Test that run 2 (which wasn't executed) last batch is 0"
        self.assertEqual(self.dbMgr.database.last_batch(2), 0)

    def test_batchtime0(self):
        "Test that batch zero (warmup) bounds are zero, 40"
        expectedBounds = (0, 40)
        self.assertEqual(self.dbMgr.database.batch_time_bounds(1,0), expectedBounds)

    def test_batchtime1(self):
        "Test that batch 1 bounds are 40, 340"
        expectedBounds = (40, 340)
        self.assertEqual(self.dbMgr.database.batch_time_bounds(1,1), expectedBounds)

    def test_batchtime2(self):
        "Test that batch 2 bounds are 340, 640"
        expectedBounds = (340, 640)
        self.assertEqual(self.dbMgr.database.batch_time_bounds(1,2), expectedBounds)

    def test_batchtime3(self):
        "Test that batch 3 bounds are 0, 0"
        expectedBounds = (0, 0)
        self.assertEqual(self.dbMgr.database.batch_time_bounds(1,3), expectedBounds)

    def test_batchtime4(self):
        "Test that batch bounds for non-existent run is 0, 0"
        expectedBounds = (0, 0)
        self.assertEqual(self.dbMgr.database.batch_time_bounds(2,1), expectedBounds)

    def test_lastbatch1(self):
        "Test that last batch for run 1 is 2"
        self.assertEqual(self.dbMgr.database.last_batch(1), 2)

    def test_lastbatch2(self):
        "Test that last batch for (non-existent) run 2 is 0"
        self.assertEqual(self.dbMgr.database.lastBatch(2), 0)

        #===========================================================================
        # Resource1, Resource2 Utilization Dataset Tests
        #===========================================================================

    def testResource1UtilizationMean0(self):
        "Test Resource1 utilization mean value for warmup is 0.6"
        elementID = "WorkLocation1.Resource1"
        dsetname = "Utilization"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 0).mean, 0.6)

    def testResource1UtilizationMean1(self):
        "Test Resource1 utilization mean value for batch 1 is 0.8"
        elementID = "WorkLocation1.Resource1"
        dsetname = "Utilization"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 1).mean, 0.8)

    def testResource1UtilizationMean2(self):
        "Test Resource1 utilization mean value for batch 2 is 0.8"
        elementID = "WorkLocation1.Resource1"
        dsetname = "Utilization"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 2).mean, 0.8)

    def testResource1UtilizationMeanDefaultBatch(self):
        "Test Resource1 utilization mean value for default (last) is 0.8"
        elementID = "WorkLocation1.Resource1"
        dsetname = "Utilization"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1).mean, 0.8)

    def testResource2UtilizationMean0(self):
        "Test Resource2 utilization mean value for warmup is 0.25"
        elementID = "WorkLocation2.Resource2"
        dsetname = "Utilization"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 0).mean, 0.25)

    def testResource2UtilizationMeanDefaultBatch(self):
        "Test Resource2 utilization mean value for default (last) is 0.9"
        elementID = "WorkLocation2.Resource2"
        dsetname = "Utilization"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1).mean, 0.9)

        #===========================================================================
        # Resource1 ProcessTime Dataset Tests
        #===========================================================================

    def testResource1ProcessTimeMean0(self):
        "Test Resource1 process time mean value for warmup is 8 seconds"
        elementID = "WorkLocation1.Resource1"
        dsetname = "ProcessTime"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 0).mean, SimTime(8))

    def testResource1ProcessTimeMin0(self):
        "Test Resource1 process time minimum value for warmup is 2 seconds"
        elementID = "WorkLocation1.Resource1"
        dsetname = "ProcessTime"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 0).min, SimTime(2))

    def testResource1ProcessTimeMax0(self):
        "Test Resource1 process time maximum value for warmup is 12 seconds"
        elementID = "WorkLocation1.Resource1"
        dsetname = "ProcessTime"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 0).max, SimTime(12))

    def testResource1ProcessTimeCount0(self):
        "Test Resource1 process time count for warmup is 3"
        elementID = "WorkLocation1.Resource1"
        dsetname = "ProcessTime"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 0).count, 3)

    def testResource1ProcessTimeMean1(self):
        "Test Resource1 process time mean value for batch 1 is 8 seconds"
        elementID = "WorkLocation1.Resource1"
        dsetname = "ProcessTime"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 1).mean, SimTime(8))

    def testResource1ProcessTimeMin1(self):
        "Test Resource1 process time minimum value for batch 1 is 2 seconds"
        elementID = "WorkLocation1.Resource1"
        dsetname = "ProcessTime"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 1).min, SimTime(2))

    def testResource1ProcessTimeMax1(self):
        "Test Resource1 process time maximum value for batch 1 is 12 seconds"
        elementID = "WorkLocation1.Resource1"
        dsetname = "ProcessTime"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 1).max, SimTime(12))

    def testResource1ProcessTimeCount1(self):
        "Test Resource1 process time count for batch 1 is 30"
        elementID = "WorkLocation1.Resource1"
        dsetname = "ProcessTime"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 1).count, 30)

    #===========================================================================
    # Resource Median Process Time tests
    # TODO should the percentile data be SimTime instances?
    #===========================================================================
    def testResource1ProcessTimeMedian1(self):
        "Test Resource1 process time median for batch 1 is 10"
        elementID = "WorkLocation1.Resource1"
        dsetname = "ProcessTime"
        self.assertEqual(self.getMedian(elementID, dsetname, 1, 1), 10)

    def testResource2ProcessTimeMedian1(self):
        "Test Resource2process time median for batch 1 is 20"
        elementID = "WorkLocation2.Resource2"
        dsetname = "ProcessTime"
        self.assertEqual(self.getMedian(elementID, dsetname, 1, 1), 20)

    #===========================================================================
    # WorkLocation1 Population Dataset Tests
    #===========================================================================

    def testWorkLocation1PopulationCurrent0(self):
        "Test WorkLocation1 population at end of warmup is zero"
        elementID = "WorkLocation1"
        dsetname = "Population"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 0).currentValue, 0)

    def testWorkLocation1PopulationCurrent1(self):
        "Test WorkLocation1 population at end of batch 1 is zero"
        elementID = "WorkLocation1"
        dsetname = "Population"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 1).currentValue, 0)

    def testWorkLocation1PopulationMin0(self):
        "Test WorkLocation1 minimum population during warmup is zero"
        elementID = "WorkLocation1"
        dsetname = "Population"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 0).min, 0)

    def testWorkLocation1PopulationMin1(self):
        "Test WorkLocation1 minimum population during batch 1 is zero"
        elementID = "WorkLocation1"
        dsetname = "Population"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 1).min, 0)

    def testWorkLocation1PopulationMax0(self):
        "Test WorkLocation1 maximum population during warmup is 2"
        elementID = "WorkLocation1"
        dsetname = "Population"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 0).max, 2)

    def testWorkLocation1PopulationMax1(self):
        "Test WorkLocation1 maximum population during batch 1 is 2"
        elementID = "WorkLocation1"
        dsetname = "Population"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 1).max, 2)

    def testWorkLocation1PopulationMean0(self):
        "Test WorkLocation1 mean population during warmup is 0.95"
        elementID = "WorkLocation1"
        dsetname = "Population"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 0).mean, 0.95)

    def testWorkLocation1PopulationMean1(self):
        "Test WorkLocation1 mean population during batch 1 is 1.2666666666"
        elementID = "WorkLocation1"
        dsetname = "Population"
        self.assertAlmostEqual(self.summaryDsetData(elementID, dsetname, 1, 1).mean, 1.2666666666)

    def testWorkLocation1PopulationMeanDefault(self):
        "Test WorkLocation1 mean population during default batch (2) is 1.2666666666"
        elementID = "WorkLocation1"
        dsetname = "Population"
        self.assertAlmostEqual(self.summaryDsetData(elementID, dsetname, 1).mean, 1.2666666666)

    def testWorkLocation1PopulationMedian0(self):
        "Test WorkLocation1 population median for warmup is 1"
        elementID = "WorkLocation1"
        dsetname = "Population"
        self.assertEqual(self.getMedian(elementID, dsetname, 1, 0), 1)

    def testWorkLocation1PopulationMedian1(self):
        "Test WorkLocation1 population median for batch 1 is 1"
        elementID = "WorkLocation1"
        dsetname = "Population"
        self.assertEqual(self.getMedian(elementID, dsetname, 1, 1), 1)

    #===========================================================================
    # WorkLocation1 Entries Dataset Tests
    #===========================================================================

    def testWorkLocation1Entries0(self):
        "Test WorkLocation1 entries during warmup is 3"
        elementID = "WorkLocation1"
        dsetname = "Entries"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 0).count, 3)

    def testWorkLocation1Entries1(self):
        "Test WorkLocation1 entries during batch 1 is 30"
        elementID = "WorkLocation1"
        dsetname = "Entries"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 1).count, 30)

    def testWorkLocation1Entries2(self):
        "Test WorkLocation1 entries during batch 2 is 30"
        elementID = "WorkLocation1"
        dsetname = "Entries"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 2).count, 30)

    #===========================================================================
    # WorkLocation1 Time Dataset Tests
    #===========================================================================

    def testWorkLocation1MeanTime0(self):
        "Test WorkLocation1 mean time during warmup is 12.666 seconds"
        elementID = "WorkLocation1"
        dsetname = "Time"
        self.assertAlmostEqual(self.summaryDsetData(elementID, dsetname, 1, 0).mean.seconds(), 12.666, 2)

    def testWorkLocation1MeanTime1(self):
        "Test WorkLocation1 mean time during batch 1 is 12.666 seconds"
        elementID = "WorkLocation1"
        dsetname = "Time"
        self.assertAlmostEqual(self.summaryDsetData(elementID, dsetname, 1, 1).mean.seconds(), 12.666, 2)

    def testWorkLocation1MeanTime2(self):
        "Test WorkLocation1 mean time during batch 2 is 12.666 seconds"
        elementID = "WorkLocation1"
        dsetname = "Time"
        self.assertAlmostEqual(self.summaryDsetData(elementID, dsetname, 1, 2).mean.seconds(), 12.666, 2)

    def testWorkLocation1MinTime0(self):
        "Test WorkLocation1 minimum time during warmup is 8 seconds"
        elementID = "WorkLocation1"
        dsetname = "Time"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 0).min.seconds(), 8)

    def testWorkLocation1MinTime1(self):
        "Test WorkLocation1 minimum time during batch 1 is 8 seconds"
        elementID = "WorkLocation1"
        dsetname = "Time"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 1).min.seconds(), 8)

    def testWorkLocation1MinTime2(self):
        "Test WorkLocation1 minimum time during batch 2 is 8 seconds"
        elementID = "WorkLocation1"
        dsetname = "Time"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 2).min.seconds(), 8)

    def testWorkLocation1MaxTime0(self):
        "Test WorkLocation1 maximum time during warmup is 16 seconds"
        elementID = "WorkLocation1"
        dsetname = "Time"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 0).max.seconds(), 16)

    def testWorkLocation1MaxTime1(self):
        "Test WorkLocation1 maximum time during batch 1 is 16 seconds"
        elementID = "WorkLocation1"
        dsetname = "Time"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 1).max.seconds(), 16)

    def testWorkLocation1MaxTime2(self):
        "Test WorkLocation1 maximum time during batch 2 is 16 seconds"
        elementID = "WorkLocation1"
        dsetname = "Time"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 2).max.seconds(), 16)

    #===========================================================================
    # WorkLocation2 Population Dataset Tests
    #===========================================================================

    def testWorkLocation2PopulationCurrent0(self):
        "Test WorkLocation2 population at end of warmup is 3"
        elementID = "WorkLocation2"
        dsetname = "Population"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 0).currentValue, 3)

    def testWorkLocation2PopulationCurrent1(self):
        "Test WorkLocation2 population at end of batch 1 is 3"
        elementID = "WorkLocation2"
        dsetname = "Population"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 1).currentValue, 3)

    def testWorkLocation2PopulationMin0(self):
        "Test WorkLocation2 minimum population during warmup is zero"
        elementID = "WorkLocation2"
        dsetname = "Population"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 0).min, 0)

    def testWorkLocation2PopulationMin1(self):
        "Test WorkLocation2 minimum population during batch 1 is 1"
        elementID = "WorkLocation2"
        dsetname = "Population"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 1).min, 1)

    def testWorkLocation2PopulationMax0(self):
        "Test WorkLocation2 maximum population during warmup is 3"
        elementID = "WorkLocation2"
        dsetname = "Population"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 0).max, 3)

    def testWorkLocation2PopulationMax1(self):
        "Test WorkLocation2 maximum population during batch 1 is 4"
        elementID = "WorkLocation2"
        dsetname = "Population"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 1).max, 4)

    def testWorkLocation2PopulationMean0(self):
        "Test WorkLocation2 mean population during warmup is 0.55"
        elementID = "WorkLocation2"
        dsetname = "Population"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 0).mean, 0.55)

    def testWorkLocation2PopulationMean1(self):
        "Test WorkLocation2 mean population during batch 1 is 2.45333"
        elementID = "WorkLocation2"
        dsetname = "Population"
        self.assertAlmostEqual(self.summaryDsetData(elementID, dsetname, 1, 1).mean, 2.45333, 3)

    def testWorkLocation2PopulationMeanDefault(self):
        "Test WorkLocation2 mean population during default batch (2) is 2.46666"
        elementID = "WorkLocation2"
        dsetname = "Population"
        self.assertAlmostEqual(self.summaryDsetData(elementID, dsetname, 1).mean,2.46666, 3)

    #===========================================================================
    # WorkLocation2 Time Dataset Tests
    #===========================================================================

    def testWorkLocation2MeanTime0(self):
        "Test WorkLocation2 mean time during warmup is None"
        elementID = "WorkLocation2"
        dsetname = "Time"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 0).mean, None, 2)

    def testWorkLocation2MeanTime1(self):
        "Test WorkLocation2 mean time during batch 1 is 24.533 seconds"
        elementID = "WorkLocation2"
        dsetname = "Time"
        self.assertAlmostEqual(self.summaryDsetData(elementID, dsetname, 1, 1).mean.seconds(), 24.533, 2)

    def testWorkLocation2MeanTime2(self):
        "Test WorkLocation2 mean time during batch 2 is 24.666 seconds"
        elementID = "WorkLocation2"
        dsetname = "Time"
        self.assertAlmostEqual(self.summaryDsetData(elementID, dsetname, 1, 2).mean.seconds(), 24.666, 2)

    def testWorkLocation2MinTime1(self):
        "Test WorkLocation2 minimum time during batch 1 is 20 seconds"
        elementID = "WorkLocation2"
        dsetname = "Time"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 1).min.seconds(), 20)

    def testWorkLocation2MinTime2(self):
        "Test WorkLocation2 minimum time during batch 2 is 20 seconds"
        elementID = "WorkLocation2"
        dsetname = "Time"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 2).min.seconds(), 20)

    def testWorkLocation2MaxTime1(self):
        "Test WorkLocation2 maximum time during batch 1 is 32 seconds"
        elementID = "WorkLocation2"
        dsetname = "Time"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 1).max.seconds(), 32)

    def testWorkLocation2MaxTime2(self):
        "Test WorkLocation2 maximum time during batch 2 is 32 seconds"
        elementID = "WorkLocation2"
        dsetname = "Time"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1, 2).max.seconds(), 32)

    #===========================================================================
    # EntryQueue Dataset Tests
    #===========================================================================

    def testEntryQueueEntries(self):
        "Test EntryQueue entries during default batch (2) is 30"
        elementID = "WorkLocation1.EntryQueue"
        dsetname = "Entries"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1).count, 30)

    def testEntryQueueTime(self):
        "Test EntryQueue mean, min and max times during default batch are all four seconds"
        elementID = "WorkLocation1.EntryQueue"
        dsetname = "Time"
        sdata = self.summaryDsetData(elementID, dsetname, 1)
        meanMinMax = (sdata.mean.seconds(), sdata.min.seconds(), sdata.max.seconds())
        self.assertEqual(meanMinMax, (4, 4, 4))

    def testEntryQueuePopulation(self):
        "Test EntryQueue mean, min, max and current population during default batch"
        elementID = "WorkLocation1.EntryQueue"
        dsetname = "Population"
        sdata = self.summaryDsetData(elementID, dsetname, 1)
        meanMinMaxCurrent = (sdata.mean, sdata.min, sdata.max, sdata.currentValue)
        self.assertEqual(meanMinMaxCurrent, (0.4, 0, 1, 0))

    #===========================================================================
    # RsrcQueue (WorkLocation1) Dataset Tests
    #===========================================================================

    def testRsrcQueue1Entries(self):
        "Test RsrcQueue 1 entries during default batch (2) is 30"
        elementID = "WorkLocation1.RsrcQueue"
        dsetname = "Entries"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1).count, 30)

    def testRsrcQueue1TimeMean(self):
        "Test RsrcQueue mean times during default batch is 0.66667 seconds"
        elementID = "WorkLocation1.RsrcQueue"
        dsetname = "Time"
        sdata = self.summaryDsetData(elementID, dsetname, 1)
        self.assertAlmostEqual(sdata.mean.seconds(), 0.6666, 3)

    def testRsrcQueue1TimeMinMax(self):
        "Test RsrcQueue min and max times during default batch are zero and two seconds"
        elementID = "WorkLocation1.RsrcQueue"
        dsetname = "Time"
        sdata = self.summaryDsetData(elementID, dsetname, 1)
        minMax = (sdata.min.seconds(), sdata.max.seconds())
        self.assertEqual(minMax, (0, 2))

    def testRsrcQueue1PopulationMean(self):
        "Test RsrcQueue mean population during default batch is 0.06667"
        elementID = "WorkLocation1.RsrcQueue"
        dsetname = "Population"
        self.assertAlmostEqual(self.summaryDsetData(elementID, dsetname, 1).mean, 0.06666, 4)

    def testRsrcQueue1PopulationMinMaxCurrent(self):
        "Test RsrcQueue min, max and current population during default batch"
        elementID = "WorkLocation1.RsrcQueue"
        dsetname = "Population"
        sdata = self.summaryDsetData(elementID, dsetname, 1)
        minMaxCurrent = (sdata.min, sdata.max, sdata.currentValue)
        self.assertEqual(minMaxCurrent, (0, 1, 0))


    #===========================================================================
    # RsrcQueue (WorkLocation2) Dataset Tests
    #===========================================================================

    def testRsrcQueue2Entries(self):
        "Test RsrcQueue 2 entries during default batch (2) is 30"
        elementID = "WorkLocation2.RsrcQueue"
        dsetname = "Entries"
        self.assertEqual(self.summaryDsetData(elementID, dsetname, 1).count, 30)

    def testRsrcQueue2TimeMean(self):
        "Test RsrcQueue 2 mean times during default batch is 6.6667 seconds"
        elementID = "WorkLocation2.RsrcQueue"
        dsetname = "Time"
        sdata = self.summaryDsetData(elementID, dsetname, 1)
        self.assertAlmostEqual(sdata.mean.seconds(), 6.6666, 3)

    def testRsrcQueue2TimeMinMax(self):
        "Test RsrcQueue 2 min and max times during default batch are zero and eighteen seconds"
        elementID = "WorkLocation2.RsrcQueue"
        dsetname = "Time"
        sdata = self.summaryDsetData(elementID, dsetname, 1)
        minMax = (sdata.min.seconds(), sdata.max.seconds())
        self.assertEqual(minMax, (0, 18))

    def testRsrcQueue2PopulationMean(self):
        "Test RsrcQueue 2 mean population during default batch is 0.6667"
        elementID = "WorkLocation2.RsrcQueue"
        dsetname = "Population"
        self.assertAlmostEqual(self.summaryDsetData(elementID, dsetname, 1).mean, 0.6666, 3)

    def testRsrcQueue2PopulationMinMaxCurrent(self):
        "Test RsrcQueue 2  min, max and current population during default batch"
        elementID = "WorkLocation2.RsrcQueue"
        dsetname = "Population"
        sdata = self.summaryDsetData(elementID, dsetname, 1)
        minMaxCurrent = (sdata.min, sdata.max, sdata.currentValue)
        self.assertEqual(minMaxCurrent, (0, 2, 1))


class SimulationTests(ReplicatorTests):
    """
    """
    @classmethod
    def setUpClass(cls):
        #SimAnimatableObject.setAnimating(False)
        warmupLength = SimTime(40)
        batchLength = SimTime(300)
        nBatches = 2
        modelscript = TEST_MODELSCRIPT1_PATH
        cls.simResult = Simulation.execute_script(modelscript, warmupLength,
                                                 batchLength, nBatches)
        cls.dbMgr = cls.simResult.dbMgr
        cls.model = Simulation.model()



def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ReplicatorTests))
    suite.addTest(unittest.makeSuite(SimulationTests))
    return suite


if __name__ == '__main__':
    SimLogging.set_level(logging.CRITICAL)
    unittest.main()

