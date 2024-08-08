=====================
Tutorial 
=====================

All of the **simprovise** tutorials involve modeling a bank with
customers and tellers who service the customer's transactions; each 
tutorial builds on the previous models, introducing new *simprovise* 
features:

* :ref:`The first tutorial <bank-1-tutorial-label>` introduces a simple
  bank model that for all intents and purposes, is a re-labeled M/M/c
  queuing model, where the tellers are "servers". It introduces basic 
  *simprovise* modeling concepts and the
  mechanisms for executing simulations and reporting their output.  
* The :ref:`second tutorial <bank-2-tutorial-label>` adds to the model by
  creating "Regular" and "Merchant" subclasses for both customers and tellers.
  It demonstrates how queue prioritization, the *simprovise* resource pool,
  and leveraging of the ``Teller`` class hierarchy can be used to easily implement 
  a fairly complex algorithm for assigning customers to tellers.  
* The :ref:`third tutorial <bank-3-tutorial-label>` introduces customized
  code to a model-defined subclass of the *simprovise* resource pool,
  using it to further refine the teller assignment algorithm by writing
  our own assignment code. 
* The :ref:`fourth tutorial <bank-4-tutorial-label>` demonstrates the
  use of resource acquisition timeouts by by adding the capability for
  customers to "bail out" of the waiting-for-a-teller queue if the wait
  gets too long. It also introduces the use of model-defined custom 
  datasets, allowing the modeler to collect simulation output data beyond that 
  which is collected automatically.   
* The :ref:`fifth tutorial <bank-5-tutorial-label>` is actually a sequence of
  four sub-tutorials. The first demonstrates a rearrangement and 
  refactoring of the third model to capture common modeling code in a
  separate module. The remaining models incorporate teller shift breaks,
  demonstrating various ways to implement resource downtime into 
  *simprovise* models.
  

.. _bank-1-tutorial-label:

Bank Model: Round 1
===================

We will start by simulating a simple bank. The bank consists of one or more tellers,
stationed at a counter. The bank has a single queue for waiting customers.

Customers enter the bank and then immediately enter the queue. When they reach the 
head of the queue, they wait for the next available teller. When a teller becomes
available, they move to the teller counter and execute their transaction with the
teller. When finished, they leave the bank.

In the language of Simprovise, the bank, teller counter, and queue are
:ref:`location-concept-label`, with the counter and queue being nested 
sublocations of the bank.
The customers are :ref:`entity-concept-label`. The actions that the 
customers perform (entering the bank/queue, waiting for and moving to a teller,
executing a transaction, leaving) are a :ref:`process <process-concept-label>`.
Tellers are :ref:`resource-concept-label` to be acquired and used by
customers.

As with all Simprovise models, our bank model will also require a
:ref:`entity source <entity-source-concept-label>` and an 
:ref:`entity sink <entity-sink-concept-label>`. The source creates customers 
and their corresponding process objects; it then starts that process. 
The process completes by moving the entity to the sink.

As with many/most simulations, part of the model is stochastic; in particular,
both the customer arrival rate and customer service time (time spent at a 
teller) are based on sampling from a psuedo-random distribution. For this
model, we will make both the interrarrival time and the service times 
exponentially distributed. In effect, this makes our bank model a slightly
dressed-up version of an m/m/c queue (where c is the number of tellers).

Building the Model
------------------

This entire bank model is implemented in a single Python script,
:doc:`bank1.py <bank1_py>`, found in the installed demos directory. The modeling 
code is shown and described below, minus the required import statements. (See the
source script for those.)

First we define the Teller class as a subclass of `SimSimpleResource`, a
basic Simprovise resource construct with an integer `capacity` attribute;
setting the capacity to more than one can simulate multiple tellers.
Note that we don't override or add any attributes or behavior to 
`SimSimpleResource`; we are just creating a new name to categorize our 
resources, which will come in handy later::

    class Teller(SimSimpleResource):
        """
        A set of bank teller resources (capacity > 1 represents multiple
        tellers)
        """

We can then define our Customer class as a `SimEntity` subclass in a
similar fashion::

    class Customer(SimEntity):
        """
        Base class for bank customer entities
        """

Then we define the Bank class as a subclass of Simprovise's `SimLocation`;
in this case, we do add attributes to represent the bank's sublocations
and teller resource(s). The sublocations are the teller counter (another
`SimLocation`) and the customer queue, a `SimQueue` (a subclass of 
`SimLocation` provided by the Simprovise library)::

    class Bank(SimLocation):
        """
        A SimLocation that encapsulates all of the objects (resources,
        queues and locations) that comprise a bank.
        """
        def __init__(self, name="Bank", nTellers=1):
            super().__init__(name)
            self.teller_counter = SimLocation("TellerCounter", self)
            self.teller = Teller("Teller", self.teller_counter, capacity = nTellers)       
            self.customer_queue = SimQueue("CustomerQueue", self)

Next, we'll actually create entity source, entity sink, and bank objects::

    source = SimEntitySource("Source")
    sink = SimEntitySink("Sink")
    bank = Bank(nTellers=4)
    
Then we will create (Python) generator objects that yield simulated interarrival 
and service times sampled from an exponential distribution. Times are specified using
Simprovise class `SimTime`, which for this model, we specify in minutes. (See
:ref:`simulated-time-concept-label`)::

    mean_interarrival_time = SimTime(1, tu.MINUTES)
    mean_service_time = SimTime(3, tu.MINUTES) 
    servicetime_generator = SimDistribution.exponential(mean_service_time)
    interarrivaltime_generator = SimDistribution.exponential(mean_interarrival_time)
    
With these objects in place, we can define our BankTransaction 
:ref:`process <process-concept-label>` subclass. All `SimProcess` classes
used in a Simprovise model must implement the `run()` method which encodes
all of the actions performed by/for the customer/entity::

    class BankTransaction(SimProcess):
        """
        Class for simulated bank transaction classes
        """        
        def run(self):
            service_time = next(servicetime_generator)
            customer = self.entity
            customer.move_to(bank.customer_queue)
            with self.acquire(bank.teller) as teller_assignment:
                customer.move_to(bank.teller_counter)
                self.wait_for(service_time)
            customer.move_to(sink)

A few notes on the `run()` code:

* `servicetime_generator` is a Python generator object, so `next()` will
  return the next sample value
* Class `SimProcess` has an `entity` property which returns the entity
  (in this case a `Customer`) created with the process by the entity source.
* `move_to()` moves an entity from one location to another. By default, it
  happens instantly (no simulated time passes)
* `acquire()` acquires a resource (in this case, a teller) on behalf of 
  the customer entity. By default, the request is for one resource (or one
  of a multi-capacity resource). If the resource is not available, this 
  call will block until the resource is acquired.
* Information about the acquired resource is included in the returned
  teller_assignment, an object of class `SimResourceAssignment`
* `wait_for` waits/blocks for the specified amount of simulated time.
* Resources must be released when the process/entity has finished using
  them. The teller assignment here is being used as a Python context
  manager which automatically releases the acquired resource(s) when
  leaving the `with` block. Alternatively, `run()` code can explicitly
  make a `release()` call.

With the entity class, process class and interarrival generator defined, 
we can finally tell the entity source how to generate entities and processes::

    source.add_entity_generator(Customer, BankTransaction, interarrivaltime_generator)

.. _bank-1-tutorial-single-execution-label:

Executing the Model
-------------------

Simprovise models can be executed in a number of ways, including right from the
model Python script (with an `if __name__ == '__main__':` guard). We'll start
by doing a single simulation run with the following parameters:

* Warmup Length: The length of (simulated) time for the simulation to reach
  steady state. The Simprovise output analysis tools will ignore data from
  the warmup period. For this model, we will start with a warmup length of
  100 minutes
* Batch Length: For a single run, we can use a batch means technique to 
  generate confidence intervals for simulation output metrics. Batch length
  is the simulated time for each batch - in this case 1000 minutes.
* Number of Batches: the number of batches to execute, here specified as 10.

With these parameters, the simulation will be run for a total of 10,100
simulated minutes (100 minutes warmup, 10 x 1,000 minute batches)::

    if __name__ == '__main__':
        warmupLength = SimTime(100, tu.MINUTES)
        batchLength = SimTime(1000, tu.MINUTES)
        nbatches = 10
        print("Running single execution...")
        with Simulation.execute(warmupLength, batchLength, nbatches) as simResult:
            simResult.print_summary()

