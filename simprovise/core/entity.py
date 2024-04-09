#===============================================================================
# MODULE entity
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimEntityElement and SimEntity classes.
#===============================================================================
__all__ = ['SimEntity']

from simprovise.core import SimClock, SimTime, SimCounter, SimUnweightedDataCollector
from simprovise.core.simelement import SimClassElement
from simprovise.core.simobject import SimTransientObject
from simprovise.core.apidoc import apidoc, apidocskip

from simprovise.core import SimLogging, SimError
logger = SimLogging.get_logger(__name__)

_ERROR_NAME = "SimEntityError"
        
@apidoc
class SimEntity(SimTransientObject):
    """
    A SimEntity is a (transient) unit of work as processed during the run of
    a simulation model.

    Args:
        source (SimEntitySource): The source that created this entity
        process (SimProcess):     The process that will be run on behalf of
                                  this entity
        properties:               Keyword arguments defining additional
                                  SimEntity subclass properties, if any.
    """
    __slots__ = ('__source', '__process', '__element', '__processElement',
                 '__createTime', '__destroyTime')
    
    elements = {}
    
    def __init_subclass__(cls, **kwargs):      
        """
        Register all subclasses of SimEntity by wrapping them in a
        SimEntityElement and adding it to SimEntity.elements.
        
        Also initializes the elements list with the SimEntity class
        itself, since models can create SimEntity objects directly.
        
        Pretty much straight from the PEP 487 document
        https://peps.python.org/pep-0487/#subclass-registration
       """
        super().__init_subclass__(**kwargs)
        
        # make sure the base SimEntity class is in the elements dictionary
        if not cls.elements:
            e = SimEntityElement(SimEntity) 
            cls.elements[e.element_id] = e
            
        # Add a process element to the SimProcess elements dictionary
        e = SimEntityElement(cls) 
        if e.element_id in cls.elements:
            msg = "SimEntity class with element ID {0} is already registered"
            raise SimError(_ERROR_NAME, msg, e.element_id)
              
        logger.info("Creating and registering an entity element for %s", e.element_id)
        cls.elements[e.element_id] = e

    @classmethod
    def final_initialize(cls):
        """
        final_initialize() is used to do any :class:`SimEntity`-derived
        class (not instance) member initialization that can't be done when the 
        class's module is imported. This method will be called for each
        SimEntity-derived class IF AND ONLY IF the method is defined
        for that derived class; it will be called at the same time that
        final_initialize() is called on all :class:`SimStaticObject`
        objects in the model - after all simulation elements are created,
        after the simulation clock, random number streams and event processor
        are created/initialized, but before the simulation execution actually
        starts.
            
        While a no-op final_initialize() is defined for :class:`SimEntity`,
        It is not necessary to do so for subclasses that need no final
        initialization processing. If the method is not defined on a subclass,
        final_initialize() will not be called. (The calling code makes sure
        not to call any implementation inherited from a base class)
        
        Client code should not call this method.
        """
        pass
            
    def __init__(self, source, process):
        super().__init__(source)
        import simprovise.core.process
        assert isinstance(process, simprovise.core.process.SimProcess), "Process passed to SimEntity is not derived from SimProcess"
        self.__source = source
        self.__process = process
        self.__createTime = SimClock.now()
        self.__destroyTime = None
        
        def get_element(cls):
            "Helper method for getting an Entity or Process SimElement"
            try:
                return cls.element
            except AttributeError:
                return None
                
        
        # Determine the entity's corresponding SimEntityElement, if any
        self.__element = get_element(self.__class__)

        # link the entity to it's process and process element, if any
        process.entity = self
        
        # increment the work-in-process counter if we have an element
        if self.element:
            self.element.counter.increment()
            
    @apidocskip
    def destroy(self):
        """
        Mark the entity as destroyed, updating entity counter and
        data collector accordingly
        """
        assert not self.__destroyTime, "Entity is already destroyed"
        self.__destroyTime = SimClock.now()
        if self.element:
            self.element.counter.decrement()
            self.element.timeDataCollector.add_value(self.process_time)            

    @property
    def source(self):
        """
        The source that generated this entity.

        Returns:
            SimEntitySource: The source that generated this entity
        """
        return self.__source

    @property
    def process(self):
        """
        The process that is to be (or is being) executed on behalf of this
        entity.

        Returns:
            SimProcess: The entity's process
        """
        return self.__process

    @property
    def element(self):
        """
        Returns the SimEntityElement associated with this entity's class,
        if any. It may be the element for a base class

        :return: The SimEntityElement associated with this entity's class,
                 or None 
        :rtype:  :class:`SimEntityElement` or None
        """
        return self.__element

    @property
    def create_time(self):
        """
       The simulated time when this entity was created.

        Returns:
             SimTime: The simulated time when this entity was created
        """
        return self.__createTime

    @property
    def destroy_time(self):
        """
        The simulated time when this entity was destroyed (upon reaching its
        SimEntitySink), or None if the entity is still in process

        Returns:
            SimTime: The simulated time when this entity was destroyed
        """
        return self.__destroyTime

    @property
    def process_time(self):
        """
        The simulated time that this entity has been (or was) in process; so
        if the entity is still in-process, it is the simulated time since the
        entity was created.

        Returns:
            SimTime: The entity's process time
        """
        if self.destroy_time:
            return self.destroy_time - self.create_time
        else:
            return SimClock.now() - self.create_time

class SimEntityElement(SimClassElement):
    """
    SimEntityElement instances represent an entire entity class as an element
    for data collection purposes, since these data are aggregated by class,
    rather than individual entity instances. To put in another way, we create
    one SimEntityElement instance for each :class:`SimEntity` subclass for which
    we want to collect data. Modeling code should specify the SimProcess-derived
    classes to create elements for by wrapping them via the
    :func:`simelement` decorator. :class:`SimEntity` itself is wrapped by
    default, since SimEntities may be instantiated directly. Analagous to
    :class:`SimProcessElement`.
    
    :param entityclass: The :class:`SimEntity` class or subclass for
                        which this :class:`SimElement` is a proxy.
    :type entityclass:  Class (NOT an instance of the class)
    """
    
    __slots__ = ('counter', 'timeDataCollector')
    
    def __init__(self, entityclass):
        """
        Create and initialize a SimEntityElement with a passed :class`SimEntity`.
        There should be one SimEntityElement for every SimEntity class or
        subclass in the simulation model.
        
        Also creates
        a :class:`SimCounter` for work-in-process :class: entities <SimEntity>
        and an :class: `unweighted data collector <SimUnweightedDataCollector>`
        for process times; both of these objects create and register
        :class:`datasets <Dataset>` with the SimEntityElement.
        """
        assert issubclass(entityclass, SimEntity)
        super().__init__(entityclass)
        self.counter = SimCounter(self, "Work-In-Process")
        self.timeDataCollector = SimUnweightedDataCollector(self, "Process-Time", SimTime)

if __name__ == '__main__':
    
    class MockEntity(SimEntity):
        """
        """
        
    for e in SimEntity.elements:
        print(e.element_id)

        