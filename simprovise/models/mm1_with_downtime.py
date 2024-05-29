import sys
from simprovise.core import simtime, SimTime
##simtime.set_base_unit(simtime.MINUTES)


from simprovise.core import (SimEntity, SimEntitySource, SimEntitySink,
                            SimProcess, SimDistribution, SimLocation,
                            SimCounter, SimSimpleResource, SimQueue,
                            SimResourceFailureAgent)

from simprovise.simulation import Simulation
from simprovise.models.queuing_theory_calc import theory_results

serverCapacity = 4
meanServiceTime = SimTime(6 * serverCapacity)
meanInterarrivalTime = SimTime(10)
mttf = SimTime(220)
mttr = SimTime(30)

queue = SimQueue("Queue")
server = SimSimpleResource("Server", capacity=serverCapacity)
serverLocation = SimLocation("ServerLocation")
source = SimEntitySource("Source")
sink = SimEntitySink("Sink")

timeToFailureGenerator = SimDistribution.exponential(mttf)
timeToRepairGenerator = SimDistribution.normal(mttr, 1)
failureAgent = SimResourceFailureAgent(server, timeToFailureGenerator, timeToRepairGenerator)

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
        self.wait_for(self.serviceTime, extend_through_downtime=True)
        self.release(resourceAssignment)
        entity.move_to(sink)

source.add_entity_generator(SimEntity, mm1Process,
                            SimDistribution.exponential(meanInterarrivalTime, streamNum=2))


if __name__ == '__main__':
    print("================ main=================")
    warmupLength = SimTime(4000)
    batchLength = SimTime(10000)
    #bl = SimTime(1000)
    print("Running single execution...")
    with Simulation.execute(warmupLength, batchLength, 10,
                            outputpath=None, overwrite=False) as simResult:
        simResult.print_summary()

    #print("Running replications...")
    #Simulation.replicate(__file__, warmupLength, batchLength, 1, 1, 1)
    #print("Replications complete.")
    
    theory_results(meanInterarrivalTime.to_scalar(), meanServiceTime.to_scalar(),
                   serverCapacity)
