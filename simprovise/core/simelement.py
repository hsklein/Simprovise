#===============================================================================
# MODULE simelement
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimElement and SimClassElement classes.
#===============================================================================
from simprovise.core import SimError, SimLogging
from simprovise.core.apidoc import apidoc, apidocskip

# This constant is accessed by other methods
ENTRIES_DATASET_NAME = "Entries"

_SIMELEMENT_ERROR_NAME = "SimElementError"

logger = SimLogging.get_logger(__name__)

@apidoc
class SimElement(object):   
    """
    SimElement is base class for objects that are elements in the 
    simulation model. These elements include static simulation objects -
    :class:`Locations <.location.SimLocation>`,
    :class:`Resources <.resource.SimResource>`,
    :class:`Entity Sources <.entitysource.SimEntitySource>` and
    :class:`Entity Sinks <.entitysink.SimEntitySink>` (and their subclasses),
    as well as :class:`SimProcessElements <.process.SimProcessElement>` and
    :class:`SimEntityElements <.entity.SimEntityElement>`, which are static
    proxies for transient process and entity objects.
    
    SimElements exist for the lifetime of the simulation, and are 
    registered on initialization with the :class:`~.model.SimModel` singleton.
    
    SimElements are the base unit for data collected during a simulation. Each
    SimElement maintains a collection of :class:`datasets <.datacollector.Dataset>`
    associated with the element, and provides methods/properties to define
    and access them.
    
    SimElement is basically an abstract base class, but we don't
    define it as such since it is also a mixin class for SimStaticObject,
    and we'd rather not deal with metaclass conflicts.
    """
    # Since this is a mixin class for SimStaticObject, we don't define an
    # initializer and don't have any data members. Plus, for that reason we do
    # NOT use __slots__. The other SimStaticObject base class, SimLocatable, 
    # does. Inheriting from two or more classes with __slots__ defined results 
    # in a TypeError - multiple bases have instance lay-out conflict (at least
    # in Python 3.12)

    @property
    def element_id(self):
        """
        Basically an abstract property implemented by subclasses.
        :return: A globally unique identifier for the element.
        
        :rtype: str
        
        """
        pass
    
    @property
    def element_class(self):
        
        """
        Another abstract property implmented by subclasses. For
        SimEntityElements and SimProcessElements, returns the underlying
        SimEntity or SimProcess class; for SimStaticObjects, returns
        the object class.
        """
        pass
    
    @staticmethod
    def get_full_class_name(cls):
        """
        Returns the fully-qualified (module + class) name of the passed
        class. Convenience method for code that needs to obtain a
        specific Entity or Process Element from the SimModel.
        """
        return cls.__module__ + '.' + cls.__qualname__        
    
    @property
    def full_class_name(self):
        """
        Returns the fully-qualified (module + class) name of the
        element_class.
        """
        return SimElement.get_full_class_name(self.element_class)
        
    @property
    def datasets(self):      
        """
        Abstract property implemented by subclasses :class:`SimClassElement`
        and :class:`SimStaticObject`.
        Returns a sequence of all of the :class:`datasets <Dataset>` for
        this element. Note that datasets are essentially a specification
        of a data stream to be collected during a simulation run, not the 
        data themselves.
        
        :return: The SimElements dataset list
        :rtype: List
        """
        pass
    
    def register_dataset(self, dataset):
        """
        Add the passed dataset to the list of datasets for this element (if
        it's not already there). If it is there, this is a no-op.
        
        :param dataset: The dataset (data stream specification)
                        to add to the SimElement
        :type dataset: :class:`Dataset`
        """
        if dataset not in self.datasets:
            self._datasets.append(dataset)
          
    @apidocskip
    def final_initialize(self):
        """
        Do any initialization that must occur after the entire model is 
        loaded and the core simulation infrastructure (random number
        streams, simulation clock and event processor) are initialized.
        
        SimEntitySource is the only core static object class that requires
        this sort of initialization - it generates the initial entity creation
        events (which won't work until after the event process is created).
                
        :class:`SimProcessElement` and :class:`SimEntityElement` objects
        call final_initialize() class methods on their respective 
        :class:`SimProcess` or :class:`SimEntity`-derived classes;
        model-defined process or entity subclasses can define
        final_initialize() when they need to initialize class member data
        at that point just before the simulation execution starts.
        """
        pass


class SimClassElement(SimElement):   
    """
    Base class for elements representing transient simulation objects
    it is the base class for :class:`SimProcessElement`SimProcessElement
    and :class:`SimEntityElement`. While not formally abstract, it
    is not meant to be instantiated directly.
    
    :param simclass: The :class:`SimProcess` or :class:`SimEntity` class
                     or subclass for which this :class:`SimElement` is:return
                     a proxy.
    :type simclass:  Class (NOT an instance of the class)
    """
    __slots__ = ('_simclass', '_datasets')
    def __init__(self, simclass):
        """
        Constructor registers the element
        """
        super().__init__()
        self._simclass = simclass
        simclass.element = self
        self._datasets = []
        
    @property
    def element_id(self):
        """
        :return: The fully qualified class name (including package)
        :rtype: String
        """
        return self.full_class_name
    
    @property
    def element_class(self):
        
        """
        Implements element_class() by returning the underlying
        simulation class
        """
        return self._simclass
        
    @property
    def datasets(self):      
        """
        Return a list of all of the :class:`datasets <Dataset>` for
        this element. Note that datasets are essentially a specification
        of a data stream to be collected during a simulation run, not the 
        data themselves.
        
        :return: the SImElements dataset list
        :rtype: List
        """
        return self._datasets
          
    @apidocskip
    def final_initialize(self):
        """
        Do any initialization that must occur after the entire model is loaded
        and the core simulation infrastructure (random number streams,
        simulation clock and event processor) are initialized.
        
        In this case, we are using SimClassElements (:class:`SimProcessElement`
        and :class:`SimEntityElement`) to do final initialization, if any,
        for the process and entity classes that they wrap, by determining
        if there is a final_initialize() classmethod defined for that process
        or entity class and calling it if there is.
        
        Note that we do NOT want to invoke a final_initialize() that is
        inherited from a base class, since that base class should already
        have it's own corresponding SimClassElement. That's why we check
        the class's __dict__ attribute for a member keyed by that method
        name.        

        """
        cls = self.element_class
        if 'final_initialize' in cls.__dict__:
            try:
                logger.info("Invoking final_initialize() on class %s", cls)
                cls.final_initialize()
            except TypeError:
                # The class has an attribute named 'final_initialize that's
                # not callable. Not a great idea, but we'll just eat the
                # resulting exception with a warning
                logger.warn("Class %s has a non-callable final_initialize member", cls)
 