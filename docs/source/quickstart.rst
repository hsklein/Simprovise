================
Quick Start
================

To quickly introduce Simprovise, we'll build a simple model of a standard
M/M/1 queuing system - a single server with a single queue, and 
exponentially distributed interarrival and service times.

Start with some boilerplate ``import`` statements; we'll see how the 
imported classes are used further down::

    from simprovise.core.simrandom import SimDistribution
    from simprovise.core.simtime import SimTime
    from simprovise.modeling import (SimEntity, SimEntitySource, SimEntitySink,
    SimProcess, SimLocation, SimSimpleResource,
    SimQueue)
    from simprovise.simulation import Simulation
    
Next, we'll create Python generators for expontially distributed interarrival
and service times, using the imported Simprovise class
:class:`~simprovise.core.simrandom.SimDistribution`::

    mean_service_time = SimTime(8)
    mean_interarrival_time = SimTime(10)
    
    service_time_generator = SimDistribution.exponential(mean_service_time)
    interarrival_time_generator = SimDistribution.exponential(mean_interarrival_time)

Then we'll create the basic objects of the model: 

* A queue
* A server, which is a simprovise :ref:`*resource* <resource-concept-label>` 
  of type :class:`~simprovise.modeling.resource.SimSimpleResource>`.
* A :ref:`location <location-concept-label>` for the server.
* An :ref:`entity source <entity-source-concept-label>` that creates
  customers for the simulation.
* An :ref:`entity sink <entity-sink-concept-label>` where customers go to
  exit the simulation.
  
::

    queue = SimQueue("Queue")
    server = SimSimpleResource("Server")
    server_location = SimLocation("ServerLocation")
    customer_source = SimEntitySource("Source")
    customer_sink = SimEntitySink("Sink")

Then we'll define the Customer class, which in Simprovise is an
:ref:`entity <entity-concept-label>`. We don't need to modify any
of the base class behavior::

  class Customer(SimEntity):
      """
      The customer being served by the Server.
      """

Next, we'll define the :ref:`process <process-concept-label>` performed on
behalf of customers by creating a process class and defining its 
:meth:`~simprovise.modeling.process.SimProcess.run` method::

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

Now that we've defined the ``Customer`` (entity) and ``mm1Process`` (process)
classes, we can tell the ``customer_source`` how and when to create them via a 
call to :meth:`~simprovise.modeling.entitysource.add_entity_generator`::

    customer_source.add_entity_generator(Customer, mm1Process,
                                         interarrival_time_generator)
                                         
This call tells the entity generator to create ``Customer`` entities that run
the ``mm1Process``, with the time period between customers coming from the
``interarrival_time_generator``.

That defines the simulation model; all that's left is to execute it, which 
can be done within the ``__main__`` guard of the script::

    if __name__ == '__main__':
        warmup_length = SimTime(4000)
        batch_length = SimTime(10000)
        nbatches = 10
        with Simulation.execute(warmup_length, batch_length, nbatches) as simResult:
            simResult.print_summary()

This code executes the model once with a warmup period and ten batches; the
result is a summary report doing batch means analysis of the simulation output::

    ----------------------------------------------------------------------------------------------------------------------------------------------------------
                                                                Results: 1 Replication, 10 Batches                                                            
    Element ID                           Dataset         Sample Size    Sample Mean     25th Percentile       Median        75th Percentile         Max       
    ----------------------------------------------------------------------------------------------------------------------------------------------------------
    __main__.mm1Process                  In-Process        2020.80      3.65              0.90              2.70              5.40             18.80        
    __main__.mm1Process                  Entries           1010.80   1010.80           1010.80           1010.80           1010.80           1010.80        
    __main__.mm1Process                  Process-Time      1010.00     36.17             11.14             26.98             51.28            172.64        
    simprovise.modeling.entity.SimEntity Work-In-Process      1.00      0.00              0.00              0.00              0.00              0.00        
    simprovise.modeling.entity.SimEntity Process-Time         0.00       nan               nan               nan               nan               nan        
    __main__.Customer                    Work-In-Process   2020.80      3.65              0.90              2.70              5.40             18.80        
    __main__.Customer                    Process-Time      1010.00     36.17             11.14             26.98             51.28            172.64        
    Queue                                Population        1811.70      2.86              0.00              1.70              4.40             17.80        
    Queue                                Entries           1009.80   1009.80           1009.80           1009.80           1009.80           1009.80        
    Queue                                Time              1010.00     28.29              2.46             17.89             42.52            160.78        
    Server                               ProcessTime       1010.00      7.89              2.27              5.42             10.94             60.81        
    Server                               Utilization       1220.10      0.80              0.90              1.00              1.00              1.00        
    Server                               DownTime             1.00      0.00              0.00              0.00              0.00              0.00        
    ServerLocation                       Population        1220.10      0.80              0.90              1.00              1.00              1.00        
    ServerLocation                       Entries           1010.00   1010.00           1010.00           1010.00           1010.00           1010.00        
    ServerLocation                       Time              1010.00      7.89              2.27              5.42             10.94             60.81        
    Source                               Population        1010.80      0.00              0.00              0.00              0.00              0.00        
    Source                               Entries           1009.80   1009.80           1009.80           1009.80           1009.80           1009.80        
    Source                               Time              1009.80      0.00              0.00              0.00              0.00              0.00  

Some key output metrics:

* Mean (Customer) Work-in-Process: 3.65
* Mean (Customer) Process (Flow) Time: 36.17
* Mean Queue Time: 28.29
* Mean Queue Size: 2.86
* Server Utilization: 80%