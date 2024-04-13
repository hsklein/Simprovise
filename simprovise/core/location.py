#===============================================================================
# MODULE location
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines SimStaticObject and three core modeling classes derived from it:
#     - SimLocation
#     - SimRootLocation
#     - SimQueue
#===============================================================================
__all__ = ['SimLocation', 'SimRootLocation', 'SimQueue']

from simprovise.core import (SimClock, SimTime, simelement, 
                             SimError, SimCounter, SimUnweightedDataCollector,
                             SimLogging)

from simprovise.core.simobject import SimLocatableObject
from simprovise.core.simelement import SimElement
from simprovise.core.apidoc import apidoc, apidocskip

_STATICOBJ_ERROR_NAME = "SimStaticObjectError"
_LOCATION_ERROR_NAME = "SimLocationError"
_ENTRIES_DATASET_NAME = simelement.ENTRIES_DATASET_NAME
_ROOT_LOCATION_NAME = "Root"

logger = SimLogging.get_logger(__name__)


@apidoc
class SimStaticObject(SimLocatableObject, SimElement):
    """
    Base class for static (vs. transient) simulation objects. Locations,
    Resources, Sources and Sinks are all instances of SimStaticObject
    subclasses.

    Static objects are created before simulation starts and exist for the
    entire simulation run.
    
    Static objects are assigned to a parent location at creation, and maintain
    that assignment for the entire simulation.  They may move within their
    assigned parent location, but the value returned by the parent_location
    property does not change.

    Static objects have an element ID, which reflects the static object
    location hierarchy - e.g. "Parent.Child.GrandChild"
    """
    __slots__ = ('_name', '_parentlocation', '_datasets')
    
    elements = {}

    def __init__(self, elementName, parentLocation=None, initialLocation=None,  
                 moveable=False):
        if parentLocation is None:
            parentLocation = SimLocation.root_location()
            
        if initialLocation is None:
            initialLocation = parentLocation
            
        super().__init__(initialLocation, moveable)
        self._datasets = []
         
        assert isinstance(elementName, str), "Static Object element name must be a string"
        assert len(elementName.strip()), "Static Object element name not be blank or empty"
        assert elementName.find('.') == -1, "Static Object element name cannot contain '.'"
        
        
        # TODO confirm initialLocation is either the parent location or a
        # sublocation of the parent location
        self._name = elementName
        self._parentlocation = parentLocation
        
        # Add the new static object to the static object elements dictionary
        if self.element_id in SimStaticObject.elements:
            msg = "Static object with element ID {0} is already registered"
            raise SimError(_STATICOBJ_ERROR_NAME, msg, self.element_id)
        
        logger.info("Registering static object %s ...", self.element_id)
        SimStaticObject.elements[self.element_id] = self
        
        # Add the new static object to the parent location's collection of
        # children
        parentLocation._add_child(self)
        
    @property
    def datasets(self):      
        """
        Return a list of all of the :class:`datasets <Dataset>` for
        this element. Note that datasets are essentially a specification
        of a data stream to be collected during a simulation run, not the 
        data themselves.
        
        :return: the SimElements dataset list
        :rtype: List
        """
        return self._datasets
        
    @property
    def element_name(self):
        """
        The base (non-qualified with ancestor names) name of this static object
        """
        return self._name
        
    @property
    def element_id(self):
        """
        Implements the element_id property defined by SimElement.
        The fully-qualified element ID of this static object - the element
        name prepended  by the ancestor location names (not including the root)
        """
        if self.parent_location.is_root:
            return self.element_name
        else:
            return "".join((self.parent_location.element_id, '.', self.element_name))
           
    @property
    def element_class(self):
        
        """
        Implements element_class() by returning the static object's class
        """
        return self.__class__

    @property
    def parent_location(self):
        """
        Returns the SimLocation that owns this static object
        """
        assert self._parentlocation, "No parent location assigned to SimStaticObject"
        return self._parentlocation        
        
    @property
    def ancestor_locations(self):
        """
        Generator yielding the static object's ancestor locations, starting with
        it's parent location (and not including the root location)
        """
        ancestor = self.parent_location
        while not ancestor.is_root:
            yield ancestor
            ancestor = ancestor.parent_location
            
    @property
    def islocation(self):
        """
        Returns true if the object is a SimLocation or SimRootLocation
        """
        return isinstance(self, (SimLocation, SimRootLocation))
            
    @apidocskip
    def final_initialize(self):
        """
        Do any initialization that must occur after the entire model is loaded
        and the core simulation infrastructure (random number streams,
        simulation clock and event processor) are initialized.
        
        SimEntitySource is the only core static object class that requires
        this sort of initialization - it generates the initial entity creation
        events (which won't work until after the event process is created)
        """
        pass
        

