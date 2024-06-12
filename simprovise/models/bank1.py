import sys
from enum import Enum
from simprovise.core import simtime, SimTime, simtrace
from simprovise.core.simtime import Unit as tu
##simtime.set_base_unit(tu.MINUTES)


from simprovise.core import (SimEntity, SimEntitySource, SimEntitySink,
                            SimProcess, SimDistribution, SimLocation,
                            SimResourcePool, SimSimpleResource, SimQueue,
                            SimModel, SimClock)

from simprovise.simulation import Simulation
from simprovise.models.queuing_theory_calc import theory_results

class Customer(SimEntity):
    """
    Base class for customer entities
    """

class RegularCustomer(Customer):
    """
    Regular (not merchant) bank customer
    """
    def __str__(self):
        return "RegularCustomer"

class MerchantCustomer(Customer):
    """
    Merchant bank customer
    """
    def __str__(self):
        return "MerchantCustomer"
    

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
    
class Bank(SimLocation):
    """
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
        
        self.teller_pool = SimResourcePool(self.regular_teller, 
                                           self.merchant_teller)
        
        self.regular_queue = SimQueue("RegularQueue", self)
        self.merchant_queue = SimQueue("MerchantQueue", self)
    
    def status_str(self):
        """
        Returns a formatted string of current bank queue and teller
        size/status for the benefit of simulation result tracing.
        """
        qstr = "\tqueue lengths - regular:{0} merchant:{1}"
        qstatus = qstr.format(self.regular_queue.current_population,
                              self.merchant_queue.current_population)
        tstr = "\tteller availability - regular:{0} merchant:{1}"
        tstatus = tstr.format(self.regular_teller.available,
                              self.merchant_teller.available)
        return qstatus + tstatus


def now_str():
    return "{:.2f}\t".format(SimClock.now().to_minutes().to_scalar())

class BankTransaction(SimProcess):
    """
    """        
    #def trace_enter_queue(self, bank):
        #if not trace: return
        #print(now_str(), self.entity, '\tentering queue\t\t', bank.status_str())
    
    #def trace_start_service(self, bank, teller):
        #if not trace: return
        #print(now_str(), self.entity, '\tmoving to:', teller, bank.status_str())
    
    #def trace_service_complete(self, bank, teller):
        #if not trace: return
        #print(now_str(), self.entity, '\tfinished with:', teller, bank.status_str())
        


class RegularTransaction(BankTransaction):
    """
    """
    mean_interarrival_time = SimTime(1, tu.MINUTES)
    mean_service_time = SimTime(3, tu.MINUTES) 
    st_generator = SimDistribution.exponential(mean_service_time)

    def run(self):
        bank = SimModel.model().get_static_object("Bank")
        sink = SimModel.model().get_static_object("Sink")
        service_time = next(RegularTransaction.st_generator)
        customer = self.entity
        customer.move_to(bank.regular_queue)
        with self.acquire_from(bank.teller_pool, RegularTeller) as teller_assignment:
            teller = teller_assignment.resource
            customer.move_to(bank.teller_counter)
            self.wait_for(service_time)
        customer.move_to(sink)

class MerchantTransaction(BankTransaction):
    """
    """
    mean_interarrival_time = SimTime(6, tu.MINUTES)
    mean_service_time = SimTime(4, tu.MINUTES)
    st_generator = SimDistribution.exponential(mean_service_time)

    def run(self):
        bank = SimModel.model().get_static_object("Bank")
        sink = SimModel.model().get_static_object("Sink")
        service_time = next(MerchantTransaction.st_generator)
        customer = self.entity
        customer.move_to(bank.merchant_queue)
        with self.acquire_from(bank.teller_pool, MerchantTeller) as teller_assignment:
            teller = teller_assignment.resource
            customer.move_to(bank.teller_counter)
            self.wait_for(service_time)
        customer.move_to(sink)

source = SimEntitySource("Source")
sink = SimEntitySink("Sink")
bank = Bank(name="Bank", nRegularTellers=4, nMerchantTellers=1)

dist_reg = SimDistribution.exponential(RegularTransaction.mean_interarrival_time) 
dist_merch = SimDistribution.exponential(MerchantTransaction.mean_interarrival_time) 
source.add_entity_generator(RegularCustomer, RegularTransaction, dist_reg)
source.add_entity_generator(MerchantCustomer, MerchantTransaction, dist_merch)

simtrace.add_trace_column(bank.regular_queue, 'current_population', 'Regular Queue')
simtrace.add_trace_column(bank.merchant_queue, 'current_population', 'Merchant Queue')
simtrace.add_trace_column(bank.regular_teller, 'available', 'RegularTellers: available')
simtrace.add_trace_column(bank.merchant_teller, 'available', 'MerchantTellers: available')


if __name__ == '__main__':
    print("================ main=================")
    warmupLength = SimTime(100, tu.MINUTES)
    batchLength = SimTime(600, tu.MINUTES)
    warmupLength = SimTime(10, tu.MINUTES)
    batchLength = SimTime(60, tu.MINUTES)
    #bl = SimTime(10000)
    print("Running single execution...")
    with Simulation.execute(warmupLength, batchLength, 10,
                            outputpath=None, overwrite=False) as simResult:
        simResult.print_summary()
 
    print("\nRegular Customers")
    theory_results(RegularTransaction.mean_interarrival_time.to_scalar(),
                   RegularTransaction.mean_service_time.to_scalar(),
                   bank.regular_teller.capacity)
 
    print("\nMerchant Customers")
    theory_results(MerchantTransaction.mean_interarrival_time.to_scalar(),
                   MerchantTransaction.mean_service_time.to_scalar(),
                   bank.merchant_teller.capacity)
