============
Introduction
============

**simprovise** is a Python library for process-based discrete event simulation. 
It offers an object-oriented API for developing simulation models. 
Simprovise modelers create models by using or customizing (via inheritance)
classes representing simulation objects such as processes, resources,
resource pools, and locations (such as queues).

For example, the following code snippet implements an M/M/1 queuing model::

    queue = SimQueue("Queue")
    server = SimSimpleResource("Server")
    server_location = SimLocation("ServerLocation")
    customer_source = SimEntitySource("Source")
    customer_sink = SimEntitySink("Sink")

    mean_service_time = SimTime(8)
    service_time_generator = SimDistribution.exponential(mean_service_time)
    
    class Customer(SimEntity):
        "The customer being served by the Server"
        
    class mm1Process(SimProcess):
        def run(self):
            service_time = next(service_time_generator)
            customer = self.entity
            customer.move_to(queue)
            with self.acquire(server) as resource_assignment:
                customer.move_to(server_location)
                self.wait_for(service_time)            
            customer.move_to(customer_sink)
            
    mean_interarrival_time = SimTime(10)
    interarrival_generator = SimDistribution.exponential(mean_interarrival_time)
    
    # Instruct the entity source to create `customer` entities running
    # the `mm1Process` at an interarrival rate sampled from an
    # exponential distribution
    customer_source.add_entity_generator(Customer, mm1Process,
                                         interarrival_generator)

    if __name__ == '__main__':
        warmup = SimTime(4000)
        batch_length = SimTime(10000)
        nbatches = 10
        with Simulation.execute(warmup, batch_length, nbatches) as simResult:
            simResult.print_summary()



**simprovise** also provides APIs and tools for model execution, 
output data collection and output analysis, including:

* Parallel execution of multiple replications, each using  an independent 
  set of pseudo-random number streams.
* Output reports including summary statistics, through both batch means and
  replication analysis.
  
By way of example, below is a portion of the standard summary report
generated for the M/M/1 model above::

    ----------------------------------------------------------------------------------------------------------------------------------------------------------
                                                                Results: 1 Replication, 10 Batches                                                            
    Element ID                           Dataset         Sample Size    Sample Mean     25th Percentile       Median        75th Percentile         Max       
    ----------------------------------------------------------------------------------------------------------------------------------------------------------
    __main__.mm1Process                  In-Process        2020.80      3.65              0.90              2.70              5.40             18.80        
    __main__.mm1Process                  Entries           1010.80   1010.80           1010.80           1010.80           1010.80           1010.80        
    __main__.mm1Process                  Process-Time      1010.00     36.17             11.14             26.98             51.28            172.64        
    __main__.Customer                    Work-In-Process   2020.80      3.65              0.90              2.70              5.40             18.80        
    __main__.Customer                    Process-Time      1010.00     36.17             11.14             26.98             51.28            172.64        
    Queue                                Size              1811.70      2.86              0.00              1.70              4.40             17.80        
    Queue                                Entries           1009.80   1009.80           1009.80           1009.80           1009.80           1009.80        
    Queue                                Time              1010.00     28.29              2.46             17.89             42.52            160.78        
    Server                               ProcessTime       1010.00      7.89              2.27              5.42             10.94             60.81        
    Server                               Utilization       1220.10      0.80              0.90              1.00              1.00              1.00        
    Server                               DownTime             1.00      0.00              0.00              0.00              0.00              0.00        
    ServerLocation                       Population        1220.10      0.80              0.90              1.00              1.00              1.00        
    ServerLocation                       Entries           1010.00   1010.00           1010.00           1010.00           1010.00           1010.00        
    ServerLocation                       Time              1010.00      7.89              2.27              5.42             10.94             60.81        
 
By default, simprovise writes the output data collected during a simulation 
(or set of simulation replications) to
a temporary SQLite relational database; the report above is generated through
queries on that database. Users may also save output data as a CSV file. 
Users can save the output database itself if they wish to create and use their 
own queries.

Implementation Notes
--------------------

Simprovise implements process-based simulation using lightweight coroutines
provided by `greenlet. <https://pypi.org/project/greenlet/>`_ 
Greenlets are similar to the generator-based coroutines that are available
from the standard CPython distribution, while providing some additional
flexability. In particular, use of the ``yield`` keyword is not required,
and ``greenlet`` switching can occur in nested method calls.
In the case of simprovise, this allows blocking and process-switching to 
occur "under the covers" during a method call like ``acquire(resource)`` above;
a model developer using simprovise should have no need to see, use or even
understand the ``greenlet`` API.
