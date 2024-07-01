#===============================================================================
# Model script - priority_queue_demo
#
# Copyright (C) 2016 Howard Klein - All Rights Reserved
#
# A model that demonstrates a single server resource with a priority queue and
# resource pre-emption.
#
# Processes are assigned a priority (1-3), with 1 having the highest priority.
# When the server resource becomes available, priority 2 processes will jump
# any priority 3 processes in the queue. Priority 1 processes not only jump
# the queue - they also pre-empt a priority 2 or 3 process currently being
# served. The entity associated with the pre-empted process moves to a holding
# location while priority 1 entities/processes are served; once there are no
# more priority 1 processes in the queue, the entity in the holding area moves
# back to the service location and that process is resumed.
#===============================================================================
from simprovise.core import (simtime, SimTime, SimClock, SimError, SimEntitySource,
                            SimEntitySink, SimEntity)
from simprovise.core import (SimEntity, SimProcess,
                            SimDistribution, SimLocation, SimCounter, SimResource,
                            SimSimpleResource, SimMsgType, SimInterruptException)

from simprovise.configuration import simelement

resource = None

def initializeModel():
    """
    Model initialization - grab a reference to the single model resource and
    assign it a request prioritization function.
    """
    global resource
    resource = SimSimpleResource("Resource1")
    resource.request_priority_func = getPriority

def getPriority(msg):
    """
    Request prioritization function. Processes in the queue are prioritized
    by the process priority attribute value. Processes that have been pre-empted
    (as indicated by the isHolding attribute) are prioritized over queued
    priority 2 and 3 processes (but not priority 1) - hence they are assigned
    a priority of 1.5.
    """
    process = msg.msgData[0]
    if process.isHolding:
        # Interrupted processes should have higher priority than incoming
        # priority 2 or 3 processes
        assert process.priority > 1, "Priority 1 process should not be holding"
        return 1.5
    else:
        return process.priority

@simelement()
class PrioritizingResource(SimSimpleResource):
    """
    The resource needs to override default behavior during request handling,
    in order to pre-empt priority 2 or 3 processes when a priority 1 process
    arrives. We can do this through an override of either
    handleResourceRequest() or assignFromRequest(); in either case, we
    perform pre-emption logic and then defer to the base class to do its thing.
    """
    def assignFromRequest(self, msg):
        """
        If the incoming msg is from a priority 1 process, check to see if the
        currently executing process is not priority 1 - if so, pre-empt it.
        Then invoke/return the base class method, which will do the actual
        assignment - eventually. The base class assignFromRequest() call will
        execute before the actual interrupt event is processed, so we rely
        on the resource release processing that occurs after the interrupt
        to then re-assign  the resource to the priority 1 process.
        """
        process = msg.msgData[0]
        if process.priority == 1:
            if self.current_transactions:
                currentProcess = self.current_transactions[0]
                if currentProcess.priority > 1:
                    currentProcess.interrupt("Pre-empted by priority 1 process")
        return super()._assign_from_request(msg)


class TestProcess(SimProcess):
    """
    Base class for our processes. Initializer takes a priority and color
    argument. Subclasses are defined for each order priority, setting the
    priority and the entity color corresponding to that priority.
    """
    waitTimeGenerator = None

    @classmethod
    def initializeClassData(cls):
        """
        Initialize class member data, invoked the first time a process is created
        for each run.
        """
        TestProcess.waitTimeGenerator = \
           SimDistribution.number_generator(SimDistribution.exponential, SimTime(3), 2)
        #TestProcess.rsrc = SimSimpleResource("Resource1")

    def __init__(self, priority=1, entitycolor='red'):
        """
        Initialize a new process instance with priority and entity fill color.
        Also sample the wait time random generator to set the process wait time.
        The entity object itself has not been instantiated yet, so we can't
        actually set the entity's fillColor here - we do so within run()
        """
        super().__init__()
        self.priority = priority
        self.fillColor = entitycolor
        self.waitTime = next(TestProcess.waitTimeGenerator)
        self.isHolding = False

    def run(self):
        """
        Process run logic - move into the queue, acquire the resource,
        hold the resource for the process wait time, release the resource
        and move to the sink.

        Priority 2 and 3 processes may be pre-empted, so handle pre-emption
        and resource re-acquisition within a loop.
        """
        queue = SimLocation("Queue1")
        workloc = SimLocation("WorkLocation1")
        holdingArea = SimLocation("HoldingArea")
        sink = SimEntitySink("Sink")
        entity = self.entity
        entity.fillColor = self.fillColor
        entity.text = str(self.priority)
        entity.move_to(queue)

        timeleft = self.waitTime
        while timeleft:
            rsrcAssignment = self.acquire(resource)
            self.isHolding = False
            startTime = SimClock.now()
            resource.fillColor = 'red'
            entity.move_to(workloc)
            try:
                self.wait_for(timeleft)
                timeleft = 0
                self.release(rsrcAssignment)
            except SimInterruptException as e:
                # We were pre-empted.
                timeleft = timeleft - (SimClock.now() - startTime)
                assert timeleft > 0, "Interrupted with zero time left!"
                self.isHolding = True
                self.release(rsrcAssignment)
                assert holdingArea.current_population == 0, "Moving second entity to holding area"
                entity.move_to(holdingArea)

        resource.fillColor = None # default
        entity.move_to(sink)


@simelement()
class TestProcess1(TestProcess):
    """
    Concrete process class for priority 1 processes
    """
    def __init__(self):
        super().__init__(1, 'red')

@simelement()
class TestProcess2(TestProcess):
    """
    Concrete process class for priority 2 processes
    """
    def __init__(self):
        super().__init__(2, 'blue')

@simelement()
class TestProcess3(TestProcess):
    """
    Concrete process class for priority 3 processes
    """
    def __init__(self):
        super().__init__(3, 'green')


