#===============================================================================
# MODULE entity
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimEntityElement and SimEntity classes.
#===============================================================================
__all__ = ['SimEntity']

import itertools
from simprovise.core import SimError
from simprovise.core.simclock import SimClock
from simprovise.core.simlogging import SimLogging
from simprovise.core.simtime import SimTime, Unit as tu
from simprovise.core.simelement import SimClassElement
from simprovise.core.datacollector import SimUnweightedDataCollector
from simprovise.core.model import SimModel
from simprovise.modeling import SimCounter
from simprovise.modeling.simobject import SimTransientObject
from simprovise.core.apidoc import apidoc, apidocskip

logger = SimLogging.get_logger(__name__)

_ERROR_NAME = "SimEntityError"

_entity_count = itertools.count(1)
        
@apidoc
class SimEntity(SimTransientObject):
    """
    A SimEntity is a (transient) unit of work that flows through the
    model during a simulation run. Customers, for example, are usually
    represented as entities.

    :param source:  The source that created this entity
    :type source:   :class:`~.entitysource.SimEntitySource`
     
    :param process: The process that will be run on behalf of this entity
    :type process:  :class:`~.process.SimProcess`

    """
    __slots__ = ('__source', '__process', '__element', '__processElement',
                 '__createTime', '__destroyTime', '_id')
    
    
    @staticmethod
    def _init_baseclass():
        """
        Put the base SimEntity class in the elements dictionary.
        """
        #x = len(SimModel.model().entity_elements)
        #if not SimModel.model().entity_elements:
        e = SimEntityElement(SimEntity) 
        SimModel.model()._register_entityElement(e)
    
    def __init_subclass__(cls, **kwargs):      
        """
        Register all subclasses of SimEntity by wrapping them in a
        SimEntityElement and adding it to SimEntity.elements.
       
        Pretty much straight from the PEP 487 document
        https://peps.python.org/pep-0487/#subclass-registration
       """
        super().__init_subclass__(**kwargs)
                    
        # Add an entity element to the SimModel registry
        e = SimEntityElement(cls) 
        logger.info("Creating and registering an entity element for %s", e.element_id)
        SimModel.model()._register_entityElement(e)

    @classmethod
    def final_initialize(cls):
        """
        final_initialize() is used to do any :class:`SimEntity`-derived
        class (not instance) member initialization that can't be done when the 
        class's module is imported. This method will be called for each
        SimEntity-derived class IF AND ONLY IF the method is defined
        for that derived class; it will be called at the same time that
        final_initialize() is called on all :class:`~.simelement.SimElement`
        objects in the model - after all simulation elements are created,
        after the simulation clock, random number streams and event processor
        are created/initialized, but before the simulation execution actually
        starts.
        
        Every SimEntity-derived class that is imported into the model will
        have a corresponding :class:`SimEntityElement` created and placed
        into the model, regardless of whether or not any objects of that
        SimEntity-derived class are created. The SimEntityElement will
        call the corresponding :class:`SimEntity` class's final_initialize(),
        if it is defined. If the method is not defined on a subclass,
        final_initialize() will not be called. (The calling code makes sure
        not to call any implementation inherited from a base class)
            
        While a no-op final_initialize() is defined for :class:`SimEntity`,
        It is not necessary to do so for subclasses that need no final
        initialization processing. 
        
        Client code can implement final_initialize() on custom
        SimEntity-derived classes, but should not call this method
        directly.
        
        """
        pass
            
    def __init__(self, source, process):
        super().__init__(source)
        import simprovise.modeling.process
        assert isinstance(process, simprovise.modeling.process.SimProcess), "Process passed to SimEntity is not derived from SimProcess"
        self.__source = source
        self.__process = process
        self.__createTime = SimClock.now()
        self.__destroyTime = None
        self._id = next(_entity_count)
               
        # Determine the entity's corresponding SimEntityElement, if any
        self.__element = self.__class__.element
        assert  self.__element, "entity class has no element"

        # link the entity to it's process and process element, if any
        process.entity = self
        
        # increment the element's work-in-process counter 
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
        
        :return: The source that generated this entity.
        :rtype:  :class:`~.entitysource.SimEntitySource`

        """
        return self.__source

    @property
    def process(self):
        """
        
        :return: The process that is to be (or is being) executed on
                 behalf of this :class:`SimEntity`.
        :rtype:  :class:`~.process.SimProcess`
        
       """
        return self.__process

    @property
    def element(self):
        """
        :return: The SimEntityElement associated with this entity's class.
        :rtype:  :class:`SimEntityElement`
        
        """
        return self.__element

    @property
    def create_time(self):
        """
        
        :return: The simulated time when this entity was created.
        :rtype:  :class:`~.simtime.SimTime`
        
        """
        return self.__createTime

    @property
    def destroy_time(self):
        """
        :return: The simulated time when this entity was destroyed (upon
                 reaching its :class:`~.entitysink.SimEntitySink`), or
                 None if the entity is still in process
        :rtype:  :class:`~.simtime.SimTime`

        """
        return self.__destroyTime

    @property
    def process_time(self):
        """
        
        :return: The simulated time that this entity has been (or was)
                 in process; if the entity is still in-process, it is the
                 simulated time since the entity was created.
        :rtype:  :class:`~.simtime.SimTime`
       
        """
        if self.destroy_time:
            return self.destroy_time - self.create_time
        else:
            return SimClock.now() - self.create_time
        
    def __str__(self):
        return "{0} {1}".format(self.__class__.__name__, self._id)

class SimEntityElement(SimClassElement):
    """
    SimEntityElement instances represent an entire entity class as an element
    for data collection purposes, since these data are aggregated by class,
    rather than individual entity instances. To put in another way, we create
    one SimEntityElement instance for each :class:`SimEntity` subclass in
    the model. SimEntityElements are automatically created and registered
    for class :class:`SimEntity`and every SimEntity-derived class imported
    into the model; client code should not create SimEntityElement objects
    directly; nor should client code subclass SimEntityElement.
    
    By default, SimEntityElements include a counter that collects
    work-in-process data for the corresponding entity class as well
    as a data collector collecting process time for entities of that
    class; these data aare collected as "Work-In-Process" and
    "Process-Time" datasets, respectively. Client code can, add
    additional :class:`~.counter.SimCounter`s and/or
    :class:`~.datacollector.SimDataCollector` objects to a
    SimEntityElement if the collection of additional custom datasets
    is desired.
    
    TODO define/illustrate how this is done
    
    Analagous to :class:`~.process.SimProcessElement`.
    
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

# Create a SimEntityElement for base class SimEntity
SimEntity._init_baseclass()

if __name__ == '__main__':
    
    class MockEntity(SimEntity):
        """
        """
        
    for e in SimModel.model().entity_elements:
        print(e.element_id, e.element_class, e.element_class.element)

        