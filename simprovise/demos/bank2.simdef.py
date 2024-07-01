#===============================================================================
# Model script - bank2
#
# Copyright (C) 2015-2016 Howard Klein - All Rights Reserved
#
# A model that simulates a typical bank teller lobby, with one merchant teller
# and a number of "regular" tellers. Regular and merchant customers enter
# separate queues. The merchant tellers priority is servicing the merchant
# customers, but if there are no merchant customers in the queue, the merchant
# teller can take on regular customers.
#
# The model demonstrates the use of a customized (through priority function and
# subclassing) SimResourcePool - a resource pool that manages assignments to
# teller (both regular and merchant) resources.
#===============================================================================
from collections import deque
from simprovise.core import (simtime, SimTime, SimClock, SimError,
                            SimEntitySource, SimEntitySink, SimEntity, SimProcess,
                            SimResourceAssignmentAgent, SimResourceAssignment,
                            SimMsgType, SimResourcePool)
from simprovise.core import (SimEntity, SimProcess,
                            SimDistribution, SimLocation, SimCounter,
                            SimResource, SimSimpleResource)
from simprovise.configuration import simelement

#print("Loading bank2")
N_TELLERS = 3
TELLER_ID = "TellerArea.TellerLocation{0}.Teller"
TELLER_INOUT_LOCID = "TellerArea.TellerLocation{0}.InOut"
TELLER_WINDOW_LOCID = "TellerArea.TellerLocation{0}.Window"

MERCHANT_TELLER_ID = "TellerArea.MerchantLocation.Teller"
MERCHANT_TELLER_INOUT_LOCID = "TellerArea.MerchantLocation.InOut"
MERCHANT_TELLER_WINDOW_LOCID = "TellerArea.MerchantLocation.Window"

assignmentAgent = None

def getTellerLocations(teller):
    """
    Returns the inout and window locations corresponding to a passed
    teller.
    Works by looping through the tellers to find the passed teller's
    teller number, and then finding the corresponding locations. The
    more elegant algorithm would find the teller's location ID, and
    then get the child locations with the passed names.
    """
    for i in range(1, N_TELLERS + 1):
        tellerID = TELLER_ID.format(i)
        if teller == Teller(tellerID):
            inoutLoc = SimLocation(TELLER_INOUT_LOCID.format(i))
            windowLoc = SimLocation(TELLER_WINDOW_LOCID.format(i))
            return inoutLoc, windowLoc

    if teller == Teller(MERCHANT_TELLER_ID):
        return (SimLocation(MERCHANT_TELLER_INOUT_LOCID),
                SimLocation(MERCHANT_TELLER_WINDOW_LOCID))

    assert False, "Teller locations not found"

def initializeModel():
    """
    The model is initialized by creating a new assignment agent. The agent can
    be either a BankAssignmentAgent or a BankAssignmentAgent2; though
    implemented differently, the two classes have identical behavior.
    """
    global assignmentAgent
    assignmentAgent = BankAssignmentAgent()

