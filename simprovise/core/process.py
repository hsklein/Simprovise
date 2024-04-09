#===============================================================================
# MODULE process
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimProcess and SimProcessElement classes.
#===============================================================================
__all__ = ['SimProcess']

from simprovise.core.transaction import SimTransaction
from simprovise.core.simelement import SimClassElement 
from simprovise.core.apidoc import apidoc, apidocskip

from simprovise.core import SimEntity, SimCounter, SimTime, SimUnweightedDataCollector
from simprovise.core import SimLogging, SimError
logger = SimLogging.getLogger(__name__)

_ERROR_NAME = "SimProcessError"
        
@apidoc
class SimProcess(SimTransaction):
    """
    SimProcess is a subclass of SimTransaction, where entities are the agents.
    As such it is the base class for all simulation processes.
    """
    __slots__ = ('__executing', '__entity', '__resourceAssignments')
    
    elements = {}
    
    def __init_subclass__(cls, **kwargs):      
        """
        Register all subclasses of SimProcess by wrapping them in a
        SimProcessElement and adding it to the SimProcess.elements list.
        
        Pretty much straight from the PEP 487 document
        https://peps.python.org/pep-0487/#subclass-registration.
        
        Note models should only use SimProcess subclasses, so no need
        to add SimProcess itself to this list.
        """
        super().__init_subclass__(**kwargs)
        
        # Add a process element to the SimProcess elements dictionary
        pe = SimProcessElement(cls) 
        if pe.element_id in cls.elements:
            msg = "SimProcess class with element ID {0} is already registered"
            raise SimError(_ERROR_NAME, msg, pe.element_id)
              
        logger.info("Creating and registering a process element for %s", pe.element_id)
        cls.elements[pe.element_id] = pe

    @classmethod
    def final_initialize(cls):
        """
        final_initialize() is used to do any :class:`SimProcess`-derived
        class (not instance) member initialization that can't be done when the 
        class's module is imported. This method will be called for each
        SimProcess-derived class IF AND ONLY IF the method is defined
        for that derived class; it will be called at the same time that
        final_initialize() is called on all :class:`SimStaticObject`
        objects in the model - after all simulation elements are created,
        after the simulation clock, random number streams and event processor
        are created/initialized, but before the simulation execution actually
        starts.
        
        While a no-op final_initialize() is defined for :class:`SimProcess`,
        It is not necessary to do so for subclasses that need no final
        initialization processing. If the method is not defined on a subclass,
        final_initialize() will not be called. (The calling code makes sure
        not to call any implementation inherited from a base class)
        
        Client code should not call this method.
        """
        pass

    def __init__(self):
        """
        Initialize the process with a null agent. The entity itself will set
        itself as the process's agent when the entity is instantiated.
        """
        super().__init__(None)
        self.__executing = False
        self.__entity = None
        self.__resourceAssignments = []
        self._initialize_class_and_super_class_data()

    @property
    def entity(self):
        """
        The SimEntity (agent) being processed by this SimProcess instance

        Returns:
            SimEntity: The entity associated with this process
        """
        return self.agent

    @entity.setter
    def entity(self, value):
        assert isinstance(value, SimEntity), "Attempt to set SimProcess.entity to an object of type " + str(type(value))
        self._agent = value

    def __str__(self):
        return self.__class__.__name__
    
class SimProcessElement(SimClassElement):
    """
    SimProcessElement instances represent an entire process class as an
    element for data collection purposes, since process data are aggregated
    by class, rather than individual executing process instances. To put in
    another way, we create one SimProcessElement instance for each
    :class:`SimProcess`-derived class in the model for which we want to
    collect data. Modeling code should specify the SimProcess-derived
    classes to create elements for by wrapping them via the
    :func:`simelement` decorator.
    
    Analagous to :class:`SimEntityElement`.
       
    :param processclass: The :class:`SimProcess` subclass for which this
                         :class:`SimElement` is a proxy.
    :type processclass:  Class (NOT an instance of the class)
    """
    
    __slots__ = ('counter', 'timeDataCollector')
    
    def __init__(self, processclass):
        """
        Create and initialize a SimProcessElement with a passed SimProcess.
        There should be one SimProcessElement for every process
        (SimProcess-derived) class in the simulation model. Also creates
        a :class:`SimCounter` for in-process :class: entities <SimEntity>
        and an :class: `unweighted data collector <SimUnweightedDataCollector>`
        for process times; both of these objects create and register
        :class:`datasets <Dataset>` with the SimProcessElement.
        """
        assert issubclass(processclass, SimProcess)
        super().__init__(processclass)
        self.counter = SimCounter(self, "In-Process")
        self.entryCounter = SimCounter(self, "Entries")
        self.timeDataCollector = SimUnweightedDataCollector(self, "Process-Time", SimTime)

    
if __name__ == '__main__':
    
    
    class MockProcess1(SimProcess):
        """
        """
        
    class MockProcess2(SimProcess):
        """
        """
        
    class MockProcess11(MockProcess1):
        """
        """
  
    for e in SimProcess.elements:
        print(e.element_id)

