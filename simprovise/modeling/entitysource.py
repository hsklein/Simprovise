#===============================================================================
# MODULE entitysource
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimEntitySource and related classes.
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
__all__ = ['SimEntitySource']

from simprovise.core import SimError
from simprovise.core.simlogging import SimLogging
from simprovise.core.simclock import SimClock
from simprovise.core.simtime import SimTime
from simprovise.core.simevent import SimEvent

from simprovise.core.apidoc import apidoc, apidocskip
from simprovise.modeling import SimLocation

logger = SimLogging.get_logger(__name__)

_ERROR_NAME = "SimEntitySourceError"

@apidoc
class SimEntitySource(SimLocation):
    """
    SimEntitySources exist solely to create :class:`SimEntity` instances
    during a simulation run, initialize them (primarily by also creating the
    :class:`.SimProcess` that will execute on their behalf), and start them
    on their way by initiating that process.
    
    Entity sources are always assigned to the root location.
        
    :param name: The name of the entity source. Must be unique across all
                 sources and other :class:`~.location.SimStaticObject`
                 objects assigned to the :class:`~.location.SimRootLocation`
    :type name:  `str`
        
    """
    # TODO should this be a pseudo-SimLocation, a-la SimEntitySink? The case is
    # not as compelling here, since there is a theoretical possibility that
    # entitys can hang around the source before being moved.

    # If we do choose to make this a pseudo-location (inherit from
    # SimStaticObject instead of SimLocation), we'll have to implement both
    # on_enter() and on_exit() and is_location.

    __slots__ = ('__generatorPairs')

    def __init__(self, name):
        super().__init__(name)
        self.__generatorPairs = []

    def final_initialize(self):
        """
        At final initialization, translate entity/interarrival generator
        pairs (created via addEntityGenerator() and/or addGeneratorPair())
        into entity generation events (which are then registered).

        The assumption is that this occurs after the random number streams
        and the simulation event processor for the current run are
        initialized.
        
        Called by infrastructure, not by client (model-specific) code -
        but any subclass that implements :meth:`final_initialize` must
        invoke `super().final_initialize()` to ensure that this base class
        implementation is executed.
        """
        self._create_entity_generation_events()

    def _create_entity_generation_events(self):
        """
        For each entity/interarrival generator pair, create and register an
        event that will create the first entity and fire its process, and
        then continually re-register itself to repeat that exercise.
        """
        for entityGenerator, interarrivalGenerator in self.__generatorPairs:
            event = SimEntityGenerationEvent(self, entityGenerator,
                                             interarrivalGenerator)
            event.register()

    def add_entity_generator(self, entityClass, processClass, interarrivalGenerator):
        """
        Initializes a stream of entities to be generated via the following
        specification:

        * The class (:class:`SimEntity` or SimEntity-derived) of the
          entities to be generated
        * The class (SimProcess-derived) of the generated entity's process
        * An interarrival generator-creating function defined in
          :class:`SimDistribution`
        * The parameters (specified as positional and/or keyword arguments) of
          the interarrival function.

        Sample Usage::

            generator = SimDistribution.exponential(mean=SimTime(42, tu.MINUTES)
            source.addEntityGenerator(SimEntity, MyProcess, generator, rnStream=18)

        This method requires the entity class initializer to take the same
        two arguments as :class:`.entity.SimEntity` (entitySource and process),
        and the process class initializer to take no arguments at all. If either 
        of those conditions do not hold, use :meth:`add_generator_pair` instead.

        Note that a entity source can be associated with multiple generators,
        so this method can be called any number of times on the same source
        instance.
       
        :param entityClass:      The class of the entity to be generated.
                                 Must be :class:`~.entity.SimEntity` or
                                 a subclass of that.
        :type entityClass:       `class`
        
        :param processClass:     The class of the process assigned to the
                                 generated entity. Must be a subclass of
                                 :class:`~.process.SimProcess`.
        :type processClass:      `class`
       
        :param interarrivalFunc: One of the members of
                                 :class:`~simprovise.core.random.SimDistribution`
        :type interarrivalFunc:  `func`
               
        :param \*iaArgs:         Positional arguments to interarrivalFunc
        :param \**iaKwargs:      Keyword arguments to interarrivalFunc
         
        """
        # Create a generator object from the interarrival function and parameters
        #interarrivalGenerator = interarrivalFunc(*iaArgs, **iaKwargs)

        # Define a simple generator that creates a entity and process of the right type,
        # and yields the entity
        def entityGenerator():
            while True:
                process = processClass()
                yield entityClass(self, process)

        # Note that rather than creating an EntityGenerationEvent, we just
        # store the two generators as a pair. The reason: the
        # EntityGenerationEvent's initializer grabs the first interarrival
        # value, which usually means sampling from a random number stream -
        # and if this is called from a standalone model script, that stream
        # should not yet be initialized.
        self.__generatorPairs.append((entityGenerator(), interarrivalGenerator))

    def add_generator_pair(self, entityGenerator, interarrivalGenerator):
        """
        ``addGeneratorPair()`` is an alternative to :meth:`addEntityGenerator`,
        typically used when either:

        (a) the :class:`SimEntity` and/or :class:`SimProcess` classes require
            additional initializer parameters, or
        (b) we wish to generate several classes of entity and/or process using a
            single interarrival distribution.

        addGeneratorPair() creates a stream of entities via two passed
        generators:

        1. An entity generator, each iteration of which yields a new entity
           (and its :class:`~.process.SimProcess`)
        2. An interarrival time generator, each iteration of which yields the
           time (:class:`~.simtime.SimTime`) until the next work item is generated

       
        :param entityGenerator:      A generator that yields objects of
                                     :class:`~entity.SimEntity` or a subclass
        :type entityGenerator:       `generator`
       
        :param interarrivalGenerator: A generator that yields interarrival
                                      times (class :class:`~.simtime.SimTime`)
        :type interarrivalGenerator:  `generator`
              
        """
        # As with addEntityGenerator(), we cannot actually create the
        # SimEntityGenerationEvent here, since this method may be called before
        # the simulation's random number streams have been initialized.
        self.__generatorPairs.append((entityGenerator, interarrivalGenerator))
        
    def _add_child(self, staticobj):      
        """
        SimEntitySources should not have child static objects.
        Raise an error on the attempt.
        """
        msg = "Attempting to add child static object {0} to SimEntitySource {1}"
        raise SimError(_ERROR_NAME, msg, self.element_id, staticobj.element_id)


class SimEntityGenerationEvent(SimEvent):
    """
    An Event that creates a new work item (along with it's process) at the next
    interarrival interval, starts that work item's process, and then re-registers
    itself in order to repeat that sequence.
    """
    __slots__ = ('__source', '__entityGenerator', '__interarrivalGenerator')

    def __init__(self, entitySource, entityGenerator, interarrivalGenerator):
        # check the first yield from the interarrival generator, to make sure it's a SimTime
        firstInterarrivalTime = next(interarrivalGenerator)
        assert isinstance(firstInterarrivalTime, SimTime), "Interarrival Generator class " + str(type(interarrivalGenerator)) + "does not yield SimTime values"

        super().__init__(SimClock.now() + firstInterarrivalTime)
        self.__source = entitySource
        self.__entityGenerator = entityGenerator
        self.__interarrivalGenerator = interarrivalGenerator

    def process_impl(self):
        """
        Process the event by:
        1.  Creating a new entity (via the event's Entity generator)
        2.  Starting that new entity's process
        3.  Re-registering this event using the next interarrival time (obtained via
            the event's interarrival generator)
        """
        entity = next(self.__entityGenerator)
        entity.process.start()
        self._time += next(self.__interarrivalGenerator)
        self.register()
