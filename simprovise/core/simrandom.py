#===============================================================================
# MODULE simrandom
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines an initialize() function to initialize random number generation for
# a specified simulation run (run number) and the SimDistribution class, which
# provides a set of static methods for creating number generators (both
# pseudo-random and transparently deterministic, e.g. round-robin).
#
# The simulator currently allows models to specify the use of up to 100
# separate (and hopefully independent) random number streams per simulation run.
# It also currently allows for up to 100 simulation runs.  This implies the
# need for up to 100x100 (10,000) separate, independent number streams.
#
# While we might simply use 10,000 different seed values, random's underlying
# Mersenne Twister RNG implementation does not make any general guarantees
# regarding the independence of RNG instances initialized with different seeds.
# We therefore rely on an offline process that uses a single random number
# stream, jumps ahead in that stream by a very large value (2 to the 50th)
# 10,000 times, saving the generator state (624 int values) after each jump
# into a numpy .npy file, containing a 100x100x624 array.  We rely on the fact
# that:
# a) in a high quality random number stream (such as those create by the
#    Mersenne Twister), discrete substreams should be highly independent, and
# b) The long period of MT 19937 (2e19937) allows for very long substreams,
#    and
# c) Substreams of length 2e50 ought to be long enough for any application.
#
# This module reads that file back into a numpy array, and initialize uses
# the 100x624 slice corresponding to the desired run to initialize a list of
# 100 random.Random instances (one per stream).  All in all, this is hopefully
# a good way to provide a reasonable guarantee of substream independence
# while continuing to use the default MT19937 random number generator that
# ships with the Python standard library.
#
# See http://www.howardklein.net/?p=157#more-157 for a more complete discussion.
#
# The initialization method initializes a list of random.Random number generator
# instances, one per stream (i.e., a list of 100 RNGs).
#
# SimDistribution provides the static method number_generator() that returns
# a Python generator function that generates values in a (possibly)
# pseudo-random distribution. For example:
#
#    SimDistribution.number_generator(SimDistribution.uniform, 100, 200, 4)
#
# returns a generator that uses the RNG for substream 4 (as created by
# initialize()) to generate uniformly distributed values in the range
# [100,200].  SimDistribution also provides static methods that enable the UI
# to inform the user of available distributions and their arguments, as well
# as facilitate the serialization of distribution specifications in a simulation
# model definition file.
#===============================================================================
__all__ = ['SimDistribution']

import random, os
import itertools
from functools import partial
import numpy as np

import simprovise
from simprovise.core import SimError, SimLogging, SimTime, simtime
from simprovise.core.apidoc import apidoc, apidocskip

logger = SimLogging.get_logger(__name__)

_STATE_SIZE = 624

# Full path of file containing initial states for all 10,000 random number
# streams. Use os.path functions to assemble the name in a
# platform-independent way.
_RNG_STATES_FILENAME = os.path.join(
    os.path.dirname(os.path.abspath(simprovise.__file__)),
   'random_initialization',
    'mt19937_states.npy')

_READ_ERROR = "Random Number Generator State File Read Error"
_RNG_INITIALIATION_ERROR = "Random Number Generator Initialization Error"
_RAND_PARAMETER_ERROR = "Invalid Psuedo-Random Distribution Parameter(s)"

_rng = []

def _read_state_file():
    """
    The initial states for all generators for all runs are maintained in a
    numpy 3-D array, pre-built and stored in a .npy file. The array is of the
    form state_array[run][substream][statevalue]; there are 624 state values
    per run/substream. (In other words if we have a maximum of x runs and y
    substreams per run, the array will be of dimension [x,y,624])

    _readStateFile() reads the Random Generator State initialization file
    into a 3-d numpy array. The array is checked and returned. An exception
    is raised if the file array cannot be read or it's format is invalid. (It
    must be three dimensional, and the final dimension must be 624)
    """
    statefile = _RNG_STATES_FILENAME
    logger.info("Reading initial random number generator states from file %s...",
                statefile)

    try:
        state_array = np.load(statefile)
    except IOError:
        logger.fatal("Failure reading random state initialization file %s",
                     statefile)
        raise SimError(_READ_ERROR, "Failure opening/reading file")

    # pylint thinks that state_array is an NpzFile (which doesn't have a shape)
    # pylint: disable=E1101
    if len(state_array.shape) != 3:
        logger.fatal("Random state initialization file %s is not a 3-dimensional array",
                     statefile)
        raise SimError(_READ_ERROR, "state array is not 3-dimensional")

    if state_array.shape[2] != _STATE_SIZE:
        logger.fatal("Random state initialization file %s state length is not %d",
                     statefile, _STATE_SIZE)
        raise SimError(_READ_ERROR, "state array state length is invalid")

    return state_array

