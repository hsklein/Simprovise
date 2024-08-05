#===============================================================================
# MODULE simelement
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimElement and SimClassElement classes.
#
# This program is free software: you can redistribute it and/or modify it under 
# the terms of the GNU General Public License as published by the Free Software 
# Foundation, either version 3 of the License, or (at your option) any later 
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT 
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#===============================================================================
from simprovise.core import SimError
from simprovise.core.simlogging import SimLogging
import simprovise.core.configuration as simconfig
from simprovise.core.apidoc import apidoc, apidocskip

# This constant is accessed by other methods
ENTRIES_DATASET_NAME = "Entries"

_SIMELEMENT_ERROR_NAME = "SimElementError"

logger = SimLogging.get_logger(__name__)

@apidoc
class SimElement(object):   
    """
    SimElement is the base class for objects that are elements in the 
    simulation model. These elements include static simulation objects -
    :class:`Locations <.modeling.location.SimLocation>`,
    :class:`Resources <.modeling.resource.SimResource>`,
    :class:`Entity Sources <.modeling.entitysource.SimEntitySource>` and
    :class:`Entity Sinks <.modeling.entitysink.SimEntitySink>` (and their subclasses),
    as well as :class:`SimProcessElements <.modeling.process.SimProcessElement>` and
    :class:`SimEntityElements <.modeling.entity.SimEntityElement>`, which are static
    proxies for transient process and entity objects.
    
    SimElements exist for the lifetime of the simulation, and are 
    registered on initialization with the :class:`~.model.SimModel`
    singleton.
    
    SimElements are the base unit for data collected during a simulation.
    Each SimElement maintains a collection of
    :class:`datasets <.datacollector.Dataset>` associated with the element,
    and provides methods/properties to define and access them.
    
    SimElement is basically an abstract base class, but we don't
    define it as such since it is also a mixin class for
    :class:`~.simobject.SimStaticObject`, and we'd rather not deal with
    metaclass conflicts.
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
        :return: A globally unique identifier for the element.        
        :rtype: `str`       
        """
        # Basically an abstract property implemented by subclasses.
        pass
    
    @property
    def element_class(self):
        
        """
        Another abstract property implemented by subclasses.
        
        :return: For :class:`~.entity.SimEntityElement` and
                 :class:`~.process.SimProcessElement` objects, returns
                 the corresponding class:`~.entity.SimEntity` or
                 :class:`~.process.SimProcess` subclass; for
                 :class:`SimStaticObjects <.simobject.SimStaticObject>`,
                 returns the object's class.
        :rtype:  `class`
        
        """
        pass
    
    @staticmethod
    def get_full_class_name(cls):
        """
        Convenience method for code that needs to obtain a specific
        Entity or Process Element from the :class:`~.model.SimModel`;
        the element ID for those objects is the module + class
        names.
        
        Note that a module name of '__mp_main__' is translated to
        '__main__'. That ensures that a elements for entity or
        process classes defined in a model script get the same ID
        if  the model script is then imported by a separate process
        created by multiprocessing.Pool.
        (See https://stackoverflow.com/questions/72497140/in-python-multiprocessing-why-is-child-process-name-mp-main-is-there-a-way)
               
        :param cls: The Python class to query
        :type cls:  `class`
        
        :return: The fully-qualified (module + class) name of the
                 passed cls. 
        :rtype:  `str`
        
        """
        modulename = cls.__module__
        if modulename == '__mp_main__':
            modulename = '__main__'
        return modulename + '.' + cls.__qualname__        
    
    @property
    def full_class_name(self):
        """
        :return: The fully-qualified (module + class) name of the
                 elements :meth:`element_class`.
        :rtype:  `str`
        
        """
        return SimElement.get_full_class_name(self.element_class)
        
    @property
    def datasets(self):      
        """
        Abstract property implemented by subclasses :class:`SimClassElement`
        and :class:`~.simobject.SimStaticObject`.
        
        Returns a sequence of all of the :class:`datasets <Dataset>` for
        this element. Note that datasets are essentially a specification
        of a data stream to be collected during a simulation run, not the 
        data themselves.
        
        :return: The SimElements dataset list
        :rtype:  list
        """
        pass
    
    def register_dataset(self, dataset):
        """
        Add the passed dataset to the list of datasets for this element (if
        it's not already there). If it is there, this is a no-op.
        
        :meth:`register_dataset` is called bySimprovise-defined
        :class:`SimElement` subclasses; client (model-specific) code
        generally should not need to call this method.
        
        :param dataset: The dataset (data stream specification)
                        to add to the SimElement
        :type dataset: :class:`~.datacollector.Dataset`
        
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
                
        :class:`~.process.SimProcessElement` and
        :class:`~.entity.SimEntityElement` objects
        call final_initialize() class methods on their respective 
        :class:`~.process.SimProcess` or :class:`~.entity.SimEntity`-derived
        classes; model-defined process or entity subclasses can define
        final_initialize() when they need to initialize class member data
        at that point just before the simulation execution starts.
        """
        pass
    
    def disable_data_collection(self):
        """
        Abstract method implemented by subclasses :class:`SimClassElement`
        and :class:`~.simobject.SimStaticObject` to disable data collection
        for this element.
        """
        pass
    
    @property
    def data_collection_enabled(self):
        """
        Abstract property implemented by subclasses :class:`SimClassElement`
        and :class:`~.simobject.SimStaticObject`.
        
        :return: ``True`` if data collection is enabled for this element
        :rtype:  ``bool``
        """
        pass
    
    def __str__(self):
        return self.element_id


