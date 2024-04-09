#===============================================================================
# MODULE entitysource
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimEntitySource and related classes.
#===============================================================================
__all__ = ['SimEntitySource']

from collections import OrderedDict
import copy
import inspect

from simprovise.core import (SimLocation, SimTime,
                            SimClock, SimDistribution)
from simprovise.core.utility import SimUtility
from simprovise.core.apidoc import apidoc, apidocskip
from simprovise.core.simevent import SimEvent
from simprovise.core.utility import SimUtility


@apidoc
class SimEntitySource(SimLocation):
    """
    SimEntitySources exist solely to create :class:`SimEntity` instances
    during a simulation run, initialize them (primarily by also creating the
    :class:`.SimProcess` that will execute on their behalf), and start them
    on their way by initiating that process.

    Args:
        name (str):                Name of the source, must be unique within the
                                   source's location (locationObj)
        locationObj (SimLocation): Location object to which this source belongs.
                                   If ``None`` this source is assigned to the
                                   Root location
        animationObj:              ``None`` if the simulation is not animated
        **properties:              Keyword dictionary for additional property
                                   values to be set (if any).
    """
    # TODO should this be a pseudo-SimLocation, a-la SimEntitySink? The case is
    # not as compelling here, since there is a theoretical possibility that
    # entitys can hang around the source before being moved.

    # If we do choose to make this a pseudo-location (inherit from
    # SimAnimatableObject instead of SimLocation), we'll have to implement both
    # onEnter() and onExit().

    __slots__ = ('__generatorDefs', '__generatorDefsAreEditable',
                 '__generatorPairs')

    def __init__(self, name, parentlocation=None):
        super().__init__(name, parentlocation)
        self.__generatorDefs = []
        self.__generatorDefsAreEditable = True
        self.__generatorPairs = []

    #@classmethod
    #@apidocskip
    #def allowsChildren(cls):
        #"""
        #Override to indicate that instances of this class do not support the
        #assignment of child static objects (even though this is a SimLocation).
        #"""
        #return False

    @property
    @apidocskip
    def generatorDefinitions(self):
        """
        Returns the list of current generator definitions, all of type
        SourceGeneratorDef.
        """
        return self.__generatorDefs

    @apidocskip
    def final_initialize(self):
        """
        At final initialization, translate entity/interarrival generator
        pairs (created via addEntityGenerator() and/or addGeneratorPair())
        into entity generation events (which are then registered).

        The assumption is that this occurs after the random number streams
        and the simulation event processor for the current run are
        initialized.
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

    def add_entity_generator(self, entityClass, processClass,
                           interarrivalFunc, *iaArgs, **iaKwargs):
        """
        Initializes a stream of entities to be generated via the following
        specification:

        - The class (:class:`SimEntity` or SimEntity-derived) of the
          entities to be generated
        - The class (SimProcess-derived) of the generated entity's process
        - An interarrival generator-creating function defined in
          :class:`SimDistribution`
        - The parameters (specified as positional and/or keyword arguments) of
          the interarrival function.

        Sample Usage::

            source.addEntityGenerator(SimEntity, MyProcess,
                                      SimDistribution.exponential,
                                      mean=SimTime(42, simtime.MINUTES),
                                      rnStream=18)

        This method requires the entity class initializer to take the same
        two arguments as :class:`.SimEntity` (entitySource and process), and the
        process class initializer to take no arguments at all. If either of
        those conditions do not hold, use :meth:`addGeneratorPair` instead.

        Note that a entity source can be associated with multiple generators,
        so this method can be called any number of times on the same source
        instance.

        Args:
            entityClass (class):         SimEntity or SimEntity-derived
            processClass (class):        SimProcess-derived
            interarrivalFunc (function): One of the members of
                                         :class:`.SimDistribution`
            *iaArgs:                     Positional arguments to interarrivalFunc
            **iaKwargs:                  Keyword arguments to interarrivalFunc
        """
        # Create a generator object from the interarrival function and parameters
        interarrivalGenerator = SimDistribution.number_generator(interarrivalFunc,
                                                                *iaArgs,
                                                                **iaKwargs)

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

        addGeneratorPair() creates stream of entities via two passed generators:

        1. An entity generator, each iteration of which yields a new entity
           (and its SimProcess)
        2. An interarrival time generator, each iteration of which yields the
           time (:class:`SimTime`) until the next work item is generated

        Args:
            entityGenerator:       A generator that yields :class:`.SimEntity`
                                   (or objects derived from ``SimEntity``)
            interarrivalGenerator: A generator that yields interarrival times
                                   (class :class:`SimTime`)
        """
        # As with addEntityGenerator(), we cannot actually create the
        # SimEntityGenerationEvent here, since this method may be called before
        # the simulation's random number streams have been initialized.
        self.__generatorPairs.append((entityGenerator, interarrivalGenerator))


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