By default, Simprovise collects a variety of data on the model's processes,
locations, resources and entities during a simulation run, writes those data
to a temporary output database, and returns a `SimResult` object that can
generate a tabular report from that database. Via the use of a context manager,
the database is deleted once the SimResult object goes out of scope. In this
case, we generated a summary report, the left-hand side of which is shown 
below::

    Run 1 execution complete: 60431 events processed. Process Time: 2.66143536567688
    simprovise.simulation INFO:	348	Simulation result created for output DB C:\Users\hklei\AppData\Local\Temp\tmpb7ul4icf.simoutput isTemporary: True
    ----------------------------------------------------------------------------------------------------------------------------------------------
                                                          Results: 1 Replication, 10 Batches                                                      
    Element ID                           Dataset            Sample Mean     25th Percentile       Median        75th Percentile         Max       
    ----------------------------------------------------------------------------------------------------------------------------------------------
    __main__.BankTransaction             In-Process           4.67              2.00              3.70              6.30             20.00        
    __main__.BankTransaction             Entries            998.00            998.00            998.00            998.00            998.00        
    __main__.BankTransaction             Process-Time         4.68 minutes      1.58 minutes      3.58 minutes      6.68 minutes     26.15 minutes
    simprovise.modeling.entity.SimEntity Work-In-Process      0.00              0.00              0.00              0.00              0.00        
    __main__.Customer                    Work-In-Process      4.67              2.00              3.70              6.30             20.00        
    __main__.Customer                    Process-Time         4.68 minutes      1.58 minutes      3.58 minutes      6.68 minutes     26.15 minutes
    Source                               Population           0.00              0.00              0.00              0.00              0.00        
    Source                               Entries            997.00            997.00            997.00            997.00            997.00        
    Source                               Time                 0.00 minutes      0.00 minutes      0.00 minutes      0.00 minutes      0.00 minutes
    Bank                                 Population           4.67              2.00              3.70              6.30             20.00        
    Bank                                 Entries            997.00            997.00            997.00            997.00            997.00        
    Bank                                 Time                 4.68 minutes      1.58 minutes      3.58 minutes      6.68 minutes     26.15 minutes
    Bank.TellerCounter                   Population           2.99              2.00              3.70              4.00              4.00        
    Bank.TellerCounter                   Entries            997.00            997.00            997.00            997.00            997.00        
    Bank.TellerCounter                   Time                 3.00 minutes      0.84 minutes      2.04 minutes      4.19 minutes     23.29 minutes
    Bank.TellerCounter.Teller            ProcessTime          3.00 minutes      0.84 minutes      2.04 minutes      4.19 minutes     23.29 minutes
    Bank.TellerCounter.Teller            Utilization          0.75              0.50              0.93              1.00              1.00        
    Bank.TellerCounter.Teller            DownTime             0.00              0.00              0.00              0.00              0.00        
    Bank.CustomerQueue                   Size                 1.68              0.00              0.00              2.30             16.00        
    Bank.CustomerQueue                   Entries            997.00            997.00            997.00            997.00            997.00        
    Bank.CustomerQueue                   Time                 1.67 minutes      0.00 minutes      0.26 minutes      2.46 minutes     12.69 minutes
    Closing and removing output database...

A few notes/observations:

* The Teller utilization averages 75%, which is what we would expect (4 tellers, 
  mean one customer arrival per minute, mean 3 minutes service time per teller 
  visit)
* The various location Entries represent the number of entities (customers) 
  entering per 1,000 minute batch. The mean value of 997 tracks with one 
  arrival per minute
* The most relevant measures are the mean queue time and mean queue population 
  (length)
* The output report has several data display options and can also be saved in
  CSV format; see :doc:`output_database` for details.
* While we typically delete the raw output database after generating report(s), 
  it can be saved for further analysis

.. _bank-1-tutorial-multiple-replications-label:

Running Multiple Replications
-----------------------------

Simprovise also supports running multiple replications of a simulation model, 
with each replication automatically using a different set of random number 
streams. To do so, use ``Simulation.replicate()``::

    if __name__ == '__main__':
        warmupLength = SimTime(100, tu.MINUTES)
        batchLength = SimTime(1000, tu.MINUTES)
        nbatches = 1
        nruns = 10
        print("Running {0} replications...".format(nruns))            
        with Simulation.replicate(None, warmupLength, batchLength, nbatches,
                                  fromRun=1, toRun=nruns) as simResult:
            simResult.print_summary()

In this case, we are doing ten replications. The maximum number of replications 
(really, the maximum `toRun` value) is configurable via .ini configuration 
files (See :doc:`configuration`); the default maximum is generally 100. The 
generated summary report::

    ----------------------------------------------------------------------------------------------------------------------------------------------
                                                               Results: 10 Replications                                                           
    Element ID                           Dataset            Sample Mean     25th Percentile       Median        75th Percentile         Max       
    ----------------------------------------------------------------------------------------------------------------------------------------------
    __main__.BankTransaction             In-Process           4.79              2.30              3.90              6.50             18.10        
    __main__.BankTransaction             Entries           1021.80           1021.80           1021.80           1021.80           1021.80        
    __main__.BankTransaction             Process-Time         4.68 minutes      1.71 minutes      3.73 minutes      6.69 minutes     25.23 minutes
    simprovise.modeling.entity.SimEntity Work-In-Process      0.00              0.00              0.00              0.00              0.00        
    __main__.Customer                    Work-In-Process      4.79              2.30              3.90              6.50             18.10        
    __main__.Customer                    Process-Time         4.68 minutes      1.71 minutes      3.73 minutes      6.69 minutes     25.23 minutes
    Source                               Population           0.00              0.00              0.00              0.00              0.00        
    Source                               Entries           1020.80           1020.80           1020.80           1020.80           1020.80        
    Source                               Time                 0.00 minutes      0.00 minutes      0.00 minutes      0.00 minutes      0.00 minutes
    Bank                                 Population           4.79              2.30              3.90              6.50             18.10        
    Bank                                 Entries           1020.80           1020.80           1020.80           1020.80           1020.80        
    Bank                                 Time                 4.68 minutes      1.71 minutes      3.73 minutes      6.69 minutes     25.23 minutes
    Bank.TellerCounter                   Population           3.09              2.30              3.80              4.00              4.00        
    Bank.TellerCounter                   Entries           1020.20           1020.20           1020.20           1020.20           1020.20        
    Bank.TellerCounter                   Time                 3.03 minutes      0.86 minutes      2.09 minutes      4.24 minutes     21.68 minutes
    Bank.TellerCounter.Teller            ProcessTime          3.03 minutes      0.86 minutes      2.09 minutes      4.24 minutes     21.68 minutes
    Bank.TellerCounter.Teller            Utilization          0.77              0.57              0.95              1.00              1.00        
    Bank.TellerCounter.Teller            DownTime             0.00              0.00              0.00              0.00              0.00        
    Bank.CustomerQueue                   Size                 1.69              0.00              0.10              2.50             14.10        
    Bank.CustomerQueue                   Entries           1020.80           1020.80           1020.80           1020.80           1020.80        
    Bank.CustomerQueue                   Time                 1.65 minutes      0.00 minutes      0.35 minutes      2.60 minutes     11.65 minutes


.. _bank-1-event-tracing-tutorial-label:

Event Tracing
-------------

Simprovise also provides a event tracing feature, generating a report of the 
key simulation events - entity move_to()s, entity acquisition and release of 
resources, and resource down time (more on that below).

Tracing can be turned on or off via settings in the [SimTrace] configuration 
file section. These settings also provide the ability to:

* Limit the number of events traced
* Specify either output as either a CSV file or formatted text
* Specify whether output is written to `stdout` or a file

Some of the default tabular output from our bank model is shown below::

        Time                                                                                    
  ==============================================================================================
        1.03 Customer 1      Move-to   Bank.CustomerQueue                                       
        1.03 Customer 1      Acquiring Bank.TellerCounter.Teller                                
        1.03 Customer 1      Acquired  Bank.TellerCounter.Teller                                
        1.03 Customer 1      Move-to   Bank.TellerCounter                                       
        2.08 Customer 2      Move-to   Bank.CustomerQueue                                       
        2.08 Customer 2      Acquiring Bank.TellerCounter.Teller                                
        2.08 Customer 2      Acquired  Bank.TellerCounter.Teller                                
        2.08 Customer 2      Move-to   Bank.TellerCounter                                       
        2.70 Customer 2      Release   Bank.TellerCounter.Teller                                
        2.70 Customer 2      Move-to   Sink                                                     
        4.70 Customer 3      Move-to   Bank.CustomerQueue                                       
        4.70 Customer 3      Acquiring Bank.TellerCounter.Teller                                
        4.70 Customer 3      Acquired  Bank.TellerCounter.Teller                                
        4.70 Customer 3      Move-to   Bank.TellerCounter                                       
        5.07 Customer 4      Move-to   Bank.CustomerQueue                                       
        5.07 Customer 4      Acquiring Bank.TellerCounter.Teller                                
        5.07 Customer 4      Acquired  Bank.TellerCounter.Teller                                
        5.07 Customer 4      Move-to   Bank.TellerCounter                                       
        5.11 Customer 5      Move-to   Bank.CustomerQueue                                       
        5.11 Customer 5      Acquiring Bank.TellerCounter.Teller                                
        5.11 Customer 5      Acquired  Bank.TellerCounter.Teller                                
        5.11 Customer 5      Move-to   Bank.TellerCounter                                       
        5.31 Customer 1      Release   Bank.TellerCounter.Teller                                
        5.31 Customer 1      Move-to   Sink                                                     
        5.44 Customer 3      Release   Bank.TellerCounter.Teller                                
        5.44 Customer 3      Move-to   Sink                                                     
        5.80 Customer 6      Move-to   Bank.CustomerQueue                                       
        5.80 Customer 6      Acquiring Bank.TellerCounter.Teller                                
        5.80 Customer 6      Acquired  Bank.TellerCounter.Teller                                
        5.80 Customer 6      Move-to   Bank.TellerCounter                                       
        6.15 Customer 7      Move-to   Bank.CustomerQueue                                       
        6.15 Customer 7      Acquiring Bank.TellerCounter.Teller                                
        6.15 Customer 7      Acquired  Bank.TellerCounter.Teller                                
        6.15 Customer 7      Move-to   Bank.TellerCounter                                       
        7.23 Customer 7      Release   Bank.TellerCounter.Teller                                
        7.23 Customer 7      Move-to   Sink                                                     
        8.93 Customer 4      Release   Bank.TellerCounter.Teller                                
        8.93 Customer 4      Move-to   Sink                                                     
        9.66 Customer 8      Move-to   Bank.CustomerQueue                                       
        9.66 Customer 8      Acquiring Bank.TellerCounter.Teller                                
        9.66 Customer 8      Acquired  Bank.TellerCounter.Teller                                
        9.66 Customer 8      Move-to   Bank.TellerCounter                                       
       10.63 Customer 6      Release   Bank.TellerCounter.Teller                                
       10.63 Customer 6      Move-to   Sink                                                     
       11.19 Customer 9      Move-to   Bank.CustomerQueue                                       
       11.19 Customer 9      Acquiring Bank.TellerCounter.Teller                                

