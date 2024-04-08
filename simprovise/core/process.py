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
        cls._classInitialized = False

    @classmethod
    @apidocskip
    def get_simelement(cls):
        """
        Return the SimProcessElement associated with this class.
        If the model has not created a SimProcessElement for this specific
        class (by wrapping the class definition with the simelement decorator),
        look up the class hierarchy to see if a base SimProcess class has
        an element - if so, return that instead. If this class and none of it's
        SimProcess base classes has an element, return None.
        """
        try:
            return cls.element
        except AttributeError:
            if cls is SimProcess:
                return None
            else:
                for baseclass in cls.__bases__:
                    if issubclass(baseclass, SimProcess):
                        return SimProcess.get_simelement(baseclass)
    
    @classmethod
    @apidocskip
    def _class_initialized(cls):
        """
        Initialize any class members for the process (typically counters and
        references to static objects), so should be invoked after model static
        initialization - we actually initialize lazily as process classes are
        instantiated for the first time during a simulation run). Should be
        implemented by SimProcess subclasses as required.
        """
        return cls._classInitialized
        #if hasattr(cls, 'classInitialized') and cls.classInitialized:
            #return True
        #else:
            #return False

    @classmethod
    @apidocskip
    def initialize_class_data(cls):
        """
        Initialize any class members for the process (typically references
        to static objects), so should be invoked after model static
        initialization - we actually initialize lazily as process classes are
        instantiated for the first time during a simulation run). Should be
        implemented by SimProcess subclasses as required.
        """
        pass

    @classmethod
    def _initialize_class_and_super_class_data(cls):
        """
        If this class's initializeClassData() has not been invoked,
        recursively check/initialize superclasses, and then initialize
        data for this class.
        """
        if not cls._classInitialized:
            for base in cls.__bases__:
                if base is not SimProcess and issubclass(base, SimProcess):
                    # pylint can't grok fact that this may be called on a
                    # SimProcess subclass
                    # pylint: disable=E1101
                    base._initialize_class_and_super_class_data()
            logger.info("Initializing class data for class %s", cls.__name__)
            cls.initialize_class_data()
            cls._classInitialized = True

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

