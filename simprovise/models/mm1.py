import sys
from simprovise.core import simtime, SimTime
from simprovise.core import (SimEntity, SimEntitySource, SimEntitySink,
                            SimProcess, SimDistribution, SimLocation,
                            SimCounter, SimSimpleResource, SimQueue)

from simprovise.simulation import Simulation
#from simprovise.configuration import simelement, SimElement
#from simprovise.runcontrol import SimReplicator, SimReplicationParameters

from simprovise.models.testprocess import TestProcess
#from Simalytix.RunControl import SimReplication
#from Simalytix.Database import SimDatabaseManager, SimSummaryData

meanServiceTime = SimTime(9)
meanInterarrivalTime = SimTime(12)

#Simulation.initialize()

warmupLength = SimTime(500)
batchLength = SimTime(1000)

#Simulation.model().simulationWarmup = warmupLength
#Simulation.model().simulationBatchLength = batchLength
#Simulation.model().simulationBatchCount = 1

queue = SimQueue("Queue")
server = SimSimpleResource("Server", capacity=1)
serverLocation = SimLocation("ServerLocation")
source = SimEntitySource("Source")
sink = SimEntitySink("Sink")

stimeGenerator = SimDistribution.number_generator(SimDistribution.exponential,
                                                 meanServiceTime, 2)

class mm1Process(SimProcess):
    """
    """
    def __init__(self):
        super().__init__()
        self.serviceTime = next(stimeGenerator)

    def run(self):
        entity = self.entity
        entity.move_to(queue)
        resourceAssignment = self.acquire(server)
        entity.move_to(serverLocation)
        self.waitFor(self.serviceTime)
        self.release(resourceAssignment)
        entity.move_to(sink)

source.add_entity_generator(SimEntity, mm1Process, SimDistribution.exponential,
                          meanInterarrivalTime, 1)


if __name__ == '__main__':
    print("================ main=================")
    warmupLength = SimTime(500)
    batchLength = SimTime(1000)
    #bl = SimTime(1000)
    print("Running single execution...")
    with Simulation.execute(warmupLength, batchLength, 3,
                            outputpath=None, overwrite=False) as simResult:
        simResult.print_summary()
        
    #with Simulation.executeScript(__file__, warmupLength, batchLength, 3) as simResult:
    #    simResult.printSummary()

    #print("Running replications...")
    #Simulation.replicate(__file__, warmupLength, batchLength, 1, 1, 1)
    #print("Replications complete.")
