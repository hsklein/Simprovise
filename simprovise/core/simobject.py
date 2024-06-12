#===============================================================================
# MODULE simobject
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimLocatableObject and SimTransientObject classes, along
# with the LocationAssignmentAgentMixin (used by classes in the
# resource module to start)
#===============================================================================
from simprovise.core import SimError, SimLogging, simtrace

from simprovise.core.agent import SimAgent, SimMsgType
from simprovise.core.apidoc import apidoc, apidocskip

_LOCATABLE_ERROR_NAME = "SimLocatableObjectError"

logger = SimLogging.get_logger(__name__)


@apidoc
class SimLocatableObject(SimAgent):
    """
    An object that can either moved to or placed at a
    :class:`~.location.SimLocation`. Since SimLocations can be placed
    (contained) in other SimLocations, they are SimLocatables as well.
    
    SimLocatables are initialized with an initial location; if None, that
    initial location defaults to the singleton Root location
    (:class:`~.location.SimRootLocation`)
    
    SimLocatables have two key binary propertys:
    
    - Fixed or Moveable: fixed locatables are contained to the location they
      are assigned at birth. Invoking move() on a fixed SimLocatable will
      raise an exception
      
    - Static or Transient. Static locatables
      (:class:`~.location.SimStaticObject`) are created prior to the start
      of a simulation run and exist for the entire run. Transient
      locatables (:class:`SimTransientObject`) may be created and/or
      destroyed during a run. :class:`~.entity.SimEntity` is the primary
      transient locatable class; most others are static.
    
    Note that SimStaticObjects, while usually fixed, can be moveable; the
    main example is :class:`~.resource.SimResource`, some of which can move
    from place to place. Static objects are assigned both an initial
    location and parent"owning" location specified at construction.
    Moveable static objects can only move to that parent or sublocations
    of that parent.
    """
    __slots__ = ('_location', '_isMoveable')

    def __init__(self, initialLocation=None, moveable=False):
        super().__init__()
        
        if not initialLocation:
            msg = "No Initial Location object pecified for SimLocatableObject {0}"
            raise SimError(_LOCATABLE_ERROR_NAME, msg, self)
        
        if not initialLocation.islocation:
            msg = "Initial Location object {0} specified for {1} is not a SimLocation"
            raise SimError(_LOCATABLE_ERROR_NAME, msg, initialLocation, self)

        self._location = initialLocation
        self._isMoveable = moveable

    @property
    def location(self):
        """
        The current location of the Locatable object
        
        :return: Current location of the locatable object
        :rtype:  :class:`~.location.SimLocation` or
                 :class:`~.location.SimRootLocation`
                 
        """
        return self._location
    
    @property
    def islocation(self):
        """
        
        :return: True if the object is a :class:`~.location.SimLocation` or
                 :class:`~.location.SimRootLocation`. Default is False
                 for SimLocatable (overridden by subclasses as required)
        :rtype:  `bool`
        
        """
        return False
    
    @property
    def ismoveable(self):
        """
        
        :return: True if the object can be moved from one location to
                 another; False otherwise. Inverse of :meth:`isfixed`
        :rtype:  `bool`
        
        """
        return self._isMoveable
     
    @property
    def isfixed(self):
        """
        
        :return: True if the object cannot be moved from one location to
                 another; False otherwise. Inverse of :meth:`ismoveable`
        :rtype:  `bool`
 
        """
        return not self._isMoveable
    
    def move_to(self, toLocation):
        """
        Move to a new location.
        
        :param toLocation: The location to move to.
        :type toLocation:  :class:`~.location.SimLocation` or
                           :class:`~.location.SimRootLocation`.
                           
        """        
        self._validate_move_to_location(toLocation)
        @simtrace.trace
        def trace():
            simtrace.trace_event(self, simtrace.Action.MOVE_TO, [toLocation])
        trace()
        self._currentLocation = toLocation

    def _validate_move_to_location(self, toLocation):
        """
        Validate the toLocation prior to a move_to(), raising if the
        toLocation is (a) not a location, (b) is the same as the current
        location, or (c) is the root location.
        """
        if not self.ismoveable:
            msg = "Attempt to move fixed object ({0})"
            raise SimError(_LOCATABLE_ERROR_NAME, msg, str(self))
 
        if not toLocation.islocation:
            msg = "Attempt to move ({0}) to a non-location object ({1})"
            raise SimError(_LOCATABLE_ERROR_NAME, msg, str(self), str(toLocation))

        if toLocation is self.location:
            msg = "Attempt to move object ({0} to it's existing location ({1}))"
            raise SimError(_LOCATABLE_ERROR_NAME, msg, str(self), str(toLocation))

        if toLocation.is_root:
            msg = "Attempt to move object ({0} to the root location"
            raise SimError(_LOCATABLE_ERROR_NAME, msg, str(self))


