#===============================================================================
# MODULE entitysink
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimEntitySink class.
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
__all__ = ['SimEntitySink']

from simprovise.core import SimError
from simprovise.core.simlogging import SimLogging
from simprovise.modeling.location import SimStaticObject
from simprovise.core.apidoc import apidoc, apidocskip

logger = SimLogging.get_logger(__name__)
_ERROR_NAME = "SimEntitySinkError" 

@apidoc
class SimEntitySink(SimStaticObject):
    """
    Defines an entity sink - where :class:`~.entity.SimEntity` objects go to die.
    Every :meth:`~.process.SimProcess.run` implementation should end with
    the equivalent of::

        entity.move_to(sink)

    SimEntitySink acts (to some extent) like a :class:`~.location.SimLocation`,
    but doesn't inherit from it, as it doesn't need all of SimLocation's
    baggage. Nonetheless, it does need to at least provide no-op versions of
    the :class:`~.location.SimLocation` interface. (Though no ``onExit()`` is
    needed, since entities check in, but they don't check out.)
    
    SimEntitySinks take no parent location parameter; they are always assigned
    to the :class:`~.location.SimRootLocation`. This restriction ensures
    entity location exit processing is always performed on the entity's last
    location before being destroyed.
        
    :param name: The name of the entity sink. Must be unique across all
                 sinks and other :class:`~.location.SimStaticObject`
                 objects assigned to the :class:`~.location.SimRootLocation`
    :type name:  `str`
        
    """
    __slots__ = ('__entries')

    def __init__(self, name):
        """
        """
        super().__init__(name)
        # Sinks should be root-level locations
        if not self.location.is_root:
            msg = "Attempt to assign a entity sink to non-root location ({0})"
            raise SimError(_ERROR_NAME, msg, self.location)
        self.__entries = 0

    @property
    def islocation(self):
        """
        Returns True if this object is a location - overridden to True in this case
        """
        return True

    @property
    def is_root(self):
        """
        Required for the SimLocation interface. Returns False.
        """
        return False

    def descendants(self):
        """
        Required for the SimLocation interface - a null generator
        """
        yield from ()

    @property
    def entries(self):
        "The number of objects that have entered the sink"
        return self.__entries

    def on_enter(self, enteringObj):
        """
        Entry into a sink is also, in effect an exit.
        Update the entry counter, remove
        """
        self.__entries += 1
        enteringObj.destroy()

    @property
    def entry_point(self):
        """
        As with a leaf :class:`~.location.SimLocation`, the
        SimEntitySink is its own entry point.
        """
        return self

    @property
    def entry_point_id(self):
        """
        Since a sink is it's own entry point, the entry point ID is the
        sink's element ID
        """
        return self.element_id






