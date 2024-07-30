import unittest
      
from simprovise.test import configuration_test
from simprovise.test import simtime_test
from simprovise.test import simclock_test
from simprovise.test import simrandom_test
from simprovise.test import simevent_test
from simprovise.test import simdatacollector_test
from simprovise.test import simcounter_test
from simprovise.test import simlocation_test
from simprovise.test import simresource_test
from simprovise.test import simentity_test
from simprovise.test import simtransaction_test
from simprovise.test import simprocess_test
from simprovise.test import simdowntime_test
from simprovise.test import simelement_test

# Note that running the system test creates too much state, and
# effs up itself and other tests - for now, it has to run
# on its own.
#from simprovise.test import system_test1

from simprovise.core.simlogging import SimLogging
import logging

def run_tests():
    SimLogging.set_level(logging.CRITICAL)

    suite = unittest.TestSuite()

    #suite.addTest(system_test1.makeTestSuite())
    suite.addTest(configuration_test.makeTestSuite())
    suite.addTest(simtime_test.makeTestSuite())
    suite.addTest(simclock_test.makeTestSuite())
    suite.addTest(simelement_test.makeTestSuite())
    suite.addTest(simrandom_test.makeTestSuite())
    suite.addTest(simevent_test.makeTestSuite())
    suite.addTest(simdatacollector_test.makeTestSuite())
    suite.addTest(simcounter_test.makeTestSuite() )
    suite.addTest(simlocation_test.makeTestSuite())
    suite.addTest(simresource_test.makeTestSuite())
    suite.addTest(simentity_test.makeTestSuite())
    suite.addTest(simtransaction_test.makeTestSuite())
    suite.addTest(simprocess_test.makeTestSuite())
    suite.addTest(simdowntime_test.makeTestSuite())

    unittest.TextTestRunner(verbosity=1).run(suite)

if __name__ == "__main__":
    # guard execution in if __name__ block to avoid multiprocessing errors
    # from replicator tests
    run_tests()