It is also possible to add data to this table within model code via 
calls to :func:`~simprovise.core.simtrace.add_trace_column`, where each 
call specifies an object and property value to add to each trace row; 
e.g the following code will show the number of available tellers at the time 
of each event::

    simtrace.add_trace_column(bank.teller, 'available', 'Tellers: available')

The output now looks like this::

        Time                                                                Tellers: available 
  =================================================================================================
        1.03 Customer 1      Move-to   Bank.CustomerQueue                              4           
        1.03 Customer 1      Acquiring Bank.TellerCounter.Teller                       4           
        1.03 Customer 1      Acquired  Bank.TellerCounter.Teller                       3           
        1.03 Customer 1      Move-to   Bank.TellerCounter                              3           
        2.08 Customer 2      Move-to   Bank.CustomerQueue                              3           
        2.08 Customer 2      Acquiring Bank.TellerCounter.Teller                       3           
        2.08 Customer 2      Acquired  Bank.TellerCounter.Teller                       2           
        2.08 Customer 2      Move-to   Bank.TellerCounter                              2           
        2.70 Customer 2      Release   Bank.TellerCounter.Teller                       2           
        2.70 Customer 2      Move-to   Sink                                            3           
        4.70 Customer 3      Move-to   Bank.CustomerQueue                              3           
        4.70 Customer 3      Acquiring Bank.TellerCounter.Teller                       3           
        4.70 Customer 3      Acquired  Bank.TellerCounter.Teller                       2           
        4.70 Customer 3      Move-to   Bank.TellerCounter                              2           
        5.07 Customer 4      Move-to   Bank.CustomerQueue                              2           
        5.07 Customer 4      Acquiring Bank.TellerCounter.Teller                       2           
        5.07 Customer 4      Acquired  Bank.TellerCounter.Teller                       1           
        5.07 Customer 4      Move-to   Bank.TellerCounter                              1           
        5.11 Customer 5      Move-to   Bank.CustomerQueue                              1           
        5.11 Customer 5      Acquiring Bank.TellerCounter.Teller                       1           
        5.11 Customer 5      Acquired  Bank.TellerCounter.Teller                       0           
        5.11 Customer 5      Move-to   Bank.TellerCounter                              0           
        5.31 Customer 1      Release   Bank.TellerCounter.Teller                       0           
        5.31 Customer 1      Move-to   Sink                                            1           
        5.44 Customer 3      Release   Bank.TellerCounter.Teller                       1           


.. _bank-2-tutorial-label:

Bank Model Round 2: Adding A Merchant Teller
=============================================

Our second model, :doc:`bank2.py <bank2_py>`, will expand on 
:ref:`bank1 <bank-1-tutorial-label>` 
by dividing our customers into two types: merchant customers and regular 
customers, with separate queues for each. We will also include two 
corresponding types of tellers.

In this model merchant customers enter the ban and join the merchant queue.
When they reach the front of the line, they are assigned to the next 
available merchant teller.

Regular customers enter the "regular" queue. When they reach the front of the
line, they are assigned to the next available "regular" teller - unless
the merchant teller is idle and there are no merchant customer tellers
in the queue. In that case, the merchant teller can service a regular customer.

The behavior described above is conceptually modeled as follows:

* We create two subclasses of `Customer`, `MerchantCustomer` and `RegularCustomer`.
  These subclasses each define the function `priority()`; for `MerchantCustomer`
  it returns 1, for `RegularCustomer` 2.
* We create two subclasses of `Teller`, `MerchantTeller` and `RegularTeller`.
  We create one instance of each of these classes, with capacities equal to
  the number of merchant and regular tellers working at the bank.
* We assign both teller instances to a 
  :ref:`resource pool <resource-pool-concept-label>`, which manages customer
  assignment to both types of tellers
* We add a priority function to the resource pool. This function takes one
  argument - the resource request object - and returns a priority. The resource
  request object includes an `entity` attribute, which in this case is the
  merchant or regular customer that made the request for a teller resource. 
  The function just returns the entity's priority as described above.
* Finally, we create `MerchantTransaction` and `RegularTransaction` subclasses
  of `BankTransaction`. Now, the `run()` methods request a teller from the
  resource pool. Resource pool requests can specify a resource class
  instead of a specific resource. In this case, the merchant transaction 
  requests a resource of class `MerchantTeller`, while the regular transaction
  requests the more general class `Teller`. this allows regular customers
  to acquire a merchant teller, but the priority function ensures that
  merchant customers will get first dibs.

Building the Model
-----------------------
The bank2.py model largely consists of additions (and some modifications)
to bank1.py

First, we will create our merchant and regular customer entity types by
subclassing our existing Customer class, also defining the priority 
functions described above::

    class RegularCustomer(Customer):
        """
        Regular (not merchant) bank customer
        """
        def priority(self):
            return 2
    
    class MerchantCustomer(Customer):
        """
        Merchant bank customer
        """
        def priority(self):
            return 1
        
Next we will create corresponding subclasses of our Teller resource,
while adding `__str__()` methods in order to make trace output more 
concise::

    class RegularTeller(Teller):
        """
        A teller primarily for regular customers
        """
        def __str__(self):
            return "RegularTeller"
    
    class MerchantTeller(Teller):
        """
        A teller primarily for merchant customers
        """
        def __str__(self):
            return "MerchantTeller"

Then we expand the class definition of our Bank location to include
both types of tellers and two queues. As noted above, this model also introduces
the concept of a :ref:`resource pool <resource-pool-concept-label>`. 
The bank now has a resource pool that includes all of the tellers, both
merchant and regular. The code for our bank transaction processes 
(below) will demonstrate how the use of a pool can help us::

    class Bank(SimLocation):
        """
        A simLocation that encapsulates all of the objects (resources,
        queues and locations) that comprise a bank.
        """    
        @staticmethod
        def get_priority(teller_request):
            """
            The priority function to be registered with the teller
            resource pool. It returns the value of the priority()
            function implemented by the requests 
            """
            return teller_request.entity.priority()
            
        def __init__(self, name="Bank", nRegularTellers=4, nMerchantTellers=1):
            super().__init__(name)
            self.teller_counter = SimLocation("TellerCounter", self)
            self.regular_teller = RegularTeller("RegularTeller",
                                                self.teller_counter,
                                                capacity = nRegularTellers)
            
            self.merchant_teller = MerchantTeller("MerchantTeller",
                                                  self.teller_counter,
                                                  capacity = nMerchantTellers)
            
            self.teller_pool = SimResourcePool(self.regular_teller, 
                                               self.merchant_teller)
            
            # Specify a resource request priority function for the teller pool
            self.teller_pool.request_priority_func = Bank.get_priority
            
            self.regular_queue = SimQueue("RegularQueue", self)
            self.merchant_queue = SimQueue("MerchantQueue", self)
            
The source and sink are created as before, along with the bank::

    source = SimEntitySource("Source")
    sink = SimEntitySink("Sink")    
    bank = Bank(name="Bank", nRegularTellers=2, nMerchantTellers=1)
    
We create subclasses of `BankTransaction` for both regular and merchant 
transactions. The `run()` methods acquire tellers from the resource pool.
As described above, merchant customers get only merchant tellers, while
regular customers will go to either type of teller.
Since we now need mean interarrival and service time for each class, we
make those values class variables, along with the class-specific service
time generator required by each `run()` method. The higher mean service 
time for regular transactions will ensure that 
some regular customers are directed to the merchant teller::

    class RegularTransaction(BankTransaction):
        """
        Represents a "regular" transaction by a "regular" (non-merchant)
        customer.
        """
        mean_interarrival_time = SimTime(1, tu.MINUTES)
        mean_service_time = SimTime(2, tu.MINUTES) 
        st_generator = SimDistribution.exponential(mean_service_time)
    
        def run(self):
            service_time = next(RegularTransaction.st_generator)
            customer = self.entity
            customer.move_to(bank.regular_queue)
            with self.acquire_from(bank.teller_pool, Teller) as teller_assignment:
                teller = teller_assignment.resource
                customer.move_to(bank.teller_counter)
                self.wait_for(service_time)
            customer.move_to(sink)
    
    class MerchantTransaction(BankTransaction):
        """
        Represents a merchant transaction (by a merchant customer)
        """
        mean_interarrival_time = SimTime(6, tu.MINUTES)
        mean_service_time = SimTime(3, tu.MINUTES)
        st_generator = SimDistribution.exponential(mean_service_time)
    
        def run(self):
            service_time = next(MerchantTransaction.st_generator)
            customer = self.entity
            customer.move_to(bank.merchant_queue)
            with self.acquire_from(bank.teller_pool, MerchantTeller) as teller_assignment:
                teller = teller_assignment.resource
                customer.move_to(bank.teller_counter)
                self.wait_for(service_time)
            customer.move_to(sink)

Finally, we need entity generators for both regular and merchant customers.
Both generators can be assigned to our single 
:ref:`entity source <entity-source-concept-label>`::
    
    # Define and create the (customer) entity generators for the model's entity
    # source.
    dist_reg = SimDistribution.exponential(RegularTransaction.mean_interarrival_time) 
    dist_merch = SimDistribution.exponential(MerchantTransaction.mean_interarrival_time) 
    source.add_entity_generator(RegularCustomer, RegularTransaction, dist_reg)
    source.add_entity_generator(MerchantCustomer, MerchantTransaction, dist_merch)

We'll also specify some different columns to add to the trace output::

    simtrace.add_trace_column(bank.regular_queue, 'current_population', 'Reg Queue')
    simtrace.add_trace_column(bank.merchant_queue, 'current_population', 'Merch Queue')
    simtrace.add_trace_column(bank.regular_teller, 'available', 'Reg: avail')
    simtrace.add_trace_column(bank.merchant_teller, 'available', 'Merch: avail')

Simulation Trace Output
-----------------------

