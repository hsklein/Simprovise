#===============================================================================
# MODULE simelement
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimElement and SimClassElement classes.
#===============================================================================
from simprovise.core import (SimClock, SimTime,
                             SimError, SimCounter, SimUnweightedDataCollector,
                             SimLogging)
from simprovise.core.apidoc import apidoc, apidocskip

# This constant is accessed by other methods
ENTRIES_DATASET_NAME = "Entries"

_SIMELEMENT_ERROR_NAME = "SimElementError"

logger = SimLogging.getLogger(__name__)

@apidoc
class SimElement(object):   
    """
    SimElement is base class for objects that are elements in the 
    simulation model. These elements include static simulation objects -
    :class:`Locations <SimLocation>`, :class:`Resources <SimResource>`,
    :class:`Entity Sources <SimEntitySource>` and
    :class:`Entity Sinks <SimEntitySink>` (and their subclasses), as well as
    :class:`SimProcessElements <SimProcessElement>` and
    :class:`SimEntityElements <SimEntityElement>`, which are static proxies for
    transient process and entity objects.
    
    SimElements exist for the lifetime of the simulation, and should be 
    registered with the :class:`SimModel` singleton. The cleanest solution would 
    be to do that registration in SimElement.__init__, but registration requires 
    the fixed, unique ID (element_id) for the element, which is based on data in 
    derived classes. We rely on :class:`SimClassElement` and
    :class:`SimStaticObject` to register new instances in their confirm
    via a call to :meth:`_register`
    
    SimElements are the base unit for data collected during a simulation.
    SimElement maintains the collection of :class:`datasets <Dataset>`
    associated with the element, and provides methods/properties to define
    and access them.
    
    SimElement is basically an abstract base class, but we don't
    define it as such since it is a mixin class for SimStaticObject,
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
        :return: A globally unique identifier for the element
        :rtype: String
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
    
    @property
    def full_class_name(self):
        """
        Returns the fully-qualified (module + class) name of the
        element_class.
        """
        cls = self.element_class
        return cls.__module__ + '.' + cls.__qualname__
        
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
