import sys
from simprovise.core import simtime, SimTime
##simtime.set_base_unit(simtime.MINUTES)


from simprovise.core import (SimEntity, SimEntitySource, SimEntitySink,
                            SimProcess, SimDistribution, SimLocation,
                            SimCounter, SimSimpleResource, SimQueue)

from simprovise.simulation import Simulation
from simprovise.models.queuing_theory_calc import theory_results

serverCapacity = 4
meanServiceTime = SimTime(8 * serverCapacity)
meanInterarrivalTime = SimTime(10)

queue = SimQueue("Queue")
server = SimSimpleResource("Server", capacity=serverCapacity)
serverLocation = SimLocation("ServerLocation")
source = SimEntitySource("Source")
sink = SimEntitySink("Sink")

stimeGenerator = SimDistribution.exponential(meanServiceTime)

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
        self.wait_for(self.serviceTime)
        self.release(resourceAssignment)
        entity.move_to(sink)

source.add_entity_generator(SimEntity, mm1Process,
                            SimDistribution.exponential(meanInterarrivalTime, streamNum=2))


if __name__ == '__main__':
    print("================ main=================")
    warmupLength = SimTime(4000)
    batchLength = SimTime(10000)
    #bl = SimTime(10000)
    print("Running single execution...")
    with Simulation.execute(warmupLength, batchLength, 5,
                            outputpath=None, overwrite=False) as simResult:
        simResult.print_summary()

    #print("Running replications...")
    #Simulation.replicate(__file__, warmupLength, batchLength, 1, 1, 1)
    #print("Replications complete.")
    
    theory_results(meanInterarrivalTime.to_scalar(), meanServiceTime.to_scalar(),
                   serverCapacity)