::

        Time                                        Reg Queue Merch Queue Reg: avail Merch: avail 
  ===================================================================================================================================================================
    1.03 RegularCustomer 1 Move-to   Bank.RegularQueue    0        0          2         1        
    1.03 RegularCustomer 1 Acquiring Teller               1        0          2         1        
    1.03 RegularCustomer 1 Acquired  RegularTeller        1        0          1         1        
    1.03 RegularCustomer 1 Move-to   Bank.TellerCounter   0        0          1         1        
    2.46 RegularCustomer 2 Move-to   Bank.RegularQueue    0        0          1         1        
    2.46 RegularCustomer 2 Acquiring Teller               1        0          1         1        
    2.46 RegularCustomer 2 Acquired  RegularTeller        1        0          0         1        
    2.46 RegularCustomer 2 Move-to   Bank.TellerCounter   0        0          0         1        
    2.66 RegularCustomer 3 Move-to   Bank.RegularQueue    0        0          0         1        
    2.66 RegularCustomer 3 Acquiring Teller               1        0          0         1        
    2.66 RegularCustomer 3 Acquired  MerchantTeller       1        0          0         0        
    2.66 RegularCustomer 3 Move-to   Bank.TellerCounter   0        0          0         0        
    2.76 RegularCustomer 3 Release   MerchantTeller       0        0          0         0        
    2.76 RegularCustomer 3 Move-to   Sink                 0        0          0         1        


Simulation Results/Analysis
---------------------------
::

    Run 1 execution complete: 42390 events processed. Process Time: 2.108820676803589
    ----------------------------------------------------------------------------------------------------------------------------------------------
                                                          Results: 1 Replication, 10 Batches                                                      
    Element ID                           Dataset            Sample Mean     25th Percentile       Median        75th Percentile         Max       
    ----------------------------------------------------------------------------------------------------------------------------------------------
    __main__.BankTransaction             In-Process           0.00              0.00              0.00              0.00              0.00        
    __main__.BankTransaction             Entries              1.00              1.00              1.00              1.00              1.00        
    __main__.RegularTransaction          In-Process           5.83              1.70              3.80              8.70             24.60        
    __main__.RegularTransaction          Entries            596.80            596.80            596.80            596.80            596.80        
    __main__.RegularTransaction          Process-Time         5.84 minutes      1.79 minutes      4.20 minutes      8.88 minutes     24.70 minutes
    __main__.MerchantTransaction         In-Process           1.32              0.00              0.80              2.00              7.10        
    __main__.MerchantTransaction         Entries            101.80            101.80            101.80            101.80            101.80        
    __main__.MerchantTransaction         Process-Time         7.82 minutes      2.90 minutes      5.94 minutes     10.79 minutes     28.07 minutes
    simprovise.modeling.entity.SimEntity Work-In-Process      0.00              0.00              0.00              0.00              0.00        
    __main__.Customer                    Work-In-Process      0.00              0.00              0.00              0.00              0.00        
    __main__.RegularCustomer             Work-In-Process      5.83              1.70              3.80              8.70             24.60        
    __main__.RegularCustomer             Process-Time         5.84 minutes      1.79 minutes      4.20 minutes      8.88 minutes     24.70 minutes
    __main__.MerchantCustomer            Work-In-Process      1.32              0.00              0.80              2.00              7.10        
    __main__.MerchantCustomer            Process-Time         7.82 minutes      2.90 minutes      5.94 minutes     10.79 minutes     28.07 minutes
    Source                               Population           0.00              0.00              0.00              0.00              0.00        
    Source                               Entries            696.60            696.60            696.60            696.60            696.60        
    Source                               Time                 0.00 minutes      0.00 minutes      0.00 minutes      0.00 minutes      0.00 minutes
    Bank                                 Population           7.14              2.40              5.20             10.30             26.50        
    Bank                                 Entries            696.60            696.60            696.60            696.60            696.60        
    Bank                                 Time                 6.14 minutes      1.89 minutes      4.43 minutes      8.91 minutes     31.19 minutes
    Bank.TellerCounter                   Population           2.49              2.10              3.00              3.00              3.00        
    Bank.TellerCounter                   Entries            694.60            694.60            694.60            694.60            694.60        
    Bank.TellerCounter                   Time                 2.15 minutes      0.61 minutes      1.46 minutes      2.96 minutes     17.96 minutes
    Bank.TellerCounter.RegularTeller     ProcessTime          2.02 minutes      0.59 minutes      1.40 minutes      2.80 minutes     14.06 minutes
    Bank.TellerCounter.RegularTeller     Utilization          0.83              0.70              1.00              1.00              1.00        
    Bank.TellerCounter.RegularTeller     DownTime             0.00              0.00              0.00              0.00              0.00        
    Bank.TellerCounter.MerchantTeller    ProcessTime          2.48 minutes      0.68 minutes      1.64 minutes      3.29 minutes     16.61 minutes
    Bank.TellerCounter.MerchantTeller    Utilization          0.84              1.00              1.00              1.00              1.00        
    Bank.TellerCounter.MerchantTeller    DownTime             0.00              0.00              0.00              0.00              0.00        
    Bank.RegularQueue                    Size                 3.84              0.00              1.30              6.10             22.10        
    Bank.RegularQueue                    Entries            595.80            595.80            595.80            595.80            595.80        
    Bank.RegularQueue                    Time                 3.83 minutes      0.02 minutes      1.74 minutes      6.56 minutes     17.86 minutes
    Bank.MerchantQueue                   Size                 0.82              0.00              0.00              1.20              6.10        
    Bank.MerchantQueue                   Entries            100.80            100.80            100.80            100.80            100.80        
    Bank.MerchantQueue                   Time                 4.85 minutes      0.52 minutes      2.56 minutes      7.02 minutes     25.20 minutes


.. _bank-3-tutorial-label:

Bank Model Round 3: Adding Assignment Flexibility
=================================================

The `bank2` model demonstrates how we can model some fairly complex behavior by using
resource pools and queue prioritization while also leveraging the Python class
hierarchy for simulation objects. But there is one obvious gap in our teller 
assignment logic: what happens if there are waiting merchant customers, available
regular tellers, and no regular customers in the queue? Perhaps in that case, we
would like regular tellers to handle merchant customers. Our next model 
(:doc:`bank3.py <bank3_py>`) 
will address that via a subclassed Resource Pool that implements a custom resource 
assignment algorithm.

A Little Bit of Background...
------------------------------

Before we dive into the code for our next bank model, it's worth looking under the covers
to see what happens when an entity/process request a resource via :meth:`acquire` or 
:meth:`acquire_from`.

Every resource in a Simprovise model is managed by a resource assignment agent. 
When a process calls :meth:`acquire` it is actually sending a resource request 
message to the assignment agent managing the call's resource argument. In this case, 
the :meth:`~modeling.resource.acquire_from`
call is sending that request to the resource pool, which is the assignment agent for
all of the resources in the pool. At this point, the calling process is suspended
until it receives a response from the assignment agent. It is the assignment agent's 
job to fulfill these requests by assigning a resource or resources to that request.
Of course the requested resource(s) may not be available, or there may be other 
requests asking for the same resource(s). So incoming resource requests are placed 
in a queue, which triggers a call to a key resource assignment agent method, 
:meth:`process_queued_requests`.

:meth:`process_queued_requests` can assign available resources to zero or more requests 
in the queue; when it does so, it notifies the process(s) via a resource assignment
message and removes those request message(s) from the queue. When the process
receives the assignment message, it is "woken up" and the process continues.

:meth:`process_queued_requests` is triggered by any event that might create the conditions
that allow requests in the queue to be fulfilled by a resource assignment, including
(but not limited to) new resource requests and resource releases. As such it 
is the key method implementing resource assignment logic. The built-in
:class:`SimResourcePool` has it's own, fairly sophisticated implementation of 
:meth:`process_queued_requests`, but this may not work for all models. When this is the
case, we can create our own model-specific subclass of :class:`SimResourcePool` and
overload :meth:`process_queued_requests` with model-specific code.

That is what we are going to do here.

Building the Model
-------------------

As noted above, we are going to create a new subclass of :class:`SimResourcePool`, 
:class:`TellerPool`. Before we look the code for that class, a few details:

* :meth:`process_queued_requests` takes one parameter, throughRequest. The only
  time this parameter has a value other than `None` is when this method
  is called in response to a resource acquire timeout (and even then, the
  parameter exists to handle a corner case). Since this model does not
  yet include resource acquire timeouts, we can ignore throughRequest for
  now.
* :class:`SimResourcePool` (and all resource assignment agent classes) has a 
  :meth:`queued_resource_requests` method that returns all resource requests.
  If a priority function has been assigned to the agent (as we did in bank2),
  the requests are returned in priority order (and FIFO within priority);
  otherwise they are returned in FIFO order.
* All resource requests are objects of class 
  :class:`.resource.SimResourceRequest`. This class provides property
  accessors for the request parameters and an assign_resource() method
  that does all of the work of fulfilling a request - sending the 
  assignment back to the requesting process and removing the request
  from the queue.
* The :class:`SimResourcePool` base class provides an 
  :meth:`available_resources` method which takes a resource class argument;
  it returns all available resources in the pool of the specified class.
  (including subclasses of the specified class)
  
TellerPool implements a couple of internal helper methods::

    def _queued_regular_requests(self):
        """
        Convenience method that returns all queued resource
        requests from regular customers
        """
        return [request for request in self.queued_resource_requests()
                if isinstance(request.entity, RegularCustomer)]
        
    def _queued_merchant_requests(self):
        """
        Convenience method that returns all queued resource
        requests from merchant customers
        """
        return [request for request in self.queued_resource_requests()
                if isinstance(request.entity, MerchantCustomer)]  

These methods return the subset of requests made by regular and 
merchant customers, respectively.

