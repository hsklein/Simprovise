from itertools import chain

from simprovise.core import simtime, SimTime, SimClock, SimError, SimEntitySource, SimEntitySink, SimEntity
from simprovise.core import (SimEntity, SimProcess, SimDistribution,
                         SimLocation, SimCounter, SimResource, SimSimpleResource, 
                         SimResourceAssignment, SimResourceAssignmentAgent, SimMsgType,
                         SimInterruptException, SimResourcePool)
from simprovise.configuration import simelement

STATION_RSRCID = "Station{0}.WorkStn"
STATION_LOCID = "Station{0}"
TABLE_LOCID = "Station{0}.Table"
OPERATOR_ID = "Operator{0}"
QUEUE_ID = "Queue{0}"

N_STATIONS = 6
PRIORITY1_STATIONS = (1, 2)
PRIORITY23_STATIONS = (3, 4, 5, 6)
N_OPERATORS = 3
N_QUEUES = 3

SOURCE_ID = "OrderSource"
SINK_ID = "OrderSink"

stnAssignmentAgent = {}
operAssignmentAgent = None

# Consider adding model parameter to initializeModel() call.
# That would allow us, for example, to retrieve all static objects for the
# model, rather than having to find them by static ID.
# It would probably be better to create a wrapper object around the model object,
# since the model developer should not be accessing using most methods in SimModel -
# perhaps we call this a StaticObjectManager, or something of that ilk
def initializeModel():
    """
    """
    global stnAssignmentAgent
    global operAssignmentAgent
    stnAssignmentAgent[1] = StationAssignmentAgent()
    stnAssignmentAgent[2] = stnAssignmentAgent[3] = StationAssignmentAgent()
    stnAssignmentAgent[1].initialize(PRIORITY1_STATIONS)
    stnAssignmentAgent[2].initialize(PRIORITY23_STATIONS)
    operAssignmentAgent = OperatorAssignmentAgent()
    operAssignmentAgent.initialize()
    
def getPriority(msg):
    """
    Returns the priority of the order associated with a request message.
    Registered as a message priority function with the assignment agents.
    """
    process = msg.msgData[0]
    order = process.entity
    return order.priority
    
class StationAssignmentAgent(SimResourcePool):
    """
    """
    def __init__(self):
        super().__init__()
        self.register_priority_func(SimMsgType.RSRC_REQUEST, getPriority)
        
    def initialize(self, stationNumbers):
        """
        """
        for i in stationNumbers:
            stnResource =  WorkTable(STATION_RSRCID.format(i))
            self.add_resource(stnResource)
    
class OperatorAssignmentAgent(SimResourcePool):
    """
    """
    def __init__(self):
        super().__init__()
        self.register_priority_func(SimMsgType.RSRC_REQUEST, getPriority)
        
    def initialize(self):
        """
        """
        for i in range(1, N_OPERATORS + 1):
            operator = Operator(OPERATOR_ID.format(i))
            self.add_resource(operator)
        
    def assignFromRequest(self, msg):
        """
        Looks for an available operator managed by this assignment agent. If 
        found, the requesting process is assigned that operator. This is all
        part of the pool's default behavior.
        
        But... if there is no available operator AND this request is from a
        priority 1 order, then we will pre-empt a lower priority order (if 
        there is one.)
        """
        process, n, resourceClass = msg.msgData
        order = process.entity
        
        availableOperators = self.available_resources()
        if availableOperators:
            operator = availableOperators[0]
            return self._create_resource_assignment(process, operator)
         
        # No operator available.  
        # For priority 1 orders, find a lower priority order to pre-empt.
        # The lucky winner is chosen first based on lowest priority, then
        # most recently started. We will rely on the pool's resource release
        # handler to retry the priority 1 order once the interrupted order
        # releases its operator.
        if order.priority == 1:
            for priority in (3, 2):
                orders = self._inProcessOrders(priority)
                if orders:
                    orderToPreempt = max(orders, 
                                         key = lambda t: t.operAssignment.assign_time)
                    print(priority, orderToPreempt.operAssignment.assign_time)
                    orderToPreempt.interrupt("Preempted")
           
        # Return None, so that the request will be enqueued for fulfillment
        # later. If we have pre-empted a lower priority order, this will
        # happen straight away
        return None   
    
    def _inProcessOrders(self, priority):
        """
        Return a list of all in-process (have an operator working on them) 
        orders of a specified priority
        """
        # Get the orders (processes) currently assigned an operator in the pool.
        orders = self.current_transactions()
        
        # return the subset of orders that have  the requested priority
        return [order for order in orders if order.priority == priority]
  
  
