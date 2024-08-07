#===============================================================================
# MODULE bank5b
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# The second step in the fifth iteration of the bank demo/tutorial model. 
# This model will again start from bank3, and add various forms of 
# downtime behavior.
#
# This second step adds scheduled down time to the two regular tellers.
# They each take two fifteen minute breaks. The first teller takes breaks
# two hours and six hours into a nine hour day. The second teller takes
# their breaks immediately after the first - 2:15 and 6:15 into the day.
#
# The processes handle encountering down time by using the 
# extend_through_downtime parameter on the wait_for() call - setting it to
# True causes the wait to be extended by the length of the down time if
# the teller goes down while they are being serviced.
#
# The idea that customers will wait at the counter while their teller takes
# a break is, of course, unrealistic. More realistic handling will be
# explored in subsequent versions of the this model model.
#===============================================================================
from simprovise.core import simtrace
from simprovise.core.simtime import SimTime, Unit as tu
from simprovise.core.simrandom import SimDistribution


from simprovise.modeling import (SimEntitySource, SimEntitySink,
                                 SimScheduledDowntimeAgent, DowntimeSchedule)

from simprovise.simulation import Simulation
from simprovise.demos.bank5 import (RegularCustomer, MerchantCustomer,
                                    Bank, BankTransaction, Teller)
                       
              
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


class RegularTransaction(BankTransaction5b):
    """
    Represents a "regular" transaction by a "regular" (non-merchant)
    customer.
    """
    mean_interarrival_time = SimTime(1, tu.MINUTES)
    mean_service_time = SimTime(2, tu.MINUTES) 
    servicetime_generator = SimDistribution.exponential(mean_service_time)
    
    def __init__(self):
        super().__init__(bank.regular_queue)
    

class MerchantTransaction(BankTransaction5b):
    """
    Represents a merchant transaction (by a merchant customer)
    """
    mean_interarrival_time = SimTime(4, tu.MINUTES)
    mean_service_time = SimTime(3, tu.MINUTES)
    servicetime_generator = SimDistribution.exponential(mean_service_time)

    def __init__(self):
        super().__init__(bank.merchant_queue)


# The bank model consists of a (customer) source, a (customer) sink, and
# a bank.
source = SimEntitySource("Source")
sink = SimEntitySink("Sink")
bank = Bank5b(name="Bank", nRegularTellers=2, nMerchantTellers=1)

# Define and create the (customer) entity generators for the model's entity
# source - one generator for regular customer entities, one for merchant customers.
dist_reg = SimDistribution.exponential(RegularTransaction.mean_interarrival_time) 
dist_merch = SimDistribution.exponential(MerchantTransaction.mean_interarrival_time) 
source.add_entity_generator(RegularCustomer, RegularTransaction, dist_reg)
source.add_entity_generator(MerchantCustomer, MerchantTransaction, dist_merch)

# Set up trace output columns
simtrace.add_trace_column(bank.regular_queue, 'current_population',
                          'Regular Queue')
simtrace.add_trace_column(bank.merchant_queue, 'current_population',
                          'Merchant Queue')

# Use our teller pool properties for these
simtrace.add_trace_column(bank, 'available_regular_tellers',
                          'RegularTellers: available')
simtrace.add_trace_column(bank, 'available_merchant_tellers',
                          'MerchantTellers: available')


if __name__ == '__main__':
    print("================ main=================")
    print("debug:", __debug__)
    warmupLength = SimTime(100, tu.MINUTES)
    batchLength = SimTime(600, tu.MINUTES)
    print("Running single execution...")
    with Simulation.execute(warmupLength, batchLength, 10,
                            outputpath=None, overwrite=False) as simResult:
        simResult.print_summary()
 