=====================
Tutorial 
=====================

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
bank1.py, found in the installed demos directory. The modeling code
is shown and described below, minus the required import statements. (See the
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
case, we generated a summary report, the left-hand side of which is shown below::

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
    Bank.CustomerQueue                   Population           1.68              0.00              0.00              2.30             16.00        
    Bank.CustomerQueue                   Entries            997.00            997.00            997.00            997.00            997.00        
    Bank.CustomerQueue                   Time                 1.67 minutes      0.00 minutes      0.26 minutes      2.46 minutes     12.69 minutes
    Closing and removing output database...

A few notes/observations:

* The Teller utilization averages 75%, which is what we would expect (4 tellers, 
  mean one customer arrival per minute, mean 3 minutes service time per teller visit)
* The various location Entries represent the number of entities (customers) entering
  per 1,000 minute batch. The mean value of 997 tracks with one arrival per minute
* The most relevant measures are the mean queue time and mean queue population (length)
* The output report has several data display options and can also be saved in
  CSV format; see :doc:`output_database` for details.
* While we typically delete the raw output database after generating report(s), it can
  be saved for further analysis


Running Multiple Replications
-----------------------------

Simprovise also supports running multiple replications of a simulation model, with each 
replication automatically using a different set of random number streams. To do so,
use `Simulation.replicate()`::

    if __name__ == '__main__':
        warmupLength = SimTime(100, tu.MINUTES)
        batchLength = SimTime(1000, tu.MINUTES)
        nbatches = 1
        nruns = 10
        print("Running {0} replications...".format(nruns))            
        with Simulation.replicate(None, warmupLength, batchLength, nbatches,
                                  fromRun=1, toRun=nruns) as simResult:
            simResult.print_summary()

In this case, we are doing ten replications. The maximum number of replications (really, 
the maximum `toRun` value) is configurable via .ini configuration files (See :doc:`configuration`); 
the default maximum is generally 100. The generated summary report::

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
    Bank.CustomerQueue                   Population           1.69              0.00              0.10              2.50             14.10        
    Bank.CustomerQueue                   Entries           1020.80           1020.80           1020.80           1020.80           1020.80        
    Bank.CustomerQueue                   Time                 1.65 minutes      0.00 minutes      0.35 minutes      2.60 minutes     11.65 minutes


.. _bank-1-event-tracing-tutorial-label:
Event Tracing
-------------

Simprovise also provides a event tracing feature, generating a report of the key simulation
events - entity move_to()s, entity acquisition and release of resources, and resource down
time (more on that below).

Tracing can be turned on or off via settings in the [SimTrace] configuration file section.
These settings also provide the ability to:

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
calls to :function:`~simprovise.core.simtrace.add_trace_column`, where each 
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

Our second model, bank2.py, will expand on :ref:`bank1 <bank-1-tutorial-label>` 
by dividing our customers into two types: merchant customers and regular customers,
with separate queues for each. We will also include two corresponding types of 
tellers.

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
  :ref:`resource pool <resource-pool--concept-label>`, which manages customer
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
the concept of a :ref:`resource pool <resource-pool--concept-label>`. 
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
    Bank.RegularQueue                    Population           3.84              0.00              1.30              6.10             22.10        
    Bank.RegularQueue                    Entries            595.80            595.80            595.80            595.80            595.80        
    Bank.RegularQueue                    Time                 3.83 minutes      0.02 minutes      1.74 minutes      6.56 minutes     17.86 minutes
    Bank.MerchantQueue                   Population           0.82              0.00              0.00              1.20              6.10        
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
would like regular tellers to handle merchant customers. Our next model (bank3.py) 
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

The next version of our bank model will add some behavior to our regular
customers; if the queue is taking to long, they will bail out of the line
and leave the bank.

.. _bank-5-tutorial-label:
Bank Model Round 5: Adding Breaks and Custom Down Time Algorithms
=================================================================

The last versions of our bank model will implement scheduled breaks, or
down time, for our teller resources. Creating and implementing a break
schedule is relatively easy; the more challenging problem: how to handle
customers that the teller is serving when they are supposed to go on break.
We will implement several approaches (some more realistic than others)
that demonstrate different Simprovise capabilities in this area.