# Module variable holding initial random number generator state for all runs
# and all streams. Lazily initialized by _initializeStateArrayIfRequired().
# Used primarily by initialize() to set the state for all RNGs for a specified
# run.
_rng_state_array = None

def _initialize_state_array_if_required():
    """
    Read the initial states for all random number generators (all runs, all
    streams) into module variable _rng_state_array
    """
    global _rng_state_array
    if _rng_state_array is None:
        _rng_state_array = _read_state_file()

@apidocskip
def initialize(run_number=1):
    """
    Create the independent random number generators (one per substream) for a
    specified run.  The generators are placed in module variable _rng, a
    single-dimensional list.

    The state data used to initialize the generators are a slice of the
    state array read by _readStateFile().
    """
    _initialize_state_array_if_required() # read rng state array if necessary

    # pylint thinks that state_array is an NpzFile (which doesn't have a shape)
    # pylint: disable=E1101
    nruns = _rng_state_array.shape[0]
    nsubstreams = _rng_state_array.shape[1]
    logger.info("Initializing %d random number generators for run %d",
                nsubstreams, run_number)

    if run_number > nruns:
        msg = "Requested run number {0} exceeds the number of runs {1} defined in the random initialization file"
        raise SimError(_RNG_INITIALIATION_ERROR, msg, run_number, nruns)

    runindex = run_number - 1

    global _rng

    # Create a new random number generator instance for each substream
    _rng = [random.Random() for i in range(nsubstreams)]

    # For each substream, extract the initial state data from the array,
    # massage it, and use it to set the initial state of the corresponding
    # random number generator instance.
    for i in range(nsubstreams):
        # Convert the array of numpy.uint32s to a list of ints
        state_list = [int(x) for x in _rng_state_array[runindex][i]]

        # Append the required value of 624 to the list
        state_list.append(_STATE_SIZE)

        # Define the required internal state tuple and use it to set the state for
        # the corresponding RNG instance.
        rng_state = (3, tuple(state_list), None)
        _rng[i].setstate(rng_state)