@apidoc
class SimLocation(SimStaticObject):
    """
    Represents a generic location for simulation objects, for the purpose of
    gathering statistics, if nothing else. SimLocation tracks the
    (time-weighted) count of objects resident at the location, and the time
    spent (per object) in the location. SimLocations may be nested - a parent
    location may contain multiple child locations - e.g., a work area
    location might contain several workstations.

    :class:`SimLocatableObject` objects enter and leave SimLocations via the
    SimLocatable's :meth:`SimLocatableObject.move_to` method.
    :meth:`SimTransientObject.move_to` also invokes :meth:`on_enter` and/or
    :meth:`on_exit` methods on the SimLocation(s) involved.
    SimLocation.on_enter/on_exit generally should only be invoked by
    transient objects.

    Strictly speaking, :class:`SimLocatableObject` instances should only
    move to leaf locations within a SimLocation hierarchy. We do, however,
    want to facilitate the notion of hierarchical modeling - e.g., a entity
    moving from one area of the model to another might invoke
    ``move_to(area2)``, where ``area2`` is a root location containing multiple
    other sub-locations, and we want ``area2`` to define exactly where the
    entity should go. To do this, the area2 location defines an entry point,
    which should be a descendant location. Entry point locations are
    specified via partially-qualified element IDs. Entry points may be
    defined recursively (e.g. parent defines a child object as entry point;
    the actual entry point will be that child's entry point, which may be the
    child or may be a descendant of the child.)

    Args:
        name (str):            Name of the location, must be unique within
                               the location's parent (parentLocationObj)
        parentlocation (SimLocation): Location object to which this location
                               belongs. If None this location is assigned to
                               the Root location
        entryPointName (str):  Relative elementID of descendant location that
                               serves as the entry point for this location. If
                               this location is it's own entry point.
     """
    # TODO locations should be static objects?  Confirm that?
    __slots__ = ('_hasChildren', '_counter', '_entryDataCollector', '_timeDataCollector',
                 '_entryPointID', '_entrypointLocation', '_childStaticObjs',
                 '_residents')
    
    _rootlocation = None
    
    @classmethod
    def root_location(cls):
        """
        Class SimLocation manages the singleton root location instance.
        We initialize it lazily, primarily to ensure that the SimModel
        singleton instance is created first.
        TODO: Should we make SimModel explicitly initialize this itself?
        """
        if SimLocation._rootlocation is None:
            SimLocation._rootlocation = SimRootLocation()
        return SimLocation._rootlocation
        

    def __init__(self, name, parentlocation=None, entrypointname=None):
        super().__init__(name, parentlocation, parentlocation, moveable=False)
        """
        SimLocations are fixed static objects, so the initial location and
        parent location are the same.
        """
        # _counter tracks the number of objects in the location, producing
        # time-weighted statistics
        # _timeDataCollector tracks the time spent in the location - it is not
        # time-weighted

        self._counter = SimCounter(self, "Population")
        # We use a data collector to keep track of entries, primarily because it's
        # entries() value will be reset at the end of each warmup/batch
        # Using a SimDataCollector is a bit heavyweight, so we could implement a
        # lighter weight version that still gets reset (via resetAll())
        # Note that we use a globally available constant for the Entries
        # dataset name, since the output table and chart generators have to
        # treat this as a special case.  (Yes, a bit of a hack.)
        self._entryDataCollector = SimUnweightedDataCollector(self,
                                                              _ENTRIES_DATASET_NAME,
                                                              int)
        self._timeDataCollector = SimUnweightedDataCollector(self, "Time", SimTime)
        self._childStaticObjs = []
        self._residents = []  # TODO make this a set?
        
        if entrypointname is None:
            # No entry point name.
            # This should be a leaf location, and as such is it's own entry point
            self._entrypointLocation = self
            self._entryPointID = self.element_id
        else:
            # The entrypoint is a child location which does not yet exist,
            # so the entry point location will get set when it is instantiated.
            # The passed entry point name should be partially qualified from
            # this location; make it fully qualified.
            self._entrypointLocation = None
            self._entryPointID = '.'.join((self.element_id, entrypointname))
           
        # At instantiation, locations have no children. We reply on a child
        # location to update his problem once it is created - as we do right
        # here
        self._hasChildren = False
        if not self.parent_location.is_root:
            self.parent_location._hasChildren = True
            
        self._initialize_parent_entrypoints()
        
    def _add_child(self, staticobj):      
        """
        Add the passed static child object to this location's list of
        children. Raises if:
        - the passed object is not a SimStaticObject
        - the passed object's parent is not this location
        - the passed object has already been added via a previous call
        """
        if not isinstance(staticobj, SimStaticObject):
            msg = "Attempt to add non-static child object {0} to location {1}"
            raise SimError(_LOCATION_ERROR_NAME, msg, staticobj, self.element_id)
        
        if staticobj.parent_location is not self:
            msg = "Static object {0} parent is not location {1}"
            raise SimError(_LOCATION_ERROR_NAME, msg, staticobj.element_id,
                           self.element_id)
        
        if staticobj in self._childStaticObjs:
            msg = "Static object {0} is already a child of location {1}"
            raise SimError(_LOCATION_ERROR_NAME, msg, staticobj.element_id,
                           self.element_id)
        
        self._childStaticObjs.append(staticobj)
            
    def _initialize_parent_entrypoints(self):
        """
        Determine if there are any ancestor locations that have specified this
        new location as their entrypoint - if so, set them
        """
        for a in self.ancestor_locations:
            if a.entry_point_id == self.element_id:
                a._entrypointLocation = self
                
    def validate(self):
        """
        Raises an error if the entry point is not valid. We don't know if
        the entry point is valid until all of SimLocation instances have
        been created, so this cannot be done at the time the object is
        created/initialized. This method provides a hook for the simulation
        to check this out prior to starting the run; otherwise, we wouldn't
        get an error until an object tried to move to this location (which
        would be a serious bummer if that happened near the end of a long
        run)
        
        TODO validate anything else?
        """
        # Easiest way to validate is to get the entry point location;
        # the property will raise an error if it's invalid
        self.entry_point            
    
    @property
    def islocation(self):
        """
        Returns true if the object is a SimLocation or SimRootLocation
        """
        return True

    @property
    def is_root(self):
        """
        Returns True only for the single root object (class SimRootLocation)
        """
        return False

    @property
    def residents(self):
        """
        A generator that yields the :class:`entities <.entity.SimEntity>`
        currently residing in this location. Note that resident entries are 
        pair tuples (entity, entrytime), so this extracts the first entry
        in each pair.
        """
        return (pair[0] for pair in self._residents)
        #for pair in self._residents:
        #    yield pair[0]

    @property
    def entries(self):
        "The number of objects that have entered the location"
        return self._entryDataCollector.entries()

    @property
    def exits(self):
        "The number of objects that have exited the location"
        return self._timeDataCollector.entries()

    @property
    def currentPopulation(self):
        "The number of objects currently resident at the location"
        return self._counter.value

    @property
    def has_child_locations(self):
        """
        Returns True if this location has at least one child location
        """
        childlocs = (obj for obj in self._childStaticObjs if obj.islocation)
        return bool(next(childlocs, None))
    
    def descendants(self, cls=None):
        """
        A generator that yields all descendant static objects of this
        location that are of/derived from a passed class (which must be
        a subclass of SimStaticObject). By default, that class is
        SimLocation.        
        """
        if cls is None:
            cls = SimLocation
            
        if not issubclass(cls, SimStaticObject):
            msg = "class {0} passed to SimLocation {1} descendants() is not a subclass of SimStaticObject"
            raise SimError(_LOCATION_ERROR_NAME, msg, cls, self.element_id)
        
        cls_children = (obj for obj in self._childStaticObjs if isinstance(obj, cls))
        loc_children = (obj for obj in self._childStaticObjs if obj.islocation)
        
        for obj in cls_children:
            yield obj
            
        for location in loc_children:
            yield from location.descendants(cls)
        
    
    def is_ancestor_of(self, staticObj):
        """
        Returns True if a passes static object is a descendant of this location
        """
        return self in staticObj.ancestor_locations


    #def __getitem__(self, index):
        #"""
        #"""
        #return self._residents[index][0]
    
    def __contains__(self, obj):       
        """
        """
        if issubclass(obj.__class__, SimStaticObject):
            return obj in self.descendants(SimStaticObject)
        else:
            return obj in self.residents

    @property
    def entry_point_id(self):
        """
        The fully qualified element ID of the descendant location
        that serves as an entry location when a SimLocatable object moves to
        this location. Locatable objects should move only to leaf locations
        within a location hierarchy, so when an object attempts to move to a
        parent (non-leaf) location, it should be redirected to that parent's
        entry point.
        """
        return self._entryPointID

    @property
    def entry_point(self):
        """
        Returns the entry point location for this location object. If this
        location has no children, the location is its own entry point. If it
        has children, it is the descendant location defined by
        :meth:`entryPointName`, (a location name if the entry point is a
        child, a partially qualified element ID if the entry point is a
        grandchild or lower descendant.)

        Since the designated entryPoint location may in fact have it's own
        entryPoint, we recursively return the entryPoint's entryPoint.

        Raises an error if the entry point is not specified, doesn't exist,
        or is otherwise invalid.

        Returns:
            SimLocation: entry point location for this SimLocation
        """
        if not self.has_child_locations:
            # Leaf locations are always their own entry points
            return self
        
        if self._entrypointLocation is self:
            msg = "Location {0} has child locations and no defined entry point"
            raise SimError(_LOCATION_ERROR_NAME, msg, self.element_id)
                     
        elif self._entrypointLocation is None:
            msg = "Entry point location {0} for location {1} not found/registered"
            raise SimError(_LOCATION_ERROR_NAME, msg, self._entryPointID, self.element_id)
        
        else:
            return self._entrypointLocation.entry_point
 
    @property
    def current_population(self):
        "The number of objects currently resident at the location"
        return self._counter.value

    @apidocskip
    def index(self, obj, j=None, k=None):
        """
        Implements sequence index() method on the _residents member
        """
        if j is None:
            j = 0
        if k is None:
            k = len(self._residents)

        for i in range(j, k):
            if obj is self._residents[i][0]:
                return i
        raise ValueError # not found

    # Methods to be (optionally) implemented by subclasses
    def on_enter_impl(self, enteringObj):
        """
        Subclasses may (optionally) perform additional onEnter() processing
        by implementing ``onEnterImpl()``. The base implementation is a no-op.

        Args:
            enteringObj (SimEntity): the entity entering this location
        """
        pass

    def on_exit_impl(self, exitingObj):
        """
        Subclasses may (optionally) perform additional onExit() processing
        by implementing ``onExitImpl()``. The base implementation is a no-op.

        Args:
            exitingObj (SimEntity): the entity leaving this location
        """
        pass

    def on_enter(self, enteringObj):
        """
        Process the entry of an object into this location.  Recursively
        invokes parent location ``onEnter()`` as required.  (It is not required
        if the entering object is already resident in the parent - e.g., if
        the entering object moves between child locations belonging to the
        parent)
        """
        if enteringObj in self:
            msg = "Object ({0}) cannot enter location {1}; it is already located there"
            raise SimError("SimLocationDuplicateEntryError",
                           msg, str(enteringObj), str(self))

        # Invoke onEnter() for ancestor locations first (skipping the single
        # root location, moving down after that). Also skip if the entering
        # object is already resident in the parent (which would be the case
        # if an object moves from one child location to another within the
        # same parent)
        parentLoc = self.parent_location
        if parentLoc and not parentLoc.is_root and not enteringObj in parentLoc:
            parentLoc.on_enter(enteringObj)

        # Add the entering object to the list of residents (along with the entry time)
        # and increment the statistics-gathering counter/datacollector
        self._residents.append((enteringObj, SimClock.now()))
        self._counter.increment(None, 1)
        self._entryDataCollector.add_value(1) # the value doesn't really matter
        self.on_enter_impl(enteringObj)

    def on_exit(self, exitingObj, nextLocation):
        """
        Process the exit (including statistics updates) of an object that is
        leaving the location. Raises an SimLocationInvalidExit Error if the
        exiting is not currently in the location.  Recursively invokes
        onExit for ancestor locations that are not contained by the
        exiting object's next destination
        """
        if not exitingObj in self:
            msg = "Attempt to exit object ({0}) from a location ({1}) that it does not reside in"
            raise SimError("SimLocationInvalidExit", msg, str(exitingObj),
                           self.element_id)

        # As one might expect, onExit processing order is reversed from
        # onEnter().  When exiting, class-specific functionality is invoked
        # prior to the generic OnExit() processing, and child locations are
        # processed prior to parents.

        # perform location subclass-specific exit processing
        self.on_exit_impl(exitingObj)

        # Find and remove the residents entry for the exiting object
        objIndex = self.index(exitingObj)
        obj, enterTime = self._residents.pop(objIndex)

        # Update the time-in-location statistics and the counter
        self._timeDataCollector.add_value(SimClock.now() - enterTime)
        self._counter.decrement(1)

        # Invoke onExit for ancestors, from botton-up, so long as the
        # ancestor is not the next destination (or contained by the next
        # destination)
        parentLoc = self.parent_location
        if parentLoc and not parentLoc.is_root and parentLoc is not nextLocation:
            if not parentLoc.is_ancestor_of(nextLocation):
                parentLoc.on_exit(exitingObj, nextLocation)