@apidoc
class SimTransientObject(SimLocatableObject):
    """
    Base class for transient simulation elements - i.e., objects that may be
    created at any time during a simulation run, and are typically destroyed
    before the run ends. That is in contrast to static objects, which are
    created before a run starts and whose lifetimes extend for the entire
    simulation run.

    Entities are the primary (and at this time, only) subclass of
    SimTransientObject. Client modeling code should NOT inherit directly
    from SimTransientObject.

    Transient objects can move from location to location, and their
    location property value reflects the most-recently-moved-to
    destination location.
    """
    def __init__(self, initialLocation):
        """
        Initialize a transient object, which is always moveable
        """
        super().__init__(initialLocation, moveable=True)
        assert initialLocation, "No initial location provided for transient object"

        initialLocation.on_enter(self)

    def move_to(self, toLocation):
        """
        Move to a new location - or more specifically, that location's
        entryPoint. For leaf locations (locations that contain no child
        locations) the location is its own entry point. Non-leaf locations
        must explcitly designate one of their child locations as their entry
        point - otherwise, any attempt to move to that non-leaf location will
        raise a :class:`~.simexception.SimError`

        :param toLocation: The location to move to.
        :type toLocation:  :class:`~.location.SimLocation` or
                           :class:`~.location.SimRootLocation`.
                           
       """
        self._validate_move_to_location(toLocation)
        # Invoke exit processing on the current location before moving
        # to the destination location - which is actually the toLocation's
        # entryPoint location (which may or may not be the same as the toLocation)
        entryPoint = toLocation.entry_point
        if entryPoint is None:
            msg = "Entry Point Location {0} not found for move-to location {1}"
            raise SimError(_LOCATABLE_ERROR_NAME, msg, toLocation.entry_point_id,
                           toLocation.element_id)

        self._location.on_exit(self, entryPoint)
        super().move_to(entryPoint)
        self._location = entryPoint

        # Invoke enter processing on the new location
        entryPoint.on_enter(self)



class LocationAssignmentAgent(SimAgent):
    """
    A mix-in class that provides a SimAgent
    with basic resource assignment functionality - the ability to handle
    resource request and release messages.  This mix-in fulfills requests
    on a first-in/first-out basis.
    """
    # TODO Is this never-alive code?
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Location assignment dictionary.
        # Keys are SimLocations managed by this agent
        # Values are  list of SimEntities currently assigned to to that location
        self._locationAssignments = {}
        self.register_handler(SimMsgType.LOC_REQUEST, self.handleLocationRequest)
        self.register_handler(SimMsgType.LOC_RELEASE, self.handleLocationRelease)

    def registerLocation(self, location):
        """
        """

    def handleLocationRequest(self, msg):
        """
        """

    def handleLocationRelease(self, msg):
        """
        """





if __name__ == '__main__':

    class MockLocation(SimLocation):
        def __init__(self, name, parentloc=None, entryPointName=None):
            super().__init__(name, parentloc, entryPointName)
            #self.name = name

        def on_enter_impl(self, enteringObj):
            print(enteringObj, "entering location", self.element_id)

        def on_exit_impl(self, exitingObj):
            print(exitingObj, "leaving location", self.element_id)

    class MockLocatable(SimTransientObject):
        def __init__(self, name, location=None):
            self.name = name
            super().__init__(location)


    parentLoc1 = MockLocation("parent", None, "child1")
    parentLoc2 = MockLocation("parent2", None)
    childLoc1 = MockLocation("child1", parentLoc1)
    childLoc2 = MockLocation("child2", parentLoc1)

    print("parent1 ID", parentLoc1.element_id)
    print("parent2 ID", parentLoc2.element_id)
    print("childLoc1 ID", childLoc1.element_id)
    print("childLoc2 ID", childLoc2.element_id)

    print("Parent1entry point:", parentLoc1.entry_point.element_id)
    
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
