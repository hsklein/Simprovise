#===============================================================================
# script mm_1
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Demo model of an m/m/1 queue.
#===============================================================================
from simprovise.core.simrandom import SimDistribution
from simprovise.core.simtime import SimTime
from simprovise.modeling import (SimEntity, SimEntitySource, SimEntitySink,
                                 SimProcess, SimLocation, SimSimpleResource,
                                 SimQueue)
from simprovise.simulation import Simulation

mean_service_time = SimTime(8)
mean_interarrival_time = SimTime(10)

service_time_generator = SimDistribution.exponential(mean_service_time)
interarrival_time_generator = SimDistribution.exponential(mean_interarrival_time)

queue = SimQueue("Queue")
server = SimSimpleResource("Server")
server_location = SimLocation("ServerLocation")
customer_sink = SimEntitySink("Sink")

class Customer(SimEntity):
    """
    The customer being served by the Server.
    """
    
class mm1Process(SimProcess):
    """
    The m/m/1 customer service process:
    - Move to the queue
    - Acquire the server
    - Hold the server for the exponentially distributed service time
    - Release the server (done implicitly via ``with`` statement)
    - Move to the sink (and exit the simulation)      
    """
    def run(self):
        service_time = next(service_time_generator)
        customer = self.entity
        customer.move_to(queue)
        with self.acquire(server) as resource_assignment:
            customer.move_to(server_location)
            self.wait_for(service_time)            
        customer.move_to(customer_sink)

# Specify an entity source that generates Customer entities running the
# mm1Process at a rate defined by the (exponential) interarrival_time_generator. 
customer_source = SimEntitySource("Source", Customer, mm1Process,
                                  interarrival_time_generator)

if __name__ == '__main__':
    multi_replication = True
    nruns = 25
    warmup_length = SimTime(100)
    batch_length = SimTime(500)
    nbatches = 20
    
    if multi_replication:
        print("Running", nruns, "replications...")
        with Simulation.replicate(None, warmup_length, batch_length, 1,
                                  fromRun=1, toRun=nruns,
                                  outputpath=None, overwrite=False) as simResult:
            simResult.print_summary(rangetype='iqr',
                                    destination='mm1output/summary.txt')
            simResult.save_summary_csv('mm1output/summary.csv')
            simResult.export_dataset('Queue', 'Size', run=5, batch=None,
                                     filename='mm1output/queue_size_run5.csv')
    else:
        with Simulation.execute(warmup_length, batch_length, nbatches) as simResult:
            simResult.print_summary(rangetype='iqr')
            simResult.export_dataset('Server', 'ProcessTime', 
                                     filename='mm1_server_processtime.csv')
            simResult.save_summary_csv('mm1_summary.csv')
            simResult.save_database_as('mm_1.simoutput')