class BankAssignmentAgent(SimResourcePool):
    """
    The BankAssignmentAgent manages a pool of tellers (regular and merchant).
    It operates as a bank with merchant teller window(s) typically do -
    There is a separate queue for merchant customers, and the merchant teller
    handles those customers first.  If, however, there are no merchant
    customers in line and there is a regular customer waiting for a teller,
    the merchant teller can go ahead and handle that regular customer.

    In all cases, we rely on the fact that regular customer processes
    request a resource of class Teller, while merchant customers request a
    resource of class MerchantTeller - and MerchantTeller is a subclass of
    Teller.

    We also rely on the fact that (a) regular tellers are in the "front" of
    the pool's resource list (added first) while merchant tellers come after
    that, and (b) the pool code that finds an available resource always
    starts searching from the beginning of that list. This ensures that
    regular customers are not assigned to a merchant teller unless all
    regular tellers are busy.

    This implementation uses the infrastructure build into SimResourcePool
    to implement the logic above; the only specialization is a priority
    function applied to determine the next request that the pool will
    attempt to fulfill.

    At first glance, it might seem sufficient for us simply to assign a higher
    priority to merchant requests, ensuring that merchants get first crack at
    the merchant teller. The problem with that is that the pool (like its
    SimResourceAssignmentAgent base class) will block if the highest priority
    request cannot be fulfilled - so if a merchant customer is waiting for
    the merchant teller to become available, then regular customers will
    wait as well, even if regular tellers are available.

    The priority function gets around that by assigning a lower priority (a
    higher number) to any request (merchant OR regular) that cannot be
    fulfilled at the time the function is invoked. This ensures that merchant
    customers are assigned to available merchant tellers first, regular
    customers are assigned to any available teller second, while customers
    that cannot currently be served do not block those who can.
    """
    def __init__(self):
        super().__init__()
        # Initialize priority function
        self.request_priority_func = self.getPriority
        self.initialize()

    def getPriority(self, msg):
        """
        MerchantTeller requests are prioritized over regular customers;
        however, we de-prioritize (priority=3) any request that cannot
        currently be fulfilled so that we do not block regular customers
        from obtaining regular tellers when the merchant teller is not
        available.
        """
        rsrcClass = msg.msgData[2]
        if not self.available(rsrcClass):
            return 3
        elif rsrcClass is MerchantTeller:
            return 1
        else:
            return 2

    def initialize(self):
        """
        Add all of the teller resources to the pool
        """
        merchantTeller = Teller(MERCHANT_TELLER_ID)
        self.add_resource(merchantTeller)
        for i in range(1, N_TELLERS + 1):
            tellerID = TELLER_ID.format(i)
            teller = Teller(tellerID)
            self.add_resource(teller)


class BankAssignmentAgent2(SimResourcePool):
    """
    This second version of the bank teller assignment agent is structured
    differently. It bypasses much of the base class code by specializing both
    handleResourceRequest() and handleResourceRelease(). This approach makes
    for a bit more code and requires that that code do some
    not-always-obvious housekeeping - but it is perhaps a bit more reflective
    of how the real bank might operate.

    This assignment agent runs it's own two queues in place of the SimAgent
    built-in message queue. Requests that cannot be fulfilled on arrival
    are put into either a regular customer or merchant customer queue.
    When a (teller) resource is released, the agent looks at that teller's
    type (class), and picks a request from one of the queues accordingly.
    """
    def __init__(self):
        super().__init__()
        self.regularQueue = deque()
        self.merchantQueue = deque()
        self.initialize()

    def initialize(self):
        """
        Add all of the teller resources to the pool
        """
        merchantTeller = Teller(MERCHANT_TELLER_ID)
        self.add_resource(merchantTeller)
        for i in range(1, N_TELLERS + 1):
            tellerID = TELLER_ID.format(i)
            teller = Teller(tellerID)
            self.add_resource(teller)

    def handleResourceRequest(self, msg):
        """
        Handle an incoming teller request. If a teller of the requested
        type/class is available, go ahead and allow _processRequest() to
        assign it (the default pool behavior will do so just fine) and take
        care of the paperwork. Otherwise, put the request in the appropriate
        queue.
        """
        process, n, tellerClass = msg.msgData
        if self.available(tellerClass):
            assigned = self._process_request(msg)
            assert assigned, "Request on available teller not assigned"
        elif tellerClass is MerchantTeller:
            self.merchantQueue.append(msg)
        else:
            self.regularQueue.append(msg)

        # Consider the message handled, since this class is managing its own
        # queue
        return True

    def handleResourceRelease(self, msg):
        """
        Handle a teller release.
        """
        assignment, releaseSpec = msg.msgData
        assert len(assignment.resources) == 1, "handleResourceRelease expecting only a single resource"

        # Do the release paperwork
        teller = assignment.resource
        teller.release_from(assignment.process)
        assignment.subtract_all()

        # If we've just released a merchant teller and there are merchant
        # customers in the queue, process and assign the next merchant
        # customer request. Otherwise, process/assign the next regular
        # customer (if there is one)
        if isinstance(teller, MerchantTeller) and len(self.merchantQueue) > 0:
            nextMsg = self.merchantQueue.popleft()
            self._process_request(nextMsg)
        elif len(self.regularQueue) > 0:
            nextMsg = self.regularQueue.popleft()
            self._process_request(nextMsg)

        # Message handled regardless, return True
        return True