process_queued_requests() then does all of the work (for brevity's sake,
the docstring is omitted)::

    def process_queued_requests(self, throughRequest=None):
        # Assign merchant customers to merchant tellers until we run
        # out of one or the other
        available_tellers = self.available_resources(MerchantTeller)
        for request in self._queued_merchant_requests():
            if available_tellers:
                teller = available_tellers.pop()
                request.assign_resource(teller)
            else:
                break
          
        # Do the same for regular customers and tellers
        available_tellers = self.available_resources(RegularTeller)
        for request in self._queued_regular_requests():
            if available_tellers:
                teller = available_tellers.pop()
                request.assign_resource(teller)
            else:
                break
            
        # If there are unassigned tellers of any type left over and any  
        # customers remaining, assign customers to any type of teller
        available_tellers = self.available_resources(Teller)
        for request in self.queued_resource_requests():
            if available_tellers:
                teller = available_tellers.pop()
                request.assign_resource(teller)
            else:
                break
                       
The rest of the model is essentially the same as bank2; the only difference
is that both merchant and regular processes request generic :class:`Teller`
resources, not :class:`MerchantTeller` or :class:`RegularTeller`. Below is
the :class:`MerchantTransaction` :meth:`run`::

    def run(self):
        bank = SimModel.model().get_static_object("Bank")
        sink = SimModel.model().get_static_object("Sink")
        service_time = next(MerchantTransaction.st_generator)
        customer = self.entity
        customer.move_to(bank.merchant_queue)
        with self.acquire_from(bank.teller_pool, Teller) as teller_assignment:
            teller = teller_assignment.resource
            customer.move_to(bank.teller_counter)
            self.wait_for(service_time)
        customer.move_to(sink)

This code was also modified to demonstrate another feature - the ability
to obtain references to static objects (locations, queues, resources, sources
and sinks) via the :class:`SimModel` registry via :meth:`get_static_object`
using an Element ID. (The bank and sink are top-level objects; the bank's
teller counter location could be accessed via element ID 'Bank.TellerCounter')

.. _bank-4-tutorial-label:

Bank Model Round 4: Abandoning the Queue and Adding Custom Data Collection
==========================================================================

The next version of our bank model, :doc:`bank4.py <bank4_py>`, will add some 
behavior to our regular customers; if the queue is taking to long, they will 
bail out of the line and leave the bank. This model will also demonstrate 
how to do additional data collection through custom 
:ref:`simulation-datasets-label`.

Custom Datasets
---------------

We will add three custom datasets to this model; one 
:ref:`time-weighted <simulation-time-weighted-datasets-label>` and the other
:ref:`unweighted <simulation-unweighted-datasets-label>`.

The **time-weighted** dataset will track the total customers - both
regular and merchant - in line at the bank. (We currently have separate
queues for each customer type, and track the number of customers by queue.)
As with most time-weighted data, we will implement this through a
:ref:`counter. <counters-datacollectors-label>`, defined in the ``__init__()``
of class ``Bank``::

    self.waiting_customer_counter = SimCounter(self, 'WaitingCustomers')
    
This code creates a counter and a time-weighted dataset named "WaitingCustomers"
that belongs to the ``Bank`` object (which is a 
:ref:`simulation element. <simulation-elements-label>`). 
The dataset will track each counter value and the length of simulated time
that it remains at that value. As we will see below, this counter will be
incremented and decremented every time a customer enters and leaves one of
the bank's queues.

.. note::
  While this model illustrates the use of a 
  :class:`counter <simprovise.modeling.counter.SimCounter>`, we could
  also collect these same data by placing both queue objects into a 
  :class:`~simprovise.modeling.location.SimLocation`.
  
The ``RegularTransaction`` class already collects process times through its
built-in ``ProcessTime`` dataset, but this dataset does not distinguish between
customers who complete their transactions and those that bail out because
the wait was too long. We will address that by creating two new 
unweighted datasets using class
:class:`~simprovise.core.datacollector.SimUnweightedDataCollector`::

    cpt_datacollector = SimUnweightedDataCollector(RegularTransaction,
                                                   "CompletedProcessTime",
                                                   simtime.SimTime)      
    quit_pt_datacollector = SimUnweightedDataCollector(RegularTransaction,
                                                       "QuittedProcessTime",
                                                       simtime.SimTime)      

These data collector objects each create a dataset (named 
"CompletedProcessTime" and "QuittedProcessTime", respectively) which belong
to the ``RegularTransaction`` :ref:`class element <class_elements-label>`.

In the next section, we will see the code that adds values to these datasets.

Bailing Out of the Queue
------------------------

In this model, regular customers bail out of the queue if they have been
waiting for "too long", which we will define as sometime between five and
thirty minutes. This "quit time" is determined by sampling from a 
:meth:`simprovise.core.simrandom.Distribution.uniform` distribution
defined as ``RegularTransaction`` class attributes::

    min_quit_time =  SimTime(5, tu.MINUTES)
    max_quit_time =  SimTime(30, tu.MINUTES)
    quit_time_generator = SimDistribution.uniform(min_quit_time, max_quit_time)

The RegularTransaction run() method  then obtains a quit_time from this
distribution and uses it as a timeout on the
:meth:`~simprovise.modeling.process.SimProcess.acquire_from` method.
If that call times out before a resource is assigned to the process,
a :class:`~simprovise.core.simexception.SimTimeOutException` is raised,
which the run() method must handle::

    quit_time = next(RegularTransaction.quit_time_generator)
    try:
        teller_assignment = self.acquire_from(bank.teller_pool, Teller,
                                              timeout=quit_time)
    except SimTimeOutException:
        # Abandon the queue and the rest of the process
        customer.move_to(sink)
        return
     
Here is the complete implementation of the run() method, where we can also
see how our custom dataset values are collected via the counter and
data collector objects::

    def run(self):
        bank = SimModel.model().get_static_object("Bank")
        sink = SimModel.model().get_static_object("Sink")
        service_time = next(RegularTransaction.st_generator)
        customer = self.entity
        startTime = SimClock.now()
        bank.waiting_customer_counter.increment()
        customer.move_to(bank.regular_queue)
        quit_time = next(RegularTransaction.quit_time_generator)
        try:
            teller_assignment = self.acquire_from(bank.teller_pool, Teller,
                                                  timeout=quit_time)
        except SimTimeOutException:
            # Abandon the queue and the rest of the process
            customer.move_to(sink)
            quit_pt_datacollector.add_value(SimClock.now() - startTime)
            bank.waiting_customer_counter.decrement()
            return
            
        with teller_assignment:
            teller = teller_assignment.resource
            bank.waiting_customer_counter.decrement()
            customer.move_to(bank.teller_counter)
            self.wait_for(service_time)
            
        customer.move_to(sink)
        cpt_datacollector.add_value(SimClock.now() - startTime)

Below is a portion of the standard summary output report, including our
custom datasets (CompletedProcessTime, QuittedProcessTime and WaitingCustomers)::

    ---------------------------------------------------------------------------------------------------------------------------------------------------------------
                                                                  Results: 1 Replication, 10 Batches                                                               
    Element ID                           Dataset              Sample Size    Sample Mean     25th Percentile       Median        75th Percentile         Max       
    ---------------------------------------------------------------------------------------------------------------------------------------------------------------
    __main__.RegularTransaction          In-Process             1188.00      4.81              1.90              4.10              7.00             17.60        
    __main__.RegularTransaction          Entries                 594.60    594.60            594.60            594.60            594.60            594.60        
    __main__.RegularTransaction          Process-Time            593.40      4.87 minutes      2.09 minutes      4.30 minutes      6.94 minutes     18.08 minutes
    __main__.RegularTransaction          CompletedProcessTime    577.70      4.81 minutes      2.03 minutes      4.19 minutes      6.89 minutes     18.08 minutes
    __main__.RegularTransaction          QuittedProcessTime       15.70      7.21 minutes      5.81 minutes      6.66 minutes      8.17 minutes     11.31 minutes
    Bank                                 Population             1493.40      6.66              2.80              5.50              9.60             22.30        
    Bank                                 Entries                 746.30    746.30            746.30            746.30            746.30            746.30        
    Bank                                 Time                    746.10      5.35 minutes      2.16 minutes      4.41 minutes      7.35 minutes     26.79 minutes
    Bank                                 WaitingCustomers       1314.60      4.02              0.20              2.50              6.60             19.30        
    Bank.RegularQueue                    Size                   1049.00      2.92              0.10              1.80              4.80             15.50        
    Bank.RegularQueue                    Entries                 593.60    593.60            593.60            593.60            593.60            593.60        
    Bank.RegularQueue                    Time                    593.40      2.96 minutes      0.29 minutes      2.12 minutes      4.81 minutes     13.43 minutes



.. _bank-5-tutorial-label:

Bank Model Round 5: Adding Breaks and Custom Down Time Algorithms
=================================================================

The last versions of our bank model will implement scheduled breaks, or
down time, for our teller resources. Creating and implementing a break
schedule is relatively easy; the more challenging problem: how to handle
customers that the teller is serving when they are supposed to go on break.
We will implement several approaches (some more realistic than others)
that demonstrate different Simprovise capabilities in this area.

.. _bank-5-step-a-tutorial-label:

Round 5, Step (a): Refactoring Bank Model 3
-------------------------------------------

We're going to base this model on the :ref:`third <bank-3-tutorial-label>`
(:doc:`bank3.py <bank3_py>`)
bank tutorial model, skipping the abandonment feature implemented in `bank4`.
In this first step, we'll refactor :doc:`bank3.py <bank3_py>` in order to:

* Reduce duplicated code
* Demonstrate the creation of model-specific modules
* Split the multi-capacity RegularTeller resource into separate resources
  (each of capacity 1), which will be needed to implement downtime in
  subsequent model versions in this tutorial. The model with separate teller
  resources should behave exactly like it's multi-capacity sibling.

We'll start this iteration by creating :doc:`bank5.py <bank5_py>`, which will 
be a module defining most of the classes used by our model that we are already
familiar with:

