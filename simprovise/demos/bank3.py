#===============================================================================
# MODULE bank3
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the third iteration of the bank demo/tutorial model. This model
# modifies the teller assignment logic my allowing tellers of either type
# (merchant or regular) to serve customers of the other type if their "own"
# queue is empty.
#
# This is implemented by creating a model-specific subclass of SimResourcePool
# with a specialized process_queued_requests() method implementation. This 
# method is called by the simulation whenever it is time to (at least attempt)
# to assign resource(s) (tellers, in this case) to entities (customers).
#===============================================================================
import sys
from simprovise.core import simtime, simtrace
from simprovise.core.simtime import SimTime, Unit as tu
from simprovise.core.simrandom import SimDistribution
from simprovise.core.model import SimModel

from simprovise.modeling import (SimEntity, SimEntitySource, SimEntitySink,
                                 SimProcess, SimLocation,
                                 SimResourcePool, SimSimpleResource, SimQueue)

from simprovise.simulation import Simulation

class Customer(SimEntity):
    """
    Base class for bank customer entities
    """

class RegularCustomer(Customer):
    """
    Regular (not merchant) bank customer
    """

class MerchantCustomer(Customer):
    """
    Merchant bank customer
    """
    
class Teller(SimSimpleResource):
    """
    Base class for teller resources
    """

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
    
class TellerPool(SimResourcePool):
    """
    A specialization of SimResourcePool that implements round 3 of
    teller assignment logic: merchant and regular tellers each
    prioritize their respective customer types, but will serve
    customers of the other type if their own queue is empty -
    i.e., if a regular teller is available, the regular customer
    queue is empty, and there is a merchant customer in the
    merchant queue, then assign that merchant customer to the
    available regular teller.
    """
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
        
    def process_queued_requests(self, throughRequest=None):
        """
        This is the method that should be overloaded to implement
        customized resource assignment logic for the pool. It
        implements the teller assignment logic described above.
        
        Requests are objects of class resource.SimResourceRequest;
        we use method SimResourceRequest.assign_resource() to
        assign a teller to the customer associated with that
        request. assign_resource() takes care of all of the paperwork :-)
        
        Since this model does not use resource acquisition timeouts,
        throughRequest will always be None and we don't have to
        worry about it. 
        """
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
        self.regular_teller = RegularTeller("RegularTeller",
                                            self.teller_counter,
                                            capacity = nRegularTellers)
        
        self.merchant_teller = MerchantTeller("MerchantTeller",
                                              self.teller_counter,
                                              capacity = nMerchantTellers)
        
        self.teller_pool = TellerPool(self.regular_teller, 
                                         self.merchant_teller)
        
        self.regular_queue = SimQueue("RegularQueue", self)
        self.merchant_queue = SimQueue("MerchantQueue", self)


class BankTransaction(SimProcess):
    """
    Base class for simulated bank transaction classes
    """        

class RegularTransaction(BankTransaction):
    """
    Represents a "regular" transaction by a "regular" (non-merchant)
    customer.
    """
    mean_interarrival_time = SimTime(1, tu.MINUTES)
    mean_service_time = SimTime(2, tu.MINUTES) 
    st_generator = SimDistribution.exponential(mean_service_time)

    def run(self):
        bank = SimModel.model().get_static_object("Bank")
        sink = SimModel.model().get_static_object("Sink")
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
    mean_interarrival_time = SimTime(4, tu.MINUTES)
    mean_service_time = SimTime(3, tu.MINUTES)
    st_generator = SimDistribution.exponential(mean_service_time)

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

# The bank model consists of a (customer) source, a (customer) sink, and
# a bank.
source = SimEntitySource("Source")
sink = SimEntitySink("Sink")
bank = Bank(name="Bank", nRegularTellers=2, nMerchantTellers=1)

# Define and create the (customer) entity generators for the model's entity
# source - one generator for regular customer entities, one for merchant customers.
dist_reg = SimDistribution.exponential(RegularTransaction.mean_interarrival_time) 
dist_merch = SimDistribution.exponential(MerchantTransaction.mean_interarrival_time) 
source.add_entity_generator(RegularCustomer, RegularTransaction, dist_reg)
source.add_entity_generator(MerchantCustomer, MerchantTransaction, dist_merch)

# Set up trace output columns
simtrace.add_trace_column(bank.regular_queue, 'current_population', 'Regular Queue')
simtrace.add_trace_column(bank.merchant_queue, 'current_population', 'Merchant Queue')
simtrace.add_trace_column(bank.regular_teller, 'available', 'RegularTellers: available')
simtrace.add_trace_column(bank.merchant_teller, 'available', 'MerchantTellers: available')


if __name__ == '__main__':
    print("================ main=================")
    print("debug:", __debug__)
    warmupLength = SimTime(100, tu.MINUTES)
    batchLength = SimTime(600, tu.MINUTES)
    #warmupLength = SimTime(10, tu.MINUTES)
    #batchLength = SimTime(60, tu.MINUTES)
    #bl = SimTime(10000)
    print("Running single execution...")
    with Simulation.execute(warmupLength, batchLength, 10,
                            outputpath=None, overwrite=False) as simResult:
        simResult.print_summary()
 