@simelement()
class Teller(SimSimpleResource):
    """
    A basic teller resource
    """

@simelement()
class MerchantTeller(Teller):
    """
    A merchant teller specialization
    """

@simelement(graphicPrototypeName="Person")
class Customer(SimEntity):
    """
    """

@simelement(graphicFile="blueperson.png")
class Merchant(SimEntity):
    """
    A merchant entity class, demonstrating use of a custom graphicFile for
    animation.  fillColor property doesn't yet work on entity graphics
    supplied via image files.
    """
    def __init__(self, source, process):
        super().__init__(source, process, fillColor='green', text='M', fontSize=20)

@simelement()
class CustomerProcess(SimProcess):
    waitTimeGenerator = None

    @classmethod
    def initializeClassData(cls):
        """
        Initialize class member data, invoked the first time a process is created
        for each run.
        """
        cls.waitTimeGenerator = \
           SimDistribution.number_generator(SimDistribution.exponential, SimTime(12), 2)

    def __init__(self):
        super().__init__()
        self.waitTime = next(self.waitTimeGenerator)

    def run(self):
        queue = SimLocation("TellerQueue")
        sink = SimEntitySink("CustomerSink")
        entity = self.entity
        entity.move_to(queue)
        rsrcAssignment = self.acquire_from(assignmentAgent, Teller)

        teller = rsrcAssignment.resource
        inoutLoc, windowLoc = getTellerLocations(teller)

        entity.move_to(SimLocation("TellerArea.Entrance"))
        entity.move_to(inoutLoc)
        entity.move_to(windowLoc)
        teller.fillColor = 'red'

        currentColor = entity.fillColor
        entity.fillColor = 'red'
        self.wait_for(self.waitTime)
        self.release(rsrcAssignment)
        entity.fillColor = currentColor
        teller.fillColor = None # default

        entity.move_to(inoutLoc)
        entity.move_to(SimLocation("TellerArea.Exit"))
        entity.move_to(sink)


@simelement()
class MerchantProcess(SimProcess):
    waitTimeGenerator = None

    @classmethod
    def initializeClassData(cls):
        """
        Initialize class member data, invoked the first time a process is created
        for each run.
        """
        cls.waitTimeGenerator = \
           SimDistribution.number_generator(SimDistribution.exponential, SimTime(12), 3)

    def __init__(self):
        super().__init__()
        self.waitTime = next(self.waitTimeGenerator)

    def run(self):
        queue = SimLocation("MerchantQueue")
        sink = SimEntitySink("CustomerSink")
        entity = self.entity
        entity.move_to(queue)
        rsrcAssignment = self.acquire_from(assignmentAgent, MerchantTeller)

        teller = rsrcAssignment.resource
        inoutLoc, windowLoc = getTellerLocations(teller)

        entity.move_to(inoutLoc)
        entity.move_to(windowLoc)
        teller.fillColor = 'red'

        currentColor = entity.fillColor
        entity.fillColor = 'red'
        self.wait_for(self.waitTime)
        self.release(rsrcAssignment)
        entity.fillColor = currentColor
        teller.fillColor = None # default

        entity.move_to(inoutLoc)
        entity.move_to(SimLocation("TellerArea.Exit"))
        entity.move_to(sink)