class SimClassElement(SimElement):   
    """
    Base class for elements representing transient simulation objects;
    it is the base class for :class:`~.process.SimProcessElement`
    and :class:`~.entity.SimEntityElement`. While not formally abstract,
    it is not meant to be instantiated directly.
    
    :param simclass: The :class:`~.process.SimProcess` or
                     :class:`~.entity.SimEntity` class or subclass for
                     which this :class:`SimElement` is a proxy.
    :type simclass:  Class (NOT an instance of the class)
    
    """
    __slots__ = ('_simclass', '_datasets', '_dataCollectionEnabled')
    def __init__(self, simclass):
        """
        """
        super().__init__()
        self._simclass = simclass
        simclass.element = self
        self._datasets = []
        self._dataCollectionEnabled = True
        
        # Check to see if data collection is disabled via configuration
        if simconfig.get_element_data_collection_disabled(self.element_id):
            self.disable_data_collection()
        
    @property
    def element_id(self):
        """
        For class elements, the ``element_id`` is the fully-qualified name
        of the (entity or process) class for which the element is a proxy.
        
        :return: The fully qualified class name (including package)
        :rtype:  `str`
        """
        return self.full_class_name
    
    @property
    def element_class(self):
        
        """
        Implements :meth`element_class` by returning the underlying
        simulation class
        """
        return self._simclass
        
    @property
    def datasets(self):      
        """
        Return a list of all of the :class:`datasets
        <.datacollector.Dataset>` for this element. Note that datasets
        are essentially a specification of a data stream to be
        collected during a simulation run, not the data themselves.
        
        :return: the SimElements dataset list
        :rtype:  `list`
        
        """
        return self._datasets
    
    def disable_data_collection(self):
        """
        Disable data collection for this element.
        """
        logger.info("Disabling data collection for class element %s",
                    self.element_id)
        self._dataCollectionEnabled = False
    
    @property
    def data_collection_enabled(self):
        """
        :return: ``True`` if data collection is enabled for this element
        :rtype:  ``bool``
        """
        return self._dataCollectionEnabled    
                  
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
                logger.warn("Class %s has a non-callable final_initialize member",
                            cls)
 