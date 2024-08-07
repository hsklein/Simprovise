#===============================================================================
# MODULE bank5c
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# The third step in the fifth iteration of the bank demo/tutorial model. 
# This model modifies the down time behavior implemented by bank5b.
#
# This third step includes (from bank5b) scheduled down time to the two regular 
# tellers. They each take two fifteen minute breaks. The first teller takes 
# breaks two hours and six hours into a nine hour day. The second teller takes
# their breaks immediately after the first - 2:15 and 6:15 into the day.
#
# The primary addition to bank5c is TellerDowntimeAgent, a subclass of
# SimScheduledDowntimeAgent. It implements two new downtime behaviors:
#
# 1. If the teller is busy when it's time for a break, the teller isn't
#    taken down; it enters the "going-down" state, where it stays up
#    but is unavailable for new customers. The teller then goes on break
#    when it completes service for the current customer.
#
# 2. The delayed break may overlap with the scheduled break of the other
#    teller. In order to avoid both tellers being on break at the same time
#    each teller checks to see of the other teller is working (and not
#    in the going-down state) before doing step(1) above. (either going on
#    break or setting the going-down state.)
#
# The extend_through_downtime parameter on the wait_for() call is no longer
# needed, so it is set back to the default value of False.
#===============================================================================
from simprovise.core import simtrace
from simprovise.core.simtime import SimTime, Unit as tu
from simprovise.core.simrandom import SimDistribution

from simprovise.core.model import SimModel
from simprovise.modeling import (SimEntitySource, SimEntitySink, 
                                 SimScheduledDowntimeAgent, DowntimeSchedule)
from simprovise.modeling.agent import SimMsgType
from simprovise.simulation import Simulation
from simprovise.demos.bank5 import (RegularCustomer, MerchantCustomer,
                                    Bank, BankTransaction, Teller)
                       
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
    
       
class Bank5c(Bank):
    """
    A subclass of Bank that adds teller downtime agents for the
    regular tellers and subscribes each of them to the other teller downtime
    agents RSRC_UP messages.
    """
    __slots__ = ('downtime_agents')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
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


# Since we no longer need extend_through_downtime, both RegularTransaction
# and MerchantTransaction can go back to inheriting from BankTransaction

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


# The bank model consists of a (customer) source, a (customer) sink, and
# a bank.
source = SimEntitySource("Source")
sink = SimEntitySink("Sink")
bank = Bank5c(name="Bank", nRegularTellers=2, nMerchantTellers=1)

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
 