@apidoc
class SimRootLocation(object):
    """
    Class that defines a singleton that serves as the root location for all
    static objects.
    
    It is not a subclass of SimLocation, since most/all of the base classes
    include member variables and behavior (particularly, but totally in __init__())
    that does not apply to the special case of a root object.
    
    Defines/implements SimLocatable/SimStaticObject/SimLocation methods/properties
    where needed for the root location.
    """
    def __init__(self):
        """
        The root does maintain a list of child static objects
        """
        self._childStaticObjs = []
       
    @property
    def element_name(self):
        """
        The base (non-qualified with ancestor names) name of this static object
        """
        return _ROOT_LOCATION_NAME
       
    @property
    def element_id(self):
        """
        The base (non-qualified with ancestor names) name of this static object
        """
        return _ROOT_LOCATION_NAME
    
    @property
    def islocation(self):
        """
        Returns true if the object is a SimLocation or SimRootLocation
        """
        return True

    @property
    def is_root(self):
        """
        Since this is the Root object, returns True
        """
        return True

    @property
    def location(self):
        """
        Required for SimLocatable interface. The Root location has no location
        """
        return None
    
    @property
    def islocation(self):
        """
        Returns true if the object is a SimLocation or SimRootLocation.
        Required for SimLocatable interface. 
        """
        return True
    
    def is_ancestor_of(self, staticObj):
        """
        Returns True if a passes static object is a descendant of this location
        All static objects are descendants of the Root location (except for the
        root location itself)
        """
        return staticObj is not self

    def on_enter(self, enteringObj):
        """
        Required for SimLocation interface.
        onEnter/onExit are no-ops for the root location
        """
        pass

    def on_exit(self, enteringObj):
        """
        Required for SimLocation interface.
        onEnter/onExit are no-ops for the root location
        """
        pass
        
    def _add_child(self, staticobj):      
        """
        Add the passed static child object to the root's list of
        children. Raises if:
        - the passed object is not a SimStaticObject
        - the passed object's parent is not this location
        - the passed object has already been added via a previous call
        
        Slight variation of SimLocation implementation
        """
        if not isinstance(staticobj, SimStaticObject):
            msg = "Attempt to add non-static child object {0} to root location"
            raise SimError(_LOCATION_ERROR_NAME, msg, staticobj)
        
        if staticobj.parent_location is not self:
            msg = "Static object {0} parent is not the root location"
            raise SimError(_LOCATION_ERROR_NAME, msg, staticobj.element_id)
        
        if staticobj in self._childStaticObjs:
            msg = "Static object {0} is already a child of root location"
            raise SimError(_LOCATION_ERROR_NAME, msg, staticobj.element_id)
        
        self._childStaticObjs.append(staticobj)