@apidoc
class SimDistribution(object):
    """
    The SimDistribution class is a namespace defining a number of static
    methods used to generate values from both deterministic and pseudo-random
    distributions.

    Most of the public static methods are functions that (when parameterized
    with their passed arguments) return functions that sample from a
    specified distribution. uniform(a,b), for example, returns a function
    that produces numbers uniformly distributed between a and b.

    There are two methods (:meth:`~function` and :meth:`.function_names`) provided
    for the benefit of a UI. :meth:`function_names` provides a sequence of
    distribution functions by name (e.g., for populating a list box), while
    :meth:`function` maps those names back to a function object.

    The final method, :meth:`number_generator`, returns a Python generator using 
    one of the above described methods. It is passed both a reference to one of
    these functions and it's parameters. The code below returns a generator
    yielding pseudo-random values uniformly distributed between 100 and 200,
    based on random number stream #4:
    
    ``SimDistribution.number_generator(SimDistribution.uniform, 100, 200, 4)``

    In many (if not most) cases, these methods are being used to generate
    time values (class :class:`~.simtime.SimTime`) - e.g., we need a generator for
    interarrival times. If any of the arguments passed to
    ``SimDistribution.number_generator()`` are :class:`~.simtime.SimTime`
    instances, the resulting generator will also return SimTime instances
    (in the units of the first SimTime argument) The generator takes care
    of unit conversion - i.e., it is OK to pass SimTime arguments with 
    ifferent time units. For example, the following returns a generator
    yielding SimTime values uniformly distributed between 30 and 120 seconds:
    
    .. code-block:: python
    
       SimDistribution.number_generator(SimDistribution.uniform,
                                        SimTime(30, simtime.SECONDS),
                                        SimTime(2, simtime.MINUTES))

    Finally, note that in a few cases (:meth:`round_robin`, :meth:`choice`)
    the values returned can be non-numeric and non-time (despite the name
    'number_generator'). We could, for example, define an entity generator (for
    a :class:`SimEntitySource` object) that instantiates a randomly-selected
    SimEntity subclass via:

    .. code-block:: python

       entity_classes = (MyEntity1, MyEntity2, MyEntity3)
       et_generator = SimDistribution.number_generator(SimDistribution.choice,
                                                       entity_classes)
 
    """
    functionDict = {}

    @staticmethod
    def function_names():
        """
        Returns a sequence of the available (defined) distribution function names
        """
        return SimDistribution.functionDict.keys()

    @staticmethod
    def function(functionName):
        """
        Returns the SimDistribution distribution function mapped to the passed name
        """
        try:
            # Because the function is actually wrapped via the staticmethod
            # decorator, we need to return the underlying function via the
            # staticmethod's __func__ attribute. see
            # http://chimera.labs.oreilly.com/books/1230000000393/ch09.html#_discussion_146
            return SimDistribution.functionDict[functionName].__func__
        except KeyError:
            msg = "{0} is not a valid/defined distribution function"
            raise SimError("SimDistribution Error", msg, functionName)

    @staticmethod
    def n_random_number_streams():
        """
        Returns the number of initialized random number streams. By default,
        this is 100.
        """
        _initialize_state_array_if_required() # read rng state array if necessary
        # pylint thinks that state_array is an NpzFile (which doesn't have a shape)
        # pylint: disable=E1101
        return _rng_state_array.shape[1]

    @staticmethod
    def constant(constValue):
        """
        Returns a function that returns a specified constant value. For example,
        the below returns a generator that always yields 42::

            SimDistribution.number_generator(SimDistribution.constant, 42)

        Args:
            constValue: The value (any type) to be returned by the function/
                        generator
        """
        def f(): return constValue
        return f
    functionDict["constant"] = constant

    @staticmethod
    def round_robin(choices):
        """
        Returns a function that returns values from a passed sequence of
        choices, cycling through them deterministically. For example, the
        below returns a generator that yields the sequence (2,4,6,2,4,6,2...)::

            SimDistribution.number_generator(SimDistribution.roundRobin, (2,4,6))

        Args:
            choices: A sequence of values to be returned, one at a time,
                     by the function/generator.
        """
        cycle = itertools.cycle(choices)
        def f():
            return next(cycle)
        return f
    functionDict["roundRobin"] = round_robin

    @staticmethod
    def choice(choices, rnStream=1):
        """
        Returns a function that returns a pseudo-randomly chosen value from
        the passed sequence of choices. The below returns a generator that
        yields a random sequence containing only the values 2, 4 or 6::

            SimDistribution.number_generator(SimDistribution.choice, (2,4,6))

        Args:
            choices:        A sequence of the possible values to be returned by
                            the function/generator.
            rnStream (int): Identifies the random stream to sample from.
                            Should be in range [1 - :meth:`nRandomNumberStreams`]
        """
        f = _rng[rnStream].choice
        return partial(f, choices)
    functionDict["choice"] = choice

    @staticmethod
    def exponential(mean, rnStream=1):
        """
        Returns a function that returns pseudo-random values from the
        exponential distribution with a specified mean. To generate
        exponentially distributed values with a mean of 42 use::

            SimDistribution.number_generator(SimDistribution.exponential, 42)

        Args:
            mean:           The mean value of the desired exponentially
                            distributed sample. May be either numeric or a
                            :class:`SimTime` instance
            rnStream (int): Identifies the random stream to sample from.
                            Should be in range [1 - :meth:`nRandomNumberStreams`]
        """
        f = _rng[rnStream].expovariate
        return partial(f, 1.0 /  mean)
    functionDict["exponential"] = exponential

    @staticmethod
    def uniform(a, b, rnStream=1):
        """
        Returns a function that returns pseudo-random values from the uniform
        distribution with the specified bounds. Sample usage::

            SimDistribution.number_generator(SimDistribution.uniform,
                                            SimTime(10, simtime.SECONDS),
                                            SimTime(1.5, simtime.MINUTES),
                                            rnStream=12)

        Args:
            a:              The low bound of the desired uniformly distributed
                            sample. May be either numeric or a :class:`SimTime`
                            instance
            b:              The high bound of the desired uniformly distributed
                            sample. May be either numeric or a :class:`SimTime`
                            instance
            rnStream (int): Identifies the random stream to sample from.
                            Should be in range [1 - :meth:`nRandomNumberStreams`]
        """
        f = _rng[rnStream].uniform
        return partial(f, a, b)
    functionDict["uniform"] = uniform

    @staticmethod
    def triangular(low, high, mode, rnStream=1):
        """
        Returns a function that returns pseudo-random values from the triangular
        distribution with the specified bounds. Sample usage::

            SimDistribution.number_generator(SimDistribution.triangular, 2, 9, 4)

        Args:
            low:            The low bound of the desired triangular distribution.
                            May be either numeric or a :class:`SimTime` instance
            high:           The high bound of the desired triangular distribution.
                            May be either numeric or a :class:`SimTime` instance
            mode:           The mode of the desired triangular distribution.
                            May be either numeric or a :class:`SimTime` instance
            rnStream (int): Identifies the random stream to sample from.
                            Should be in range [1 - :meth:`nRandomNumberStreams`]
       """
        f = _rng[rnStream].triangular
        return partial(f, low, high, mode)
    functionDict["triangular"] = triangular

    @staticmethod
    def gaussian(mu, sigma, floor=0, rnStream=1):
        """
        Returns a function that returns pseudo-random values from the gaussian
        distribution with the specified mu (mean) and sigma (standard deviation).
        Sample usage::

            SimDistribution.number_generator(SimDistribution.gaussian, 27, 4.5)

        Gaussian distribution values are not guaranteed to be positive, and
        negative values are obviously a problem in many situations (e.g.,
        interarrival or process times) A floor value of zero ensures that
        negative values are not returned - note that will change the
        effective mean and standard deviation of the distribution.

        Args:
            mu:             The mean value of the desired gaussian distribution.
                            May be either numeric or a :class:`SimTime` instance
            sigma:          The std deviation of the desired gaussian distribution.
                            May be either numeric or a :class:`SimTime` instance
            rnStream (int): Identifies the random stream to sample from.
                            Should be in range [1 - :meth:`nRandomNumberStreams`]
        """
        f = _rng[rnStream].gauss
        if floor is None:
            return partial(f, mu, sigma)
        else:
            # TODO I'm sure there is a more efficient way to do this...
            f1 = partial(f, mu, sigma)
            def f2():
                x = f1()
                return max(x, floor)
            return f2
    functionDict["gaussian"] = gaussian

    @staticmethod
    def weibull(alpha, beta, rnStream=1):
        """
        Returns a function that returns pseudo-random values from the weibull
        distribution with the specified alpha (scale) and beta (shape)
        parameters. Sample usage::

            SimDistribution.number_generator(SimDistribution.weibull, 2, 0.7)

        Args:
            alpha:          The scale parameter of the desired weibull distribution.
                            May be either numeric or a :class:`SimTime` instance
            beta:           The shape paramter of the desired triangular distribution.
                            May be either numeric or a :class:`SimTime` instance
            rnStream (int): Identifies the random stream to sample from.
                            Should be in range [1 - :meth:`nRandomNumberStreams`]
        """
        f = _rng[rnStream].weibullvariate
        return partial(f, alpha, beta)
    functionDict["weibull"] = weibull

    @staticmethod
    def pareto(alpha, rnStream=1):
        """
        Returns a function that returns pseudo-random values from the pareto
        distribution with the specified alpha (shape) parameter. Sample usage::

            SimDistribution.number_generator(SimDistribution.pareto, 1.5)

        Args:
            alpha:          The shape parameter of the desired pareto distribution.
                            May be either numeric or a :class:`SimTime` instance
            rnStream (int): Identifies the random stream to sample from.
                            Should be in range [1 - :meth:`nRandomNumberStreams`]
        """
        f = _rng[rnStream].paretovariate
        return partial(f, alpha)
    functionDict["pareto"] = pareto

    @staticmethod
    def lognormal(mu, sigma, rnStream=1):
        """
        Returns a function that returns pseudo-random values from the log-
        normal distribution with the specified mu and sigma parameters.

        Args:
            mu:             The location parameter of the desired lognormal distribution.
                            May be either numeric or a :class:`SimTime` instance
            sigma:          The scale parameter of the desired lognormal distribution.
                            May be either numeric or a :class:`SimTime` instance,
                            but must be greater than zero
            rnStream (int): Identifies the random stream to sample from.
                            Should be in range [1 - :meth:`nRandomNumberStreams`]
        """
        if sigma <= 0:
            msg = "Invalid Lognormal sigma ({0}); value must be greater than zero"
            raise SimError(_RAND_PARAMETER_ERROR, msg, sigma)
        f = _rng[rnStream].lognormvariate
        return partial(f, mu, sigma)
    functionDict["lognormal"] = lognormal

    @staticmethod
    def beta(alpha, beta, rnStream=1):
        """
        Returns a function that returns pseudo-random values from the beta
        distribution with the specified alpha and beta parameters.

        Args:
            alpha:          Shape parameter of the desired beta distribution.
                            May be either numeric or a :class:`SimTime` instance.
                            Must be greater than zero
            beta:           Shape parameter of the desired beta distribution.
                            May be either numeric or a :class:`SimTime` instance
                            Must be greater than zero
            rnStream (int): Identifies the random stream to sample from.
                            Should be in range [1 - :meth:`nRandomNumberStreams`]
        """
        if alpha <= 0:
            msg = "Beta Distribution: invalid alpha value ({0}); alpha and beta parameters must be greater than zero"
            raise SimError(_RAND_PARAMETER_ERROR, msg, alpha)
        if beta <= 0:
            msg = "Beta Distribution: invalid beta value ({0}); alpha and beta parameters must be greater than zero"
            raise SimError(_RAND_PARAMETER_ERROR, msg, beta)
        f = _rng[rnStream].betavariate
        return partial(f, alpha, beta)
    functionDict["beta"] = beta

    @staticmethod
    def gamma(alpha, beta, rnStream=1):
        """
        Returns a function that returns pseudo-random values from the gamma
        distribution with the specified alpha and beta parameters.

        Args:
            alpha:          Alpha parameter of the desired gamma distribution.
                            May be either numeric or a :class:`.SimTime` instance.
                            Must be greater than zero
            beta:           Beta parameter of the desired gamma distribution.
                            May be either numeric or a :class:`.SimTime` instance
                            Must be greater than zero
            rnStream (int): Identifies the random stream to sample from.
                            Should be in range [1 - :meth:`nRandomNumberStreams`]
        """
        if alpha <= 0:
            msg = "Gamma Distribution: invalid alpha value ({0}); alpha and beta parameters must be greater than zero"
            raise SimError(_RAND_PARAMETER_ERROR, msg, alpha)
        if beta <= 0:
            msg = "Gamma Distribution: invalid beta value ({0}); alpha and beta parameters must be greater than zero"
            raise SimError(_RAND_PARAMETER_ERROR, msg, beta)
        f = _rng[rnStream].gammavariate
        return partial(f, alpha, beta)
    functionDict["gamma"] = gamma

    @staticmethod
    def number_generator(func, *args, **kwargs):
        """
        Creates and returns a number generator using the passed function and
        arguments. The passed function will typically be one of the
        distribution methods defined by this class. These functions, when
        called with the passed arguments (or modified arguments, as described
        below) return a (related) function that will then be called by the
        generator to create the yielded values.
        
        For example, the code below returns a generator yielding pseudo-random
        values uniformly distributed between 100 and 200, based on random number
        stream #4:
    
        ``SimDistribution.number_generator(SimDistribution.uniform, 100, 200, 4)``

        If any of the passed arguments are :class:`~.simtime.SimTime` instances,
        the generator will yield :class:`~.simtime.SimTime` instances. In that
        case, the passed arguments are, in effect, converted to the same units
        (the unit of the first :class:`~.simtime.SimTime` encountered), and the
        resulting scalar values are passed to func. The generator then converts
        the generated values back into :class:`~.simtime.SimTime` instances and
        yields them. In this way, the number functions do not have to be aware of
        :class:`~.simtime.SimTime`.
        
        """
        # TODO: if any argument is a SimTime, then they all should be.
        # Check and raise if that is not the case.
        # Also... if the arguments are SimTime, it is probably safe to assume that
        # the returned value of the generator should never be negative.
        isSimTimeGenerator = False
        timeUnits = None

        # Create a (possibly) modified argument list.
        # If any of the arguments are SimTime instances, convert the argument
        # to a scalar value, using the time unit of the first SimTime
        # argument we encounter in the argument list. We hold onto that time
        # unit, so that the generator yields SimTime instances of that unit.
        # (Our assumption is that if any arguments are SimTime instances,
        # than the intention is to to generate time values)
        def modifiedArg(a):
            nonlocal timeUnits
            nonlocal isSimTimeGenerator
            if isinstance(a, SimTime):
                isSimTimeGenerator = True
                if timeUnits is None:
                    timeUnits = a.units
                    return a.value
                else:
                    return a.toUnits(timeUnits).value
            else:
                return a

        # Modify the positional arguments
        modifiedArgs = [modifiedArg(a) for a in args]

        # Modify the keyword arguments
        modifiedKwargs = {}
        for key in kwargs:
            modifiedKwargs[key] = modifiedArg(kwargs[key])

        # Call the passed function with the modified arguments, which should
        # return another function to be used by the generator.
        generatorFunc = func(*modifiedArgs, **modifiedKwargs)

        if isSimTimeGenerator:
            while True:
                yield SimTime(generatorFunc(), timeUnits)
        else:
            while True:
                yield generatorFunc()


