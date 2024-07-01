#===============================================================================
# MODULE bank1
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines one iteration of the bank demo model.
#===============================================================================
import sys, os
from enum import Enum
#print("*********importing bank1****** pid:", os.getpid())
from simprovise.core import simtime, simtrace
from simprovise.core.simtime import SimTime, Unit as tu
from simprovise.core.simrandom import SimDistribution
from simprovise.core.model import SimModel

from simprovise.modeling import (SimEntity, SimEntitySource, SimEntitySink,
                                 SimProcess, SimLocation,
                                 SimResourcePool, SimSimpleResource, SimQueue)

from simprovise.simulation import Simulation
from simprovise.demos.queuing_theory_calc import theory_results

            
class Teller(SimSimpleResource):
    """
    A set of bank teller resources (capacity > 1 represents multiple
    tellers)
    """

class Customer(SimEntity):
    """
    Base class for bank customer entities
    """
    
class Bank(SimLocation):
    """
    A simLocation that encapsulates all of the objects (resources,
    queues and locations) that comprise a bank.
    """
    def __init__(self, name="Bank", nTellers=1):
        super().__init__(name)
        self.teller_counter = SimLocation("TellerCounter", self)
        self.teller = Teller("Teller", self.teller_counter, capacity = nTellers)       
        self.customer_queue = SimQueue("CustomerQueue", self)
        
        
# The bank model consists of a (customer) source, a (customer) sink, and
# a bank with a specified number of tellers.
source = SimEntitySource("Source")
sink = SimEntitySink("Sink")
bank = Bank(nTellers=4)

# Customer interarrival times and service times are both exponentially
# distributed. Set distribution means and create generators for psuedo-
# random samples.
mean_interarrival_time = SimTime(1, tu.MINUTES)
mean_service_time = SimTime(3, tu.MINUTES) 
servicetime_generator = SimDistribution.exponential(mean_service_time)
interarrivaltime_generator = SimDistribution.exponential(mean_interarrival_time)

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
        
# Dreate the (customer) entity generators for the model's entity source.
source.add_entity_generator(Customer, BankTransaction, interarrivaltime_generator)


# Set up trace output
simtrace.add_trace_column(bank.teller, 'available', 'Tellers: available')
#simtrace.add_trace_column(bank.merchant_teller, 'available', 'MerchantTellers: available')


if __name__ == '__main__':
    #print("================ main=================")
    warmupLength = SimTime(100, tu.MINUTES)
    batchLength = SimTime(1000, tu.MINUTES)
    nbatches = 10
    nruns = 10
    print("Running {0} replications...".format(nruns))
    with Simulation.execute(warmupLength, batchLength, nbatches) as simResult:
        simResult.print_summary()
        
    #with Simulation.replicate(None, warmupLength, batchLength, nbatches,
                              #fromRun=1, toRun=nruns) as simResult:
        #simResult.print_summary()
    
 
    print("\nM/M/{0} theory result:".format(bank.teller.capacity))
    theory_results(mean_interarrival_time.to_scalar(),
                  mean_service_time.to_scalar(),
                   bank.teller.capacity)
 