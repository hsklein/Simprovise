#===============================================================================
# MODULE bank5a
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# The first step in the fifth iteration of the bank demo/tutorial model. 
# This model will again start from bank3, and eventually add various
# forms of downtime behavior.
#
# This initial step is functionally the same as bank3. The changes:
#
# - The BankTransaction classes have been refactored to consolidate code
#   from the two subclass run() methods into the base class
#
# - In preparation for introducing down time, the individual tellers are
#   now separate resources - e.g., we use three RegularTeller objects instead
#   of one with capacity 3. (We will need separate resources to take down
#   individual tellers; taking down a RegularTeller with capacity 3
#   makes all three down and unavailable)
#
#===============================================================================
from simprovise.core import simtrace
from simprovise.core.simtime import SimTime, Unit as tu
from simprovise.core.simrandom import SimDistribution

from simprovise.demos.bank5 import (RegularCustomer, MerchantCustomer,
                                    Bank, BankTransaction)
from simprovise.modeling import SimEntitySource, SimEntitySink
from simprovise.simulation import Simulation


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
bank = Bank(name="Bank", nRegularTellers=2, nMerchantTellers=1)

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

# Use our bank properties for these
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
 