@apidoc
class SimQueue(SimLocation):
    """
    A Location acting as a queue.
    """
    

    
if __name__ == '__main__':
    from simprovise.core import SimProcess
    from simprovise.core.simobject import SimTransientObject
    
    # Note that the code below that creates MockLocation objects fails when
    # SimModel.register_element() does issubclass(element.__class__, SimElement)
    # Pretty sure this is because Python thinks the class created in the file
    # being executed is not the same class that is imported

    class MockProcess(SimProcess):
        def __init__(self):
            super().__init__()
            print("initializing mock process")
 
    class MockLocation(SimLocation):
        def __init__(self, name, parentloc=None, entryPointName=None):
            """
            """
            super().__init__(name, parentloc, entryPointName)
            #self.name = name
    
        def on_enter_impl(self, enteringObj):
            print(enteringObj, "entering location", self.element_id)
    
        def on_exit_impl(self, exitingObj):
            print(exitingObj, "leaving location", self.element_id)
            
    class MockLocation2(MockLocation):      
        """
        """


    class MockLocatable(SimTransientObject):
        def __init__(self, name, location=None, moveable=True):
            self.name = name
            super().__init__(location)

    parentLoc1 = MockLocation("parent", None, "child1")
    parentLoc2 = MockLocation("parent2", None)
    childLoc1 = MockLocation("child1", parentLoc1)
    childLoc2 = MockLocation2("child2", parentLoc1)

    print("parent1 ID", parentLoc1.element_id)
    print("parent1 is SimElement", issubclass(parentLoc1.__class__, SimElement))
    print("parent2 ID", parentLoc2.element_id)
    print("childLoc1 ID", childLoc1.element_id)
    print("MockLocatable ID", childLoc2.element_id)

    print("Parent1entry point:", parentLoc1.entry_point.element_id)
    
    print("===== parentLoc1 location descendants ======")
    for d in parentLoc1.descendants():
        print(d.element_id)
        
    print("===== parentLoc1 MockLocation2 descendants ======")
    for d in parentLoc1.descendants(MockLocation2):
        print(d.element_id)
    
    for a in childLoc1.ancestor_locations:
        print("childLoc1 ancestor: ", a.element_id)

    item1 = MockLocatable("item1", childLoc1)
    item2 = MockLocatable("item2", childLoc1)

    print("Current Population:", "Parent1: ", parentLoc1.current_population,
          "Child1:", childLoc1.current_population,
          "Child2:", childLoc2.current_population,
          "Parent2:", parentLoc2.current_population)

    item1.move_to(childLoc2)
    print("Current Population:", "Parent1: ", parentLoc1.current_population,
          "Child1:", childLoc1.current_population,
          "Child2:", childLoc2.current_population,
          "Parent2:", parentLoc2.current_population)

    item1.move_to(parentLoc2)
    print("Current Population:", "Parent1: ", parentLoc1.current_population,
          "Child1:", childLoc1.current_population,
          "Child2:", childLoc2.current_population,
          "Parent2:", parentLoc2.current_population)
