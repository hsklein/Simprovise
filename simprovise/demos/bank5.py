#===============================================================================
# MODULE bank5
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
from simprovise.modeling import (SimEntity, SimLocation, SimResourcePool,
                                 SimSimpleResource, SimQueue, SimProcess)
from simprovise.core.model import SimModel


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
    def __str__(self):
        return self.element_name

class RegularTeller(Teller):
    """
    A teller primarily for regular customers
    """

class MerchantTeller(Teller):
    """
    A teller primarily for merchant customers
    """
    
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