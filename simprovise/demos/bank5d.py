#===============================================================================
# MODULE bank5d
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# The final step in the fifth iteration of the bank demo/tutorial model. 
# This model will modify the teller down time implementation by adding
# and handling a timeout to the teller going-down phase introduced by the 
# bank5c model.
#
# This version models the notion that the teller scheduled for a break 
# shouldn't have to wait too long to actually go on break - what happens if 
# they happen to be servicing a particularly long transaction at break time? 
# We model this by:
#
# - Adding a timeout to the going-down phase via the timeout parameter to
#   _set_resource_going_down(). The teller is then taken down at the end of
#   the timeout period if it hasn't come down already.
#
# - If the timeout fires and a customer is still holding that teller,
#   a SimResourceDownException will be raised in that customer's
#   transaction.run() method; that method handles the exception by
#   reacquiring a (probably different) teller and completing the transaction.
#   (Note that we must handle the possibility that the second teller can go down
#   as well.)
#
# - Finally, we don't want this kicked-out customer to go to the end of the
#   queue when acquiring a new teller - so we give each transaction process
#   a priority (2 normally, 1 after being kicked out) and set a resource
#   request priority function on the teller pool that uses these priority
#   values. This ensures that the kicked-out customer gets the next available
#   teller to complete it's transaction.
#
#===============================================================================
from simprovise.core import simtrace
from simprovise.core.simtime import SimTime, Unit as tu
from simprovise.core.simrandom import SimDistribution
from simprovise.core.simclock import SimClock

from simprovise.core.model import SimModel
from simprovise.modeling import (SimEntitySource, SimEntitySink, 
                                 SimScheduledDowntimeAgent, DowntimeSchedule,
                                 SimResourceDownException)
from simprovise.modeling.agent import SimMsgType
from simprovise.simulation import Simulation
from simprovise.demos.bank5 import (RegularCustomer, MerchantCustomer,
                                    Bank, BankTransaction, Teller)
                       
class TellerDowntimeAgent(SimScheduledDowntimeAgent):
    """
    Modifies the ``TellerDowntimeAgent`` implemented in bank5c by adding
    a timeout to the going-down state; if the customer holding  the
    going-down teller doesn't release it before the timeout, the teller
    is taken down anyway. The takedown will raise a ``SimResourceDownException``
    which must be handled by the customer's ``run()`` method.
    
    The timeout is set to four minutes, to ensure that this behavior gets
    executed during a simulation.
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
            # start going-down with a timeout of four minutes
            self._set_resource_going_down(timeout=SimTime(4, tu.MINUTES))
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
        
        return True
    
       
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
                        
    def make_downtime_agents(self):
        """
        Create two downtime schedules, use them to create two scheduled
        downtime agents, and assign each of those agents to a regular teller
        resource. (We'll assume at least two regular tellers.)
        """
        downtime_schedules = self.make_schedules()
        tellers = self.regular_tellers        
        return [TellerDowntimeAgent(tellers[i], sched)
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


class RegularTransaction(BankTransaction5d):
    """
    Represents a "regular" transaction by a "regular" (non-merchant)
    customer.
    """
    mean_interarrival_time = SimTime(1, tu.MINUTES)
    mean_service_time = SimTime(2, tu.MINUTES) 
    servicetime_generator = SimDistribution.exponential(mean_service_time)
    
    def __init__(self):
        super().__init__(bank.regular_queue)
    

class MerchantTransaction(BankTransaction5d):
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
bank = Bank5d(name="Bank", nRegularTellers=2, nMerchantTellers=1)

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
 