* ``Customer``, ``RegularCustomer`` and ``MerchantCustomer``
* ``Teller``, ``RegularTeller`` and ``MerchantTeller``
* ``TellerPool``
* ``Bank``
* ``BankTransaction``

All of the ``Customer`` and ``Teller`` classes, as well as ``TellerPool``, are 
copied verbatim from ``bank3.py``.

The ``Bank`` class is modified, however::

              
    class Bank(SimLocation):
        """
        A SimLocation that encapsulates all of the objects (resources,
        queues and locations) that comprise a bank.
        """
        __slots__ = ('teller_counter', 'regular_teller', 'merchant_teller',
                     'teller_pool', 'regular_queue', 'merchant_queue')
        
        def __init__(self, name="Bank", nRegularTellers=4, nMerchantTellers=1):
            super().__init__(name)
            self.teller_counter = SimLocation("TellerCounter", self)
            
            self.regular_tellers = self._make_tellers(RegularTeller,
                                                      nRegularTellers)
            self.merchant_tellers = self._make_tellers(MerchantTeller,
                                                       nMerchantTellers)
                     
            self.teller_pool = TellerPool(*self.regular_tellers, 
                                             *self.merchant_tellers)
            
            self.regular_queue = SimQueue("RegularQueue", self)
            self.merchant_queue = SimQueue("MerchantQueue", self)
            
        def _make_tellers(self, tellerClass, ntellers):
            """
            Create *n* teller resource objects of a passed class, where *n*
            is passed as parameter ``ntellers``.
                """
            id_range = range(1, ntellers+1)
            tellerid = tellerClass.__name__ + '{0}'
            location = self.teller_counter
            return [tellerClass(tellerid.format(i), location) for i in id_range]
    
        @property
        def available_regular_tellers(self):
            """
            A property that returns the number of available regular tellers.
            Used as a simtrace column (which must be a property)
            """
            return self.teller_pool.available(RegularTeller)
        
        @property
        def available_merchant_tellers(self):
            """
            A property that returns the number of available merchant tellers.
            Used as a simtrace column (which must be a property of a simulation
            element)
            """
            return self.teller_pool.available(MerchantTeller)

We are now creating individual regular and merchant tellers, each with 
capacity 1, via method :meth:`_make_tellers`, which returns them as a list.
(The lists are assigned to Bank instance attributes ``regular_tellers`` and
``merchant_tellers``, respectively.)

We've also added a couple of properties, primarily for the purpose of
enabling simtrace columns equivalent to the ``available`` property used in prior
versions of the model. (simtrace columns can reference only element properties,
not functions.)

Finally, we've re-factored :class:`BankTransaction` to capture the code
basically common to both of its subclasses::

    class BankTransaction(SimProcess):
        """
        Base class for simulated bank transaction classes
        """
        @classmethod
        def get_service_time(cls):
            """
            Return the next sample from the BankTransaction subclass
            service time distribution
            """
            return next(cls.servicetime_generator)
        
        def __init__(self, queue):
            super().__init__()
            self.queue = queue
            
        def run(self):
            bank = SimModel.model().get_static_object("Bank")
            sink = SimModel.model().get_static_object("Sink")
            service_time = self.get_service_time()
            customer = self.entity
            customer.move_to(self.queue)
            with self.acquire_from(bank.teller_pool, Teller) as teller_assignment:
                teller = teller_assignment.resource
                customer.move_to(bank.teller_counter)
                self.wait_for(service_time)
            customer.move_to(sink)        

The specific queue to enter after customer creation is specified via
class initializer (and as we will see, provided by the subclass). The
service times are provided by a class attribute (``servicetime_generator``)
defined for each subclass.

The main model script is ``bank5a.py``; it imports ``bank5`` and defines the  
rest of the model. The changes from bank3 are the BankTransaction subclasses 
and the "available" simtrace column definitions::

    class RegularTransaction(BankTransaction):
        """
        Represents a "regular" transaction by a "regular" (non-merchant)
        customer.
        """
        mean_interarrival_time = SimTime(1, tu.MINUTES)
        mean_service_time = SimTime(2, tu.MINUTES) 
        servicetime_generator = SimDistribution.exponential(mean_service_time)
        
        def __init__(self):
            super().__init__(bank.regular_queue)
        
    
    class MerchantTransaction(BankTransaction):
        """
        Represents a merchant transaction (by a merchant customer)
        """
        mean_interarrival_time = SimTime(4, tu.MINUTES)
        mean_service_time = SimTime(3, tu.MINUTES)
        servicetime_generator = SimDistribution.exponential(mean_service_time)
    
        def __init__(self):
            super().__init__(bank.merchant_queue)
    
    
    simtrace.add_trace_column(bank, 'available_regular_tellers',
                              'RegularTellers: available')
    simtrace.add_trace_column(bank, 'available_merchant_tellers',
                              'MerchantTellers: available')



.. _bank-5-step-b-tutorial-label:

Round 5, Step (b): Add a Simple Teller Break Schedule
-----------------------------------------------------

For the next iteration, :doc:`bank5b.py <bank5b_py>`,
we will add two scheduled fifteen minute breaks for 
each of the two regular tellers, using classes
:class:`~simprovise.modeling.downtime.DowntimeSchedule` and
:class:`~simprovise.modeling.downtime.SimScheduledDowntimeAgent`.
Two 
:class:`downtime agents, <simprovise.modeling.downtime.SimDowntimeAgent>`
one per regular teller, are responsible for taking
down tellers for their breaks and bringing them back up when the breaks 
conclude.

The workday will be defined as nine hours long. The first regular teller
will get breaks starting two hours and six hours into that day; the 
second teller will be scheduled for breaks immediately thereafter (2:15
and 6:15 into the day).

The schedules and downtime agents are defined in a new **Bank** subclass::

    class Bank5b(Bank):
        """
        A subclass of Bank that adds scheduled downtime agents for the
        regular tellers.
        """
        __slots__ = ('downtime_agents')
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            
            # Create downtime agents for the regular tellers
            self.downtime_agents = self.make_downtime_agents()
                            
        def make_downtime_agents(self):
            """
            Create two downtime schedules, use them to create two scheduled
            downtime agents, and assign each of those agents to a regular teller
            resource. (We'll assume at least two regular tellers.)
            """
            downtime_schedules = self.make_schedules()
            tellers = self.regular_tellers
            
            return [SimScheduledDowntimeAgent(tellers[i], sched)
                    for i, sched in enumerate(downtime_schedules)]
        
        def make_schedules(self):
            """
            Create a two downtime schedules (A and B), each with two 15 minute
            breaks, one after the other.
            """
            day_length = SimTime(9, tu.HOURS)
            break_length = SimTime(15, tu.MINUTES)
            
            breakA1 = (SimTime(2, tu.HOURS), break_length)
            breakA2 = (SimTime(6, tu.HOURS), break_length)
            breakB1 = (SimTime(2.25, tu.HOURS), break_length)
            breakB2 = (SimTime(6.25, tu.HOURS), break_length)
            
            breaksA = [breakA1, breakA2]
            breaksB = [breakB1, breakB2]
            
            scheduleA = DowntimeSchedule(day_length, breaksA)
            scheduleB = DowntimeSchedule(day_length, breaksB)
            
            return scheduleA, scheduleB

We will also create a new **BankTransaction** subclass::

    class BankTransaction5b(BankTransaction):
        """
        BankTransaction subclass that adds extend_through_downtime
        for teller service wait_for() call.
        """
        def run(self):
            service_time = self.get_service_time()
            customer = self.entity
            customer.move_to(self.queue)
            with self.acquire_from(bank.teller_pool, Teller) as teller_assignment:
                #teller = teller_assignment.resource
                customer.move_to(bank.teller_counter)
                # In case teller goes down during wait, enxtend wait for
                # the length of the down time.
                self.wait_for(service_time, extend_through_downtime=True)
            customer.move_to(sink)        

Whenever a model implements resource downtime, the model's processes also 
need to be prepared to handle the situation where a resource goes down while
the process is holding it. When that happens, an exception is raised, which the
process must handle one way or another.

This subclass handles it through the ``extend_through_downtime`` parameter of 
the :meth:`~simprovise.modeling.process.SimProcess.wait_for` method; when
this parameter is set to ``True``, ``wait_for()`` handles the exception under
the covers and extends the wait period by the length of the down time.

The rest of our model looks essentially the same as :doc:`bank5a.py <bank5a_py>`;
the ``RegularTransaction`` and 
``MerchantTransaction`` classes inherit from ``BankTransaction5b``, but are
otherwise unchanged. And the bank is of class ``Bank5b`` (as opposed to 
``Bank``).

