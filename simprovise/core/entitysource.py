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

# Source Generator dictionary key constants
_ENTITY_CLASS = "EntityClass"
_PROCESS_CLASS = "ProcessClass"
_IA_DISTRIBUTION = "InterarrivalDistribution"
_IA_DIST_PARAMETERS = "InterarrivalDistributionParameters"


class SourceGeneratorDef(object):
    """
    SourceGeneratorDef instances define/specify how to generate a stream of entitys
    (objects of or derived from SimEntity) from a SimEntitySource.  The specification
    consists of:
    - The class of the entitys to generate
    - The class of the process (derived from SimProcess) that will be initiated for
      each generated entity
    - The interarrival distribution used to "space" the generation of entitys/processes
      over simulated time.

    SourceGeneratorDef instances are designed to be specified by the user at design time,
    serialized/saved with the model (as part of a SimEntitySource), and then used by
    that SimEntitySource to create SimEntityGenerationEvents at model execution time.
    In other words, this class is designed for use with a GUI model builder, not
    model scripts written as stand-alone code.
    """
    def __init__(self):
        """
        Initialize a new (empty) SourceGeneratorDef.
        """
        d = {}
        keys = (_ENTITY_CLASS, _PROCESS_CLASS, _IA_DISTRIBUTION, _IA_DIST_PARAMETERS)
        self.__defDict = d.fromkeys(keys)
        self.__defDict[_IA_DISTRIBUTION] = None
        self.__defDict[_IA_DIST_PARAMETERS] = OrderedDict()

    def asDict(self):
        """
        Return the SourceGeneratorDef as it's dictionary.
        """
        return self.__defDict

    def fromDict(self, sgdict):
        """
        Initialize the SourceGeneratorDef from a passed dictionary, typically as read
        from a JSON (or other) deserialization.  When coming from JSON. the distribution
        parameters ordered dictionary will be a standard (un-ordered) dictionary instead;
        If that's the case, convert it back to an ordered dictionary.  Also convert
        serialized SimTime values back to SimTime objects.
        """
        self.__defDict = copy.deepcopy(sgdict)
        if not isinstance(sgdict[_IA_DIST_PARAMETERS], OrderedDict):
            # Interarrival distribution parameters are a standard, not ordered dictionary
            # Reset the distribution name, which also creates a new ordered dictionary, with
            # all of the right keys in the right order.  (We set it to None first, as the
            # setter is a no-op when the value doesn't change)
            self.interarrivalDistributionName = None
            self.interarrivalDistributionName = sgdict[_IA_DISTRIBUTION]

            # Copy the values from the passed dictionary into the ordered dictionary.
            # Deserialize any SimTime values.  SimTime.derserialize() will just return
            # the passed object if it's not supposed to be a SimTime.
            for pname, pval in sgdict[_IA_DIST_PARAMETERS].items():
                self.interarrivalDistributionParameters[pname] = SimTime.deserialize(pval)

    @property
    def entityClassName(self):
        """
        The (fully-qualified) name of the entity class
        """
        return self.__defDict[_ENTITY_CLASS]

    @entityClassName.setter
    def entityClassName(self, newVal):
        """
        The (fully-qualified) name of the entity class
        """
        self.__defDict[_ENTITY_CLASS] = newVal

    @property
    def entityClass(self):
        """
        Returns the entity class itself (not the name), or None if not specified
        """
        if self.entityClassName:
            return SimUtility.getClass(self.entityClassName)
        else:
            return None

    @property
    def processClassName(self):
        """
        The (fully-qualified) name of the process class
        """
        return self.__defDict[_PROCESS_CLASS]

    @processClassName.setter
    def processClassName(self, newVal):
        """
        The (fully-qualified) name of the process class
        """
        self.__defDict[_PROCESS_CLASS] = newVal

    @property
    def processClass(self):
        """
        Returns the process class itself (not the name), or None if not specified
        """
        if self.processClassName:
            return SimUtility.getClass(self.processClassName)
        else:
            return None

    @property
    def interarrivalDistributionName(self):
        """
        The name of the interarrival distribution.
        """
        return self.__defDict[_IA_DISTRIBUTION]

    @interarrivalDistributionName.setter
    def interarrivalDistributionName(self, newVal):
        """
        Sets the name of the interarrival distribution; also initializes the
        distribution parameters if the name has changed.
        """
        if newVal != self.interarrivalDistributionName:
            if newVal is None:
                self.__defDict[_IA_DISTRIBUTION] = None
                self.__defDict[_IA_DIST_PARAMETERS] = OrderedDict()
            else:
                  # If we've set a new (non-None) distribution, re-initialize
                # the parameter dictionary by inspecting the distribution function
                # arguments.
                iaFunc = SimDistribution.function(newVal)
                argSpec = inspect.getfullargspec(iaFunc)

                # Get the argument names in a list
                args = argSpec.args

                # Get default values (if any), which apply starting at the end
                # of the argument list.
                if argSpec.defaults:
                    defaults = list(argSpec.defaults)
                else:
                    defaults = []

                # For arguments where the function does not specify a default
                # value, initialize the corresponding dictionary value to None.
                defaults.extend([None] * (len(args) - len(defaults)))
                defaults.reverse()
                self.__defDict[_IA_DIST_PARAMETERS] = OrderedDict(zip(args, defaults))
                self.__defDict[_IA_DISTRIBUTION] = newVal

    @property
    def interarrivalDistribution(self):
        """
        The interarrival distribution function corresponding to the currently st
        distribution name.
        """
        return SimDistribution.function(self.interarrivalDistributionName)

    @property
    def interarrivalDistributionParameters(self):
        """
        The currently set interarrival distribution parameters, as an ordered dictionary.
        """
        return self.__defDict[_IA_DIST_PARAMETERS]

    def interarrivalParametersAsString(self):
        """
        The currently set interarrival distribution parameters, as a display string.
        """
        parms = self.interarrivalDistributionParameters
        pstrlist = [p[0] + '=' + str(p[1]) for p in parms.items()]
        return ', '.join(pstrlist)


