from simprovise.core import simtime, SimTime, SimClock, SimError, SimEntitySource, SimEntitySink, SimEntity
from simprovise.core import (SimEntity, SimProcess, SimDistribution,
                         SimLocation, SimCounter, SimResource, SimSimpleResource)

from simprovise.configuration import simelement

print("loading mm1-1...")

@simelement()
class TestProcess(SimProcess):
    #counter = SimCounter(None, 1) # counter with capacity 1, acts like resource
    rsrc = None
    waitTimeGenerator = None
    
    @classmethod
    def initializeClassData(cls):
        """
        Initialize class member data, invoked the first time a process is created
        for each run.
        """
        TestProcess.waitTimeGenerator = \
           SimDistribution.number_generator(SimDistribution.exponential, SimTime(9), 2)
        TestProcess.rsrc = SimSimpleResource("Resource1")
      
    def __init__(self):
        super().__init__()
        self.waitTime = next(TestProcess.waitTimeGenerator)
        
    def run2(self):
        entity = self.entity        
        entity.move_to(sink)
        
    def run(self):
        testQueue = SimLocation("Queue1")
        workloc = SimLocation("WorkLocation1")
        sink = SimEntitySink("Sink")
        entity = self.entity
        entity.move_to(testQueue)
        
        rsrcAssignment = self.acquire(TestProcess.rsrc)
        entity.move_to(workloc)
        TestProcess.rsrc.fillColor = 'red'
        
        currentColor = entity.fillColor
        entity.fillColor = 'red'
        self.wait_for(self.waitTime)
        self.release(rsrcAssignment)
        entity.fillColor = currentColor
        TestProcess.rsrc.fillColor = None # default
        
        entity.move_to(sink)

def entityGenerator(source):
    while True:
        process = TestProcess()
        yield SimEntity(source, process) 
        
class TestSource(SimEntitySource):
    def __init__(self, name, locationObj=None, animationObj=None, **properties):
        super().__init__(name, locationObj, animationObj, **properties)
        print("*** creating TestSource:", self)
        
        
    def staticInitialize(self):
        self.add_entity_generator(SimEntity, TestProcess, 
                                  SimDistribution.exponential, SimTime(10), 1)
        #iaGenerator = SimDistribution.numberGenerator(SimDistribution.exponential, SimTime(10), 1)
        #wiGenerator = entityGenerator(self)
        #self.addGeneratorPair(wiGenerator, iaGenerator)
   
# TODO really need a model-level initialize to reset this before each run  
waitTimeGenerator = [None] * 6
waitTimeGenerator[1] = SimDistribution.number_generator(SimDistribution.exponential, SimTime(9), 1)
waitTimeGenerator[2] = SimDistribution.number_generator(SimDistribution.exponential, SimTime(7), 2)
waitTimeGenerator[3] = SimDistribution.number_generator(SimDistribution.exponential, SimTime(8), 3)
waitTimeGenerator[4] = SimDistribution.number_generator(SimDistribution.exponential, SimTime(8), 4)
waitTimeGenerator[5] = SimDistribution.number_generator(SimDistribution.exponential, SimTime(4), 5)

class TestProcessBase(SimProcess):
    def __init__(self, workSequence, entityColor):
        super().__init__()
        self.entityColor = entityColor
        self.queueName = []
        self.worklocName = []
        self.rsrcName = []
        self.waitTime = []
        for i in workSequence:
            self.queueName.append("Queue" + str(i))
            self.worklocName.append("WorkLocation" + str(i))
            self.rsrcName.append("Resource" + str(i))
            self.waitTime.append(next(waitTimeGenerator[i]))
        
    def run(self):
        sink = SimEntitySink("Sink")
        entity = self.entity
        entity.fillColor = self.entityColor
        for i in range(len(self.waitTime)):         
            queue = SimLocation(self.queueName[i])
            workloc = SimLocation(self.worklocName[i])
            rsrc = SimSimpleResource(self.rsrcName[i])
            
            entity.move_to(queue)        
            rsrcAssignment = self.acquire(rsrc)
            entity.move_to(workloc)     
            currentColor = entity.fillColor
            entity.fillColor = 'red'
            self.wait_for(self.waitTime[i])
            rsrcAssignment.release()
            entity.fillColor = currentColor
            #TestProcess.rsrc.color = 'white'
        
        entity.move_to(sink)
        
class TestProcess1(TestProcessBase):
    def __init__(self):
        super().__init__((1,3,5), 'blue')
        
        
class TestProcess2(TestProcessBase):
    def __init__(self):
        super().__init__((2,4,5), 'green')
