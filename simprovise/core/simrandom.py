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
# The simulator currently allows models to specify the use of up to 2000
# separate, independent random number streams per simulation run. It also 
# currently allows for up to 100 simulation replication runs.  This implies 
# the need for up to 2000x100 (200,000) separate, independent pseudo-random 
# number streams.
#
# While we might simply use 200,000 different seed values (one per stream),
# most pseudo-random number generators (PRNGs) do not provide any guarantees
# of independence for generators with arbitrarily different seeds. Good
# generators should have the characteristic that non-overlapping substreams of
# a single generated stream should pass tests of independence.
#
# The underlying pseudo-random bit generator currently in use is the PCG64DXSM
# generator provided by the numpy random module. This generator is reasonably
# efficient, has a sufficiently long period (2**128) and a very fast function
# for jumping ahead in a stream, allowing us to deterministically create 
# generators for an arbitrarily high number of large (> 2**50), sufficiently 
# independent substreams.
#
# In constrast, the Mersenne Twister (MT19377) PRNG that ships with the
# standard Python random module has an orders-of-magnitude slower jump ahead
# function; creating 200,000 independent generators through that method
# currently (2024) requires an hour or more on a reasonably powerful laptop.
# An earlier version of this module using the MT generator got around this by
# creating these generators offline and saving their states to a file to be
# read by the simulator at run time. Since each generator state consists of
# 624 unsigned ints, that file gets quite large for a large number of streams.
#
# The initialization method initializes a list of random.Random number 
# generator instances for a specified run/replication number, one per stream 
# (i.e., a list of 2000 RNGs).
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

import os
import itertools
from functools import partial
import numpy as np

import simprovise
from simprovise.core import SimError, SimLogging, SimTime, simtime
from simprovise.core.apidoc import apidoc, apidocskip

logger = SimLogging.get_logger(__name__)

_BASE_SEED = 1976
_BASE_BIT_GENERATOR = np.random.PCG64DXSM(seed=_BASE_SEED)

# The number of independent streams allowed per model (run) TODO: make configurable
_NSTREAMS = 2000

# The maximum number of replications (runs) supported TODO: make configurable
_MAX_REPLICATIONS = 100

# We obtain (sufficiently) independent streams by starting with a base
# generator and advancing/jumping ahead by a delta value
_STREAM_DELTA = pow(2,48) * 42

# To obtain a separate set of streams for each run, we start by jumping ahead of
# all the streams created for earlier runs
_RUN_DELTA = _STREAM_DELTA * _NSTREAMS

_RNG_INITIALIATION_ERROR = "Random Number Generator Initialization Error"
_RAND_PARAMETER_ERROR = "Invalid Psuedo-Random Distribution Parameter(s)"

# The psuedo-random-number generators for a single run, one for each
# substream in the run.
_rng = []

@apidoc        
def max_streams():
    """
    The number of separate pseudo-random-number streams supported for
    each model run.
    
    :return: The (maximum) number of supported separate/independent streams
    :rtype:  `int`
    
    """
    return _NSTREAMS
        
@apidoc        
def max_run_number():
    """
    The maximum run number supported by the initialized random number
    generator as configured. (Or, to put it another way, the maximum number
    of replications that can be executed)
    
    :return: maximum supported run number
    :rtype:  `int`
    
    """
    return _MAX_REPLICATIONS

@apidoc        
def min_run_number():
    """
    The minimum run number supported by the initialized random number
    generator- always 1
     
    :return: minimum supported run number
    :rtype:  `int`
    
    """
    return 1

