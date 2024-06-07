"""
A standalone model script implementation of the same simulation model
implemented in systest1.simdef/systest1.simdef.py.

system_test1 should run identical unit tests against both models.
"""
import sys
import itertools

from simprovise.core import simtime, SimTime
from simprovise.core import (SimEntity, SimEntitySource, SimEntitySink,
                            SimProcess, SimDistribution, SimLocation,
                            SimSimpleResource, SimQueue)
from simprovise.core.simtime import Unit as tu

from simprovise.simulation import Simulation

RSRC1_WAITS = [SimTime(10), SimTime(12), SimTime(2)]
RSRC2_WAITS = [SimTime(0.5, tu.MINUTES), SimTime(20), SimTime(4)]

pcounter = itertools.count()

rsrc1_wait = SimDistribution.round_robin(RSRC1_WAITS)
rsrc2_wait = SimDistribution.round_robin(RSRC2_WAITS)

warmupLength = SimTime(40)
batchLength = SimTime(300)
meanInterarrivalTime = SimTime(10)
nBatches = 2

workloc1 = SimLocation("WorkLocation1", entrypointname="EntryQueue")
workloc2 = SimLocation("WorkLocation2", entrypointname="RsrcQueue")
queue1 = SimQueue("RsrcQueue", workloc1)
queue2 = SimQueue("RsrcQueue", workloc2)
rsrc1 = SimSimpleResource("Resource1", workloc1)
rsrc2 = SimSimpleResource("Resource2", workloc2, capacity=2)
rsrcloc1 = SimLocation("ResourceLoc", workloc1)
rsrcloc2a = SimLocation("ResourceLocA", workloc2)
rsrcloc2b = SimLocation("ResourceLocB", workloc2)
entryQueue = SimQueue("EntryQueue", workloc1)
source = SimEntitySource("Source1")
sink = SimEntitySink("Sink1")


class TestProcess1(SimProcess):
    """
    """
    def __init__(self):
        super().__init__()
        self.pid = next(pcounter)
        self.r1wait = next(rsrc1_wait)
        self.r2wait = next(rsrc2_wait)

    def run(self):
        entity = self.entity
        entity.move_to(workloc1)
        self.wait_for(SimTime(4))
        entity.move_to(queue1)
        rsrcAssignment = self.acquire(rsrc1)
        entity.move_to(rsrcloc1)
        self.wait_for(self.r1wait)
        self.release(rsrcAssignment)
        entity.move_to(workloc2)
        rsrcAssignment = self.acquire(rsrc2)
        if rsrcloc2a.current_population == 0:
            entity.move_to(rsrcloc2a)
        else:
            entity.move_to(rsrcloc2b)
        self.wait_for(self.r2wait)
        self.release(rsrcAssignment)
        entity.move_to(sink)

source.add_entity_generator(SimEntity, TestProcess1,
                            SimDistribution.constant(meanInterarrivalTime))


if __name__ == '__main__':
    print("main")
    for e in SimEntity.elements.values():
        print(e.element_id, e.element_class, e.element_class.element)
    #warmupLength = None
    #batchLength = None
    #print("Running single execution...")
    with Simulation.execute(warmupLength, batchLength, nBatches) as simResult:
        simResult.print_summary()

    #print("Running replications...")
    #Simulation.replicate(__file__, warmupLength, batchLength, 1, 1, 1)
    #print("Replications complete.")