@apidoc
class SimEntitySource(SimLocation):
    """
    SimEntitySources exist solely to create :class:`.SimEntity` instances
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

    def __init__(self, name, locationObj=None, animationObj=None, **properties):
        super().__init__(name, locationObj, animationObj, **properties)
        self.__generatorDefs = []
        self.__generatorDefsAreEditable = True
        self.__generatorPairs = []

    @classmethod
    @apidocskip
    def allowsChildren(cls):
        """
        Override to indicate that instances of this class do not support the
        assignment of child static objects (even though this is a SimLocation).
        """
        return False

    @property
    @apidocskip
    def generatorDefinitions(self):
        """
        Returns the list of current generator definitions, all of type
        SourceGeneratorDef.
        """
        return self.__generatorDefs

    @generatorDefinitions.setter
    def generatorDefinitions(self, newVal):
        #self.raiseIfNotInDesignMode("Entity Generator definitions can only be modified at design time")
        self.__generatorDefs = newVal

    @property
    @apidocskip
    def generatorDefinitionsAreEditable(self):
        """
        Flag indicating whether the user should be able to add/delete/modify the entity
        generator definitions.  When False, the UI object property viewer will NOT display
        generation definitions.
        """
        return self.__generatorDefsAreEditable

    @generatorDefinitionsAreEditable.setter
    def generatorDefinitionsAreEditable(self, newVal):
        """
        Flag indicating whether the user should be able to add/delete/modify the entity
        generator definitions.  When False, the UI object property viewer will NOT display
        generation definitions.
        """
        self.__generatorDefsAreEditable = newVal

    @apidocskip
    def staticInitialize(self):
        """
        At static initialization, translate generator definitions into
        entity/interarrival generator pairs; then convert all such pairs into
        entity generation events (which actually put the generator
        definitions into action). Note that generator pairs may have also
        been created directly via addEntityGenerator() and/or
        addGeneratorPair() calls.

        The assumption is that this occurs after the random number generators
        for the current run are initialized.
        """
        self._processGeneratorDefinitions()
        self._createEntityGenerationEvents()

    def _createEntityGenerationEvents(self):
        """
        For each entity/interarrival generator pair, create and register an
        event that will create the first entity and fire its process, and
        then continually re-register itself to repeat that exercise.
        """
        for entityGenerator, interarrivalGenerator in self.__generatorPairs:
            event = SimEntityGenerationEvent(self, entityGenerator,
                                             interarrivalGenerator)
            event.register()

    def _processGeneratorDefinitions(self):
        """
        Creates a entity generator (via addEntityGenerator()) for each
        generatorDefinition (type SourceGeneratorDef)
        """
        for gdef in self.generatorDefinitions:
            wiClass = gdef.entityClass
            processClass = gdef.processClass
            interarrivalFunc = gdef.interarrivalDistribution
            kwargs = gdef.interarrivalDistributionParameters
            self.addEntityGenerator(wiClass, processClass, interarrivalFunc, **kwargs)

    def addEntityGenerator(self, entityClass, processClass,
                           interarrivalFunc, *iaArgs, **iaKwargs):
        """
        Initializes a stream of entities to be generated via the following
        specification:

        - The class (:class:`.SimEntity`SimEntity or SimEntity-derived) of the
          entities to be generated
        - The class (SimProcess-derived) of the generated entity's process
        - An interarrival generator-creating function defined in
          :class:`.SimDistribution`
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
        interarrivalGenerator = SimDistribution.numberGenerator(interarrivalFunc,
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

    def addGeneratorPair(self, entityGenerator, interarrivalGenerator):
        """
        ``addGeneratorPair()`` is an alternative to :meth:`addEntityGenerator`,
        typically used when either:

        (a) the :class:`.SimEntity` and/or :class:`.SimProcess` classes require
            additional initializer parameters, or
        (b) we wish to generate several classes of entity and/or process using a
            single interarrival distribution.

        addGeneratorPair() creates stream of entities via two passed generators:

        1. An entity generator, each iteration of which yields a new entity
           (and its SimProcess)
        2. An interarrival time generator, each iteration of which yields the
           time (:class:`.SimTime`) until the next work item is generated

        Args:
            entityGenerator:       A generator that yields :class:`.SimEntity`
                                   (or objects derived from ``SimEntity``)
            interarrivalGenerator: A generator that yields interarrival times
                                   (class :class:`.SimTime`)
        """
        self.__generatorPairs.append((entityGenerator, interarrivalGenerator))

        # As with addEntityGenerator(), we cannot actually create the
        # SimEntityGenerationEvent here, since this method may be called before
        # the simulation's random number streams have been initialized.

        #event = SimEntityGenerationEvent(self, entityGenerator, interarrivalGenerator)
        #event.register()


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
        #entity.initializePropertyValues()
        entity.process.start()
        self._time += next(self.__interarrivalGenerator)
        self.register()

if __name__ == '__main__':
    gdefin = SourceGeneratorDef()
    gdefin.interarrivalDistributionName = "uniform"
    print(gdefin.interarrivalDistributionParameters)
    print(gdefin.interarrivalParametersAsString())