if __name__ == '__main__':
    import time
    initialize()
    for n in SimDistribution.function_names():
        print(n)

    gen = SimDistribution.number_generator(SimDistribution.constant, 10)
    total = 0
    cpustart = time.process_time()
    for i in range(100000):
        total += next(gen)
    cpuend = time.process_time()
    print("SimDistribution number_generator constant scalar", cpuend - cpustart, "mean value:", total / 100000)

    gen = SimDistribution.number_generator(SimDistribution.exponential, 10)
    total = 0
    cpustart = time.process_time()
    for i in range(100000):
        total += next(gen)
    cpuend = time.process_time()
    print("SimDistribution number_generator exponential scalar", cpuend - cpustart, "mean value:", total / 100000)

    gen = SimDistribution.number_generator(SimDistribution.exponential, SimTime(9), 2)
    total = SimTime(0)
    cpustart = time.process_time()
    for i in range(100000):
        total += next(gen)
    cpuend = time.process_time()
    print("SimDistribution number_generator exponential SimTime", cpuend - cpustart, "mean value:", total / 100000)

    gen = SimDistribution.number_generator(SimDistribution.uniform, SimTime(10), SimTime(1, simtime.MINUTES))
    total = 0
    cpustart = time.process_time()
    for i in range(100000):
        total += next(gen)
    cpuend = time.process_time()
    print("SimDistribution number_generator uniform time", cpuend - cpustart, "mean value:", total / 100000)

    gen = SimDistribution.number_generator(SimDistribution.triangular, SimTime(10), SimTime(1, simtime.MINUTES), 35)
    total = 0
    cpustart = time.process_time()
    for i in range(100000):
        total += next(gen)
    cpuend = time.process_time()
    print("SimDistribution number_generator triangular time", cpuend - cpustart, "mean value:", total / 100000)

    args1 = [SimTime(10)]
    kwargs1 = {}
    kwargs1['high'] = SimTime(1, simtime.MINUTES)
    kwargs1['mode'] = 35
    gen = SimDistribution.number_generator(SimDistribution.triangular, *args1, **kwargs1)
    total = 0
    cpustart = time.process_time()
    for i in range(100000):
        total += next(gen)
    cpuend = time.process_time()
    print("SimDistribution number_generator triangular time", cpuend - cpustart, "mean value:", total / 100000)


    gen = SimDistribution.number_generator(SimDistribution.gaussian, SimTime(10), 4)
    total = 0
    negativeCount = 0
    cpustart = time.process_time()
    for i in range(1000):
        nextVal = next(gen)
        total += nextVal
        if nextVal < 0: negativeCount += 1
    cpuend = time.process_time()
    print("SimDistribution number_generator gaussian time", cpuend - cpustart, negativeCount, "mean value:", total / 1000)

    r = random.Random()
    n = pow(10, 6)
    cpustart = time.process_time()

    for i in range(n):
        r.random()
    cpuend = time.process_time()
    s = r.getstate()
    #print(s)
    print("random() time", cpuend - cpustart, "mean value:", (cpuend - cpustart) / 100, type(s))