The output of a simulation run; notice that the sample mean downtime
is 6% for the two regular tellers::

    -------------------------------------------------------------------------------------------------------------------------------------------------------------
                                                                 Results: 1 Replication, 10 Batches                                                              
    Element ID                              Dataset         Sample Size    Sample Mean     25th Percentile       Median        75th Percentile         Max       
    -------------------------------------------------------------------------------------------------------------------------------------------------------------
    simprovise.demos.bank5.BankTransaction  In-Process           1.00      0.00              0.00              0.00              0.00              0.00        
    simprovise.demos.bank5.BankTransaction  Entries              1.00      1.00              1.00              1.00              1.00              1.00        
    simprovise.demos.bank5.BankTransaction  Process-Time         0.00       nan               nan               nan               nan               nan        
    __main__.BankTransaction5b              In-Process           1.00      0.00              0.00              0.00              0.00              0.00        
    __main__.BankTransaction5b              Entries              1.00      1.00              1.00              1.00              1.00              1.00        
    __main__.BankTransaction5b              Process-Time         0.00       nan               nan               nan               nan               nan        
    __main__.RegularTransaction             In-Process        1234.50     18.80             11.70             17.80             25.70             44.10        
    __main__.RegularTransaction             Entries            618.90    618.90            618.90            618.90            618.90            618.90        
    __main__.RegularTransaction             Process-Time       615.60     18.09 minutes     11.05 minutes     17.08 minutes     24.09 minutes     45.68 minutes
    __main__.MerchantTransaction            In-Process         298.30      2.53              0.80              1.90              4.00             10.20        
    __main__.MerchantTransaction            Entries            149.60    149.60            149.60            149.60            149.60            149.60        
    __main__.MerchantTransaction            Process-Time       148.70     10.17 minutes      4.08 minutes      8.17 minutes     14.20 minutes     33.39 minutes
    simprovise.modeling.entity.SimEntity    Work-In-Process      1.00      0.00              0.00              0.00              0.00              0.00        
    simprovise.modeling.entity.SimEntity    Process-Time         0.00       nan               nan               nan               nan               nan        
    simprovise.demos.bank5.Customer         Work-In-Process      1.00      0.00              0.00              0.00              0.00              0.00        
    simprovise.demos.bank5.Customer         Process-Time         0.00       nan               nan               nan               nan               nan        
    simprovise.demos.bank5.RegularCustomer  Work-In-Process   1234.50     18.80             11.70             17.80             25.70             44.10        
    simprovise.demos.bank5.RegularCustomer  Process-Time       615.60     18.09 minutes     11.05 minutes     17.08 minutes     24.09 minutes     45.68 minutes
    simprovise.demos.bank5.MerchantCustomer Work-In-Process    298.30      2.53              0.80              1.90              4.00             10.20        
    simprovise.demos.bank5.MerchantCustomer Process-Time       148.70     10.17 minutes      4.08 minutes      8.17 minutes     14.20 minutes     33.39 minutes
    Source                                  Population         767.50      0.00              0.00              0.00              0.00              0.00        
    Source                                  Entries            766.50    766.50            766.50            766.50            766.50            766.50        
    Source                                  Time               766.50      0.00 minutes      0.00 minutes      0.00 minutes      0.00 minutes      0.00 minutes
    Bank                                    Population        1531.80     21.34             13.60             20.50             28.80             47.90        
    Bank                                    Entries            766.50    766.50            766.50            766.50            766.50            766.50        
    Bank                                    Time               764.30     16.58 minutes      8.61 minutes     15.80 minutes     22.92 minutes     45.68 minutes
    Bank.TellerCounter                      Population         830.60      2.86              2.90              3.00              3.00              3.00        
    Bank.TellerCounter                      Entries            764.30    764.30            764.30            764.30            764.30            764.30        
    Bank.TellerCounter                      Time               764.30      2.25 minutes      0.61 minutes      1.49 minutes      3.04 minutes     21.02 minutes
    Bank.TellerCounter.RegularTeller1       ProcessTime        274.30      2.07 minutes      0.58 minutes      1.38 minutes      2.69 minutes     20.63 minutes
    Bank.TellerCounter.RegularTeller1       Utilization        295.30      0.95              1.00              1.00              1.00              1.00        
    Bank.TellerCounter.RegularTeller1       DownTime             5.60      0.06              0.00              0.00              0.00              1.00        
    Bank.TellerCounter.RegularTeller2       ProcessTime        275.10      2.10 minutes      0.56 minutes      1.40 minutes      2.83 minutes     19.11 minutes
    Bank.TellerCounter.RegularTeller2       Utilization        301.90      0.96              1.00              1.00              1.00              1.00        
    Bank.TellerCounter.RegularTeller2       DownTime             5.60      0.06              0.00              0.00              0.00              1.00        
    Bank.TellerCounter.MerchantTeller1      ProcessTime        214.90      2.68 minutes      0.76 minutes      1.84 minutes      3.78 minutes     16.00 minutes
    Bank.TellerCounter.MerchantTeller1      Utilization        235.40      0.95              1.00              1.00              1.00              1.00        
    Bank.TellerCounter.MerchantTeller1      DownTime             1.00      0.00              0.00              0.00              0.00              0.00        
    Bank.RegularQueue                       Size              1183.80     16.68              9.60             15.70             23.60             41.80        
    Bank.RegularQueue                       Entries            617.90    617.90            617.90            617.90            617.90            617.90        
    Bank.RegularQueue                       Time               615.60     16.02 minutes      9.08 minutes     14.96 minutes     21.88 minutes     39.58 minutes
    Bank.MerchantQueue                      Size               283.90      1.79              0.10              1.10              3.00              9.20        
    Bank.MerchantQueue                      Entries            148.60    148.60            148.60            148.60            148.60            148.60        
    Bank.MerchantQueue                      Time               148.70      7.20 minutes      1.69 minutes      4.75 minutes     10.71 minutes     28.37 minutes



.. _bank-5-step-c-tutorial-label:

Round 5, Step (c): Finish the Job Before Going on Break
-------------------------------------------------------

Using the ``extend_through_downtime`` parameter is the simplest way to handle
down time, and it makes sense in some scenarios, e.g. when entities are 
orders in a manufacturing shop. Our bank is probably not one of those
situations; expecting customers to wait while their teller is on break is,
to be gentle, less than realistic.

We will attempt to address that shortcoming in our next iteration,
:doc:`bank5c.py <bank5c_py>`. In this model, if a regular teller is serving
a customer when it is time to go on break, they will complete that customer's 
transaction before starting their break.

In this model, completion of service for a customer delays a break, but does
not shorten it; if the teller is scheduled for a break at hour 6 but takes three 
extra minutes to complete a customer transaction, that teller will not
return to work (be brought up) until 6:18 - which overlaps with the 
second teller's break.

In order to eliminate the possibility of both tellers being on break at the
same time, this model will also delay the start of the other teller's break
when needed to avoid that scenario.

To do this, we will create subclasses of ``Bank`` (``Bank5c``) and 
:class:`~simprovise.modeling.downtime.SimScheduledDowntimeAgent`,
(``TellerDowntimeAgent``).

``Bank5c`` looks very much like ``Bank5b``, but with some additional code at the
end of the ``__init__()`` method::

    # Have each downtime agent subscribe to RSRC_UP messages from all of
    # the other downtime agents.
    for agent in self.downtime_agents:
        otherAgts = [agt for agt in self.downtime_agents if agt is not agent]
        for otherAgt in otherAgts:
            otherAgt.add_subscriber(agent, SimMsgType.RSRC_UP)

When a resource comes back up, the           
:class:`downtime agents <simprovise.modeling.downtime.SimScheduledDowntimeAgent>`
responsible notifies the other agents associated with that resource -
its resource assignment agent and its other downtime agents (if any)
by sending them a ``RSRC_UP`` message. 

In this case, we use the :class:`~simprovise.modeling.agent.SimAgent`
subscription service to ensure that **all** teller downtime agents are 
notified whenever *any* teller resource comes back up. 
Class SimDowntimeAgent provides a stub method,
:meth:`~simprovise.modeling.downtime.SimDowntimeAgent._handle_resource_up`,
that handles this message type as a no-op. Our ``TellerDowntimeAgent`` will
overrride it, as described below.

The ``TellerDowntimeAgent`` subclass takes advantage of:

* The resource's
  :attr:`~simprovise.modeling.resource.SimResource.going_down` property,
  which indicates that while the resource is still up and working, it is about
  to go down and should not be assigned new work, and

* The downtime agent's 
  :meth:`~simprovise.modeling.downtime.SimDownTimeAgent._set_resource_going_down`
  method, which set's that property to ``True`` on the resource it is assigned 
  to. This method is called by an override implementation of
   
* The ``RSRC_UP`` subscription notifications when a different teller comes back
  up, by implementing 
  :meth:`~simprovise.modeling.downtime.SimDowntimeAgent._handle_resource_up`,
 
  
The full implementation of this subclass::

    class TellerDowntimeAgent(SimScheduledDowntimeAgent):
        """
        Implements custom algorithms/behavior for regular teller scheduled downtime.
        The Bank object that creates these agents subscribes them to RSRC_UP
        messages from the teller pool, which is necessary to fully implement the
        behavior as described below.
        
        When a scheduled break is initiated for the agent's regular teller resource
        (via :meth:`start_resource_takedown`), this agent:
        
        - Checks to see if any of the other regular tellers are on break or in
          the "going-down" state; if so, the teller remains in the fully-up state.
          
        - If the other tellers are fully operating, this agent's teller then
          checks to see if it is idle (not serving a customer). If so, it goes
          down/on break immediately via :meth:`_takedown_resource`. If it is
          in-use/serving a customer, it enters the ``going-down`` state via
          :meth:`_set_resource_going_down`; in that state, it will not be
          available to new customer assignments but will stay up until released
          by the current customer (as implemented by the base SimDowntimeAgent
          class).
          
        - The agent's RSRC_UP handler, through subscription to the other teller
          downtime agents, should receive a message every time a teller comes
          back up (off break). That handler refires :meth:`start_resource_takedown`,
          which will re-run the algorithm.
     
        """
        __slots__ = ('start_delayed', 'bank')
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.start_delayed = False
            self.bank = SimModel.model().get_static_object("Bank")
                    
        def start_resource_takedown(self):
            """
            Time for a scheduled break. (Or time to try and take a break again.)
            
            - If any of the other tellers are down or going down, delay the
              break until they all are back up and servicing new customers.
              
            - Otherwise, take the teller down if it is idle, or set it to
              going-down (not taking new customers) if it is not idle.
              
            """
            self.start_delayed = False
            if self._tellers_down_or_goingdown(bank.regular_tellers):
                self.start_delayed = True
            elif self.resource.in_use:
                self._set_resource_going_down()
            else:
                self._takedown_resource()
            
        def _tellers_down_or_goingdown(self, tellers):
            """
            Returns the number of tellers that are down or going down.
            """
            return len([t for t in tellers if t.down or t.going_down])
            
        def _handle_resource_up(self, msg):
            """
            One of the teller resources has come back up/off break. (We should be
            subscribing to all tellers that can go down.) If we delayed
            starting a break due to another teller already on break,
            we'll use this event to trigger another attempt.
            """
            if self.start_delayed:
                # Try again
                self.start_resource_takedown()
            
            # Return ``True`` to indicate the message was handled
            return True
        