@apidocskip
def initialize(run_number=1):
    """
    Create the independent random number generators (one per substream) for a
    specified run.  The generators are placed in module variable _rng, a
    single-dimensional list.
    
    :param run_number: The run number to initialize random number streams
                       for. must be in in range 1 - :func:`max_run_number`
    :type run_number:  `int`
    
    """
    nsubstreams = max_streams()
    logger.info("Initializing %d random number generators for run %d",
                nsubstreams, run_number)

    if run_number > max_run_number():
        msg = "Requested run number {0} exceeds the configured maximum number of runs ({1})"
        raise SimError(_RNG_INITIALIATION_ERROR, msg, run_number, max_run_number())

    global _rng

    # Create a new random number generator instance for each substream
    
    # start by jumping ahead based on the run number, and adding
    # one stream delta increment for good measure
    runjumps = (run_number - 1) * _RUN_DELTA + _STREAM_DELTA
    bit_generator = _BASE_BIT_GENERATOR.jumped(runjumps)
    
    # Create the list of generators, one for each possible stream
    # in the run.
    sdelta = _STREAM_DELTA
    ns = max_streams()    
    _rng = [np.random.Generator(bit_generator.jumped(i * sdelta)) for i in range(ns)]

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
    based on random number stream #4::
    
        SimDistribution.number_generator(SimDistribution.uniform, 100, 200, 4)

    In many (if not most) cases, these methods are being used to generate
    time values (class :class:`~.simtime.SimTime`) - e.g., we need a generator for
    interarrival times. If any of the arguments passed to 
    :meth:`number_generator` are :class:`~.simtime.SimTime` instances, the
    resulting generator will also return :class:`~.simtime.SimTime` instances
    (in the units of the first SimTime argument). The generator takes care
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
    def constant(constValue):
        """
        Returns a function that returns a specified constant value. For example,
        the below returns a generator that always yields 42::

            SimDistribution.number_generator(SimDistribution.constant, 42)

        :param constValue: The value to be returned by the function/generator
        :type constValue:  Any
        
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

        :param choices: A sequence of values to be returned, one at a time,
                        by the function/generator.
        :type choices:  Sequence
        
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

        :param choices:  A sequence of the possible values to be returned by
                         the function/generator.
        :type choices:   Sequence

        :param rnStream: Identifies the random stream to sample from.
        :type rnStream:  `int` in range [1 - :func:`max_streams`]

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
                        
        :param mean:     The mean value (or scale) of the desired exponentially
                         distributed sample.
        :type mean:      Either numeric or a :class:`~.simtime.SimTime`

        :param rnStream: Identifies the random stream to sample from.
        :type rnStream:  `int` in range [1 - :func:`max_streams`]
           
        """
        f = _rng[rnStream].exponential
        return partial(f, mean)
    functionDict["exponential"] = exponential

    @staticmethod
    def uniform(low, high, rnStream=1):
        """
        Returns a function that returns pseudo-random values from the uniform
        distribution with the specified bounds. Sample usage::

            SimDistribution.number_generator(SimDistribution.uniform,
                                            SimTime(10, simtime.SECONDS),
                                            SimTime(1.5, simtime.MINUTES),
                                            rnStream=12)
                                            
        :param low:      The low bound of the desired uniformly distributed sample. 
        :type low:       Either numeric or a :class:`~.simtime.SimTime`
                        
        :param high:     The high bound of the desired uniformly distributed sample. 
        :type high:      Either numeric or a :class:`~.simtime.SimTime`

        :param rnStream: Identifies the random stream to sample from.
        :type rnStream:  `int` in range [1 - :func:`max_streams`]

        """
        f = _rng[rnStream].uniform
        return partial(f, low, high)
    functionDict["uniform"] = uniform

    @staticmethod
    def triangular(low, mode, high, rnStream=1):
        """
        Returns a function that returns pseudo-random values from the triangular
        distribution with the specified bounds. Sample usage::

            SimDistribution.number_generator(SimDistribution.triangular, 2, 9, 4)

                                            
        :param low:      The low bound of the desired triangular distribution. 
        :type low:       Either numeric or a :class:`~.simtime.SimTime`
                        
        :param mode:     The mode of the desired triangular distribution. 
        :type mode:      Either numeric or a :class:`~.simtime.SimTime`
                        
        :param high:     The high bound of the desired triangular distribution. 
        :type high:      Either numeric or a :class:`~.simtime.SimTime`

        :param rnStream: Identifies the random stream to sample from.
        :type rnStream:  `int` in range [1 - :func:`max_streams`]

       """
        f = _rng[rnStream].triangular
        return partial(f, low, mode, high)
    functionDict["triangular"] = triangular

    @staticmethod
    def normal(mu, sigma, floor=0, rnStream=1):
        """
        Returns a function that returns pseudo-random values from the normal
        (Gaussian) distribution with the specified mu (mean) and sigma
        (standard deviation). Sample usage::

            SimDistribution.number_generator(SimDistribution.normal, 27, 4.5)

        Normal distribution values are not guaranteed to be positive, and
        negative values are obviously a problem in many situations (e.g.,
        interarrival or process times) A floor value of zero ensures that
        negative values are not returned - note that will change the
        effective mean and standard deviation of the distribution.

        :param mu:       The mean of the desired normal distribution. 
        :type mu:        Either numeric or a :class:`~.simtime.SimTime`
                        
        :param sigma:    The standard deviation of the desired normal distribution. 
        :type sigma:     Either numeric or a :class:`~.simtime.SimTime`
                        
        :param floor:    If not `None`, the floor return value. Defaults to
                         zero, which ensures that the sampling never returns a
                         negative value.
        :type floor:     `None`, numeric, or a :class:`~.simtime.SimTime`

        :param rnStream: Identifies the random stream to sample from.
        :type rnStream:  `int` in range [1 - :func:`max_streams`]      

        """
        f = _rng[rnStream].normal
        if floor is None:
            return partial(f, mu, sigma)
        else:
            # TODO I'm sure there is a more efficient way to do this...
            f1 = partial(f, mu, sigma)
            def f2():
                x = f1()
                return max(x, floor)
            return f2
    functionDict["normal"] = normal

    @staticmethod
    def weibull(a, rnStream=1):
        """
        Returns a function that returns pseudo-random values from the weibull
        distribution with the specified alpha (shape) parameter. Sample usage::

            SimDistribution.number_generator(SimDistribution.weibull, 2, 0.7)
                        
        :param a:        The shape of the of the desired weibull distribution.
        :type a:         Either numeric or a :class:`~.simtime.SimTime`

        :param rnStream: Identifies the random stream to sample from.
        :type rnStream:  `int` in range [1 - :func:`max_streams`]

        """
        f = _rng[rnStream].weibull
        return partial(f, a)
    functionDict["weibull"] = weibull

    @staticmethod
    def pareto(alpha, rnStream=1):
        """
        Returns a function that returns pseudo-random values from the pareto
        distribution with the specified alpha (shape) parameter. Sample usage::

            SimDistribution.number_generator(SimDistribution.pareto, 1.5)
                        
        :param alpha:    The shape of the of the desired pareto distribution.
        :type alpha:     Either numeric or a :class:`~.simtime.SimTime`

        :param rnStream: Identifies the random stream to sample from.
        :type rnStream:  `int` in range [1 - :func:`max_streams`]

        """
        f = _rng[rnStream].pareto
        return partial(f, alpha)
    functionDict["pareto"] = pareto

    @staticmethod
    def lognormal(mean, sigma, rnStream=1):
        """
        Returns a function that returns pseudo-random values from the log-
        normal distribution with the specified mean and sigma parameters.
        Sample usage::

            SimDistribution.number_generator(SimDistribution.lognormal, 20, 1.5)
                       
        :param mean:     The mean of the underlying normal distribution.
        :type mean:      Either numeric or a :class:`~.simtime.SimTime`
                        
        :param sigma:    The standard deviation of the underlying normal distribution.
        :type sigma:     Either numeric or a :class:`~.simtime.SimTime`

        :param rnStream: Identifies the random stream to sample from.
        :type rnStream:  `int` in range [1 - :func:`max_streams`]

        """
        if sigma <= 0:
            msg = "Invalid Lognormal sigma ({0}); value must be greater than zero"
            raise SimError(_RAND_PARAMETER_ERROR, msg, sigma)
        f = _rng[rnStream].lognormal
        return partial(f, mean, sigma)
    functionDict["lognormal"] = lognormal

    @staticmethod
    def beta(alpha, beta, rnStream=1):
        """
        Returns a function that returns pseudo-random values from the beta
        distribution with the specified alpha (shape) and beta (scale) parameters.
        
        :param alpha:    Shape parameter of the of the desired beta distribution.
                         Must be greater than zero.
        :type alpha:     Either numeric or a :class:`~.simtime.SimTime`
                       
        :param beta:     Scale parameter of the of the desired beta distribution.
                         Must be greater than zero.
        :type beta:      Either numeric or a :class:`~.simtime.SimTime`

        :param rnStream: Identifies the random stream to sample from.
        :type rnStream:  `int` in range [1 - :func:`max_streams`]
        
        """
        if alpha <= 0:
            msg = "Beta Distribution: invalid alpha value ({0}); alpha and beta parameters must be greater than zero"
            raise SimError(_RAND_PARAMETER_ERROR, msg, alpha)
        if beta <= 0:
            msg = "Beta Distribution: invalid beta value ({0}); alpha and beta parameters must be greater than zero"
            raise SimError(_RAND_PARAMETER_ERROR, msg, beta)
        f = _rng[rnStream].beta
        return partial(f, alpha, beta)
    functionDict["beta"] = beta

    @staticmethod
    def gamma(alpha, beta, rnStream=1):
        """
        Returns a function that returns pseudo-random values from the gamma
        distribution with the specified alpha (shape) and beta (scale) parameters.

        :param alpha:    Shape parameter of the of the desired gamma distribution.
                         Must be non-negative.
        :type alpha:     Either numeric or a :class:`~.simtime.SimTime`
                       
        :param beta:     Scale parameter of the of the desired gamma distribution.
                         Must be non-negative.
        :type beta:      Either numeric or a :class:`~.simtime.SimTime`

        :param rnStream: Identifies the random stream to sample from.
        :type rnStream:  `int` in range [1 - :func:`max_streams`]

        """
        if alpha < 0:
            msg = "Gamma Distribution: invalid alpha value ({0}); alpha and beta parameters must be non-negative"
            raise SimError(_RAND_PARAMETER_ERROR, msg, alpha)
        if beta < 0:
            msg = "Gamma Distribution: invalid beta value ({0}); alpha and beta parameters must be non-negative"
            raise SimError(_RAND_PARAMETER_ERROR, msg, beta)
        f = _rng[rnStream].gamma
        return partial(f, alpha, beta)
    functionDict["gamma"] = gamma

    @staticmethod
    def geometric(rho, rnStream=1):
        """
        Returns a function that returns pseudo-random values from the geometric
        distribution with the specified rho (probability of success of a single
        trial) parameter. Sample usage::

            SimDistribution.number_generator(SimDistribution.geometric, 0.35)

        :param rho:      The probability of success of an individual trial.
                         0.0 < rho <= 1.0
        :type rho:       `float`
                       
        :param rnStream: Identifies the random stream to sample from.
        :type rnStream:  `int` in range [1 - :func:`max_streams`]

        """
        try:
            rho = float(rho)
        except TypeError:
            msg = "Geometric Distribution: invalid (non-numeric) rho value ({0}); must be > 0 and <= 1"
            raise SimError(_RAND_PARAMETER_ERROR, msg, rho)
            
        if rho <= 0 or rho > 1:
            msg = "Geometric Distribution: invalid rho (probability) value ({0}); must > 0 and <= 1"
            raise SimError(_RAND_PARAMETER_ERROR, msg, rho)
        
        f = _rng[rnStream].geometric
        return partial(f, rho)
    functionDict["geometric"] = geometric

    @staticmethod
    def logistic(loc=0.0, scale=1.0, floor=0, rnStream=1):
        """
        Returns a function that returns pseudo-random values from the logistic
        distribution with the specified loc and scale parameters. Like the normal
        distribution, values are not guaranteed to be positive; a floor value of
        zero ensures that negative values are never returned.

        :param loc:      Loc parameter of the distribution. Defaults to zero.
        :type loc:       Either numeric or a :class:`~.simtime.SimTime`
                       
        :param scale:    Scale parameter of the of the distribution Defaults to 1.
        :type scale:     Either numeric or a :class:`~.simtime.SimTime`
                        
        :param floor:    If not `None`, the floor return value. Defaults to
                         zero, which ensures that the sampling never returns a
                         negative value.
        :type floor:     `None`, numeric, or a :class:`~.simtime.SimTime`
                       
        :param rnStream: Identifies the random stream to sample from.
        :type rnStream:  `int` in range [1 - :func:`max_streams`]

        """
        f = _rng[rnStream].logistic
        if floor is None:
            return partial(f, loc, scale)
        else:
            # TODO I'm sure there is a more efficient way to do this...
            f1 = partial(f, loc, scale)
            def f2():
                x = f1()
                return max(x, floor)
            return f2
    functionDict["logistic"] = logistic    

    @staticmethod
    def binomial(n, rho, rnStream=1):
        """
        Returns a function that returns pseudo-random values from the binomial
        distribution with the specified n (number of trials) and rho (probability of
        success of a single trial) parameter. Sample usage::

            SimDistribution.number_generator(SimDistribution.binomial, 5, 0.35)

        :param n:       The number of trials, >= 0
        :type n:       `int`
        
        :param rho:      The probability of success of an individual trial.
                         0.0 <= rho <= 1.0
        :type rho:       `float`
                       
        :param rnStream: Identifies the random stream to sample from.
        :type rnStream:  `int` in range [1 - :func:`max_streams`]

        """
        try:
            n = int(n)
        except TypeError:
            msg = "binomial Distribution: invalid (non-numeric) n value ({0}); must be >= 0 "
            raise SimError(_RAND_PARAMETER_ERROR, msg, n)
        
        try:
            rho = float(rho)
        except TypeError:
            msg = "binomial Distribution: invalid (non-numeric) rho value ({0}); must be >= 0 and <= 1"
            raise SimError(_RAND_PARAMETER_ERROR, msg, rho)
                      
        if n < 0:
            msg = "Geometric Distribution: invalid n value ({0}); must >= 0"
            raise SimError(_RAND_PARAMETER_ERROR, msg, n)
        if rho < 0 or rho > 1:
            msg = "Geometric Distribution: invalid rho (probability) value ({0}); must >= 0 and <= 1>"
            raise SimError(_RAND_PARAMETER_ERROR, msg, rho)
        
        f = _rng[rnStream].geometric
        return partial(f, n, rho)
    functionDict["binomial"] = binomial
    
    # TODO Add  binomial, multinomial, poisson, power distributions from numpy

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
                    return a.to_units(timeUnits).value
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

    gen = SimDistribution.number_generator(SimDistribution.triangular, SimTime(10), 35, SimTime(1, simtime.MINUTES))
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


    gen = SimDistribution.number_generator(SimDistribution.normal, SimTime(10), 4)
    total = 0
    negativeCount = 0
    cpustart = time.process_time()
    for i in range(1000):
        nextVal = next(gen)
        total += nextVal
        if nextVal < 0: negativeCount += 1
    cpuend = time.process_time()
    print("SimDistribution number_generator gaussian time", cpuend - cpustart, negativeCount, "mean value:", total / 1000)