@simelement(graphicFile="person1.png")
class Operator(SimSimpleResource):
    """
    A basic operator resource
    """
    
class Order(SimEntity):
    """
    Order base class
    """
    def __init__(self, source, process, color, priority):
        super().__init__(source, process, fillColor=color)
        self.priority = priority
        #self.stationNumber = None
    
@simelement()
class P1_Order(Order):
    """
    Priority 1 Order
    """
    def __init__(self, source, process):
        super().__init__(source, process, 'orange', 1)
    
@simelement()
class P2_Order(Order):
    """
    Priority 2 Order
    """
    def __init__(self, source, process):
        super().__init__(source, process, 'blue', 2)
    
@simelement()
class P3_Order(Order):
    """
    Priority 3 Order
    """
    def __init__(self, source, process):
        super().__init__(source, process, 'green', 3)


@simelement()
class WorkTable(SimSimpleResource):
    """
    A basic work table resource
    """
    
class OrderProcess(SimProcess):
    """
    Base class for orders (of all priorities)
    """
    def __init__(self, priority):
        super().__init__()
        self.priority = priority
        self.operAssignment = None
        self.waitTime = SimTime(30)

    def run(self):
        queue = SimLocation(QUEUE_ID.format(self.priority))
        sink = SimEntitySink(SINK_ID)       
        
        order = self.entity
        order.move_to(queue)
                
        tableAssignment = self.acquire_from(stnAssignmentAgent[self.priority], 
                                           WorkTable)
        workLoc = tableAssignment.resource.location
        order.move_to(workLoc)
        
        #operator.opacity = 0.5
         
        
        timeleft = self.waitTime
        while timeleft:
            print("acquiring operator for order priority", order.priority)
            operAssignment = self.acquire_from(operAssignmentAgent, Operator)
            self.operAssignment = operAssignment
            operator = operAssignment.resource
            operator.move_to(workLoc)
            startTime = SimClock.now()
            order.opacity = None # default
            
            try:
                self.wait_for(timeleft)
                timeleft = 0
            except SimInterruptException as e:
                order.opacity = 0.25
                timeleft = timeleft - (SimClock.now() - startTime)
                print(e.reason, "time left:", timeleft)
                assert timeleft > 0, "Interrupted with zero time left!"
                self.release(operAssignment)
       
        # By releasing the table assignment first, we can avoid some of the
        # cases where the operator at a priority 1 station is assigned to a
        # priority 2/3 order, only to be immediately interrupted/reassigned to
        # a new priority 1 order.
        self.release(tableAssignment)
        self.release(operAssignment)
        order.opacity = 1.0
        #entity.fillColor = currentColor
        #teller.fillColor = None # default
        
        order.move_to(sink)

@simelement()
class OrderProcess1(OrderProcess):
    waitTimeGenerator = None
   
    @classmethod
    def initializeClassData(cls):
        """
        Initialize class member data, invoked the first time a process is created
        for each run.
        """
        cls.waitTimeGenerator = \
           SimDistribution.number_generator(SimDistribution.exponential, SimTime(10), 2)
            
    def __init__(self):
        super().__init__(1)
        #self.waitTime = next(self.waitTimeGenerator)
                 

@simelement()
class OrderProcess2(OrderProcess):
    waitTimeGenerator = None
   
    @classmethod
    def initializeClassData(cls):
        """
        Initialize class member data, invoked the first time a process is created
        for each run.
        """
        cls.waitTimeGenerator = \
           SimDistribution.number_generator(SimDistribution.exponential, SimTime(10), 3)
            
    def __init__(self):
        super().__init__(2)
        #self.waitTime = next(self.waitTimeGenerator)

@simelement()
class OrderProcess3(OrderProcess):
    waitTimeGenerator = None
   
    @classmethod
    def initializeClassData(cls):
        """
        Initialize class member data, invoked the first time a process is created
        for each run.
        """
        cls.waitTimeGenerator = \
           SimDistribution.number_generator(SimDistribution.exponential, SimTime(10), 4)
            
    def __init__(self):
        super().__init__(3)
        #self.waitTime = next(self.waitTimeGenerator)