Some key points:

* The base class implementation of
  :meth:`~simprovise.modeling.downtime.SimDowntimeAgent.start_resource_takedown`
  simply takes down the resource. The override implementation in this subclass
  delays any action if the other teller is down or going down (and sets a
  flag to that effect); otherwise, it either:
  
  - Sets it's teller to the going-down state if it is in use, or
  - Takes the teller down if it is not in use

* If takedown action was delayed, 
  :meth:`~simprovise.modeling.downtime.SimDowntimeAgent._handle_resource_up`
  reacts to a teller coming back up by essentially trying again to take
  its own teller down.
  
To see this in action, let's look at some of the trace from the time that the
first regular teller is scheduled for a break - at 120 minutes on the 
simulated clock::

    117.05 RegularCustomer 142    Release   RegularTeller1                                                             
    117.05 RegularCustomer 142    Move-to   Sink                                                                       
    117.05 RegularCustomer 144    Acquired  RegularTeller1                                                             
    117.05 RegularCustomer 144    Move-to   Bank.TellerCounter                                                         

    <lots of skipped events>

    124.27 RegularCustomer 146    Release   RegularTeller2                                                             
    124.27 RegularCustomer 146    Move-to   Sink                                                                       
    124.27 RegularCustomer 147    Acquired  RegularTeller2                                                             
    124.27 RegularCustomer 147    Move-to   Bank.TellerCounter                                                         
    124.75 RegularCustomer 144    Release   RegularTeller1                                                             
    124.75 RegularTeller1         Down                                                                                 
    124.75 RegularCustomer 144    Move-to   Sink                                                                       
 
As we can see, RegularCustomer 144 acquired teller 1 at time 117.05, and
did not release it until well into the scheduled break at time 124.75.
RegularTeller1 went down (on break) immediately thereafter.

::

    138.94 RegularCustomer 161    Release   RegularTeller2                                                             
    138.94 RegularCustomer 161    Move-to   Sink                                                                       
    138.94 RegularCustomer 162    Acquired  RegularTeller2                                                             
    138.94 RegularCustomer 162    Move-to   Bank.TellerCounter                                                         
    139.02 RegularCustomer 178    Move-to   Bank.RegularQueue                                                          
    139.02 RegularCustomer 178    Acquiring Teller                                                                     
    139.75 RegularTeller1         Up                                                                                   
    139.75 RegularCustomer 163    Acquired  RegularTeller1                                                             
    139.75 RegularCustomer 163    Move-to   Bank.TellerCounter                                                         
    140.13 RegularCustomer 179    Move-to   Bank.RegularQueue                                                          
    140.13 RegularCustomer 179    Acquiring Teller                                                                     
    140.28 RegularCustomer 163    Release   RegularTeller1                                                             
    140.28 RegularCustomer 163    Move-to   Sink                                                                       
    140.28 RegularCustomer 164    Acquired  RegularTeller1                                                             
    140.28 RegularCustomer 164    Move-to   Bank.TellerCounter                                                         
    140.31 RegularCustomer 180    Move-to   Bank.RegularQueue                                                          
    140.31 RegularCustomer 180    Acquiring Teller                                                                     
    140.42 RegularCustomer 164    Release   RegularTeller1                                                             
    140.42 RegularCustomer 164    Move-to   Sink                                                                       
    140.42 RegularCustomer 166    Acquired  RegularTeller1                                                             
    140.42 RegularCustomer 166    Move-to   Bank.TellerCounter                                                         
    140.61 RegularCustomer 162    Release   RegularTeller2                                                             
    140.61 RegularTeller2         Down                                                                                 

RegularTeller1 comes back up, off break, 15 minutes later, at time 139.75.
RegularTeller2 has postponed going on break (or even preparing to go down),
and had started serving a new customer (162) just under a minute before.
RegularTeller2 does not start its break until customer 162 releases it at 
time 140.61

 
.. _bank-5-step-d-tutorial-label:

Round 5, Step (d): But Don't Wait Too Long Before Going on Break
----------------------------------------------------------------

The downtime algorithm implemented in the :doc:`bank5c.py <bank5c_py>`
is probably pretty reasonable, but what if a teller is servicing an
especially long transaction when it's time for break?
In our last iteration, :doc:`bank5d.py <bank5d_py>`, we will make sure
that the teller waits only so long before starting a break.

This strategy has two components:

* Make sure that the teller goes down no more than a specified amount
  of time (we're choosing four minutes) after the scheduled start of their
  break
* If the customer they are serving has **not** completed their transaction
  at that time, send them to the next available teller to finish up.
  
We can implement that first component by using the optional ``timeout`` parameter
of the
:meth:`~simprovise.modeling.downtime.SimDownTimeAgent._set_resource_going_down`
method. Our TellerDowntimeAgent class does so with a slight modification to
it's ``start_resource_takedown()``::

    def start_resource_takedown(self):
        """
        Time for a scheduled break. (Or time to try and take a break again.)
        
        - If any of the other tellers are down or going down, delay the
          break until they all are back up and servicing new customers.
          
        - Otherwise, take the teller down if it is idle, or set it to
          going-down (not taking new customers) if it is not idle.
          
        """
        self.start_delayed = False
        if self._tellers_down_or_goingdown(bank.regular_tellers):
            self.start_delayed = True
        elif self.resource.in_use:
            # start going-down with a timeout of four minutes
            self._set_resource_going_down(timeout=SimTime(4, tu.MINUTES))
        else:
            self._takedown_resource()

If the ``timeout`` expires while the teller is still in the ``going-down`` state, 
it is taken down immediately. If a customer is holding that teller at the time,
a :class:`~simprovise.modeling.downtime.SimResourceDownException` is raised,
which the transaction process needs to handle::

    class BankTransaction5d(BankTransaction):
        """
        Modifies BankTransaction.run() in order to handle
        ``SimResourceDownException`` exceptions by reacquiring a teller for
        the remaining service time. Since the wait after that reacquire could
        also run into a teller going down, we have to account for that via
        a recursively called ``wait_for_service()`` internal function.
        """
        def run(self):
            # Priority is two initially, will be set to one if forced to
            # reaquire a teller after the original teller goes down/on break.
            self.priority = 2
            
            def wait_for_service(tm, move=False):
                # wait for the remaining chunk of service time (or all of it,
                # initially). The move to the teller counter is only needed on
                # the initial call to this.
                with self.acquire_from(bank.teller_pool, Teller) as teller_assignment:
                    if move:
                        customer.move_to(bank.teller_counter)
                    start_tm = SimClock.now()
                    try:
                        self.wait_for(tm)
                        return
                    except SimResourceDownException:
                        time_so_far = SimClock.now() - start_tm
                        remaining_time = tm - time_so_far
                        self.priority = 1
                wait_for_service(remaining_time)
                              
            service_time = self.get_service_time()
            customer = self.entity
            customer.move_to(self.queue)
            wait_for_service(service_time, move=True)               
            customer.move_to(sink)        

The transaction ``run()`` implementation handles the resource-down exception by
calculating the remaining time in the transaction, re-aquiring a teller,
and attempting to complete the transaction. (Note that this code should handle
the case where the customer's subsequent teller(s) go down as well.)

Finally, note the ``priority`` attribute that has been added to the transaction
process. It starts at ``2``, but is changed to ``1`` if the transaction is 
interrupted by a teller going down. The ``bank`` object and it's ``teller_pool``
are then modified to use this in a resource request priority function::

    class Bank5d(Bank):
        """
        Modifies Bank5c by defining a priority function to be used by the
        teller pool that will prioritize any customer that gets "kicked out"
        by it's teller if the teller going-down times out.    
        """
        __slots__ = ('downtime_agents')
        
        @staticmethod
        def get_priority(teller_request):
            """
            The priority function to be registered with the teller
            resource pool. It returns the value of the priority attribute
            set by BankTransaction5d processes
            """
            return teller_request.process.priority
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            
            self.teller_pool.request_priority_func = Bank5d.get_priority
            
            # Create downtime agents for the regular tellers
            self.downtime_agents = self.make_downtime_agents()
            
            # Have each downtime agent subscribe to RSRC_UP messages from all of
            # the other downtime agents.
            for agent in self.downtime_agents:
                otherAgts = [agt for agt in self.downtime_agents if agt is not agent]
                for otherAgt in otherAgts:
                    otherAgt.add_subscriber(agent, SimMsgType.RSRC_UP)
     
Using this priority function, any customer left hanging when their teller 
goes on break effectively jumps to the head of the queue for the next
available teller.

Again, let's look at the trace output::

    117.05 RegularCustomer 144    Acquired  RegularTeller1                                                             
    117.05 RegularCustomer 144    Move-to   Bank.TellerCounter   
    
    <lots of skipped events>

    124.00 RegularTeller1         Down                                                                                 
    124.00 RegularCustomer 144    Release   RegularTeller1                                                             
    124.00 RegularCustomer 144    Acquiring Teller                                                                     
    124.01 RegularCustomer 145    Release   RegularTeller2                                                             
    124.01 RegularCustomer 145    Move-to   Sink                                                                       
    124.01 RegularCustomer 144    Acquired  RegularTeller2                                                             

As we can see, RegularCustomer 144 is still holding RegularTeller1 four 
minutes after it was scheduled to go on break. At that point:

* Teller 1 goes down
* Customer 144 releases Teller 1
* Customer 144 requests another teller
* Customer 144 acquires Teller 2 immediately after it is released by
  Customer 145
  
Further Reading
===============

:doc:`modeling_concepts`

:doc:`data_collection`

:doc:`api_reference`