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
# We use NumPy's random module for both random number generation and
# probability distribution sampling (via those generators). NumPy provides
# a number of generators (or to be precise, bit generators); we are currently
# using the PCG64DXSM bit generator, which is likely to become the default
# generator in a future NumPy release. This generator is reasonably
# efficient, has a sufficiently long period (2**128) and a very fast function
# for jumped() implementation, which is our chosen technique for generating
# multiple independent streams (see below).
#
# The simulator allows models to use essentially any number of independent
# random number streams per simulation run; the maximum number is
# configurable, and currently defaults to 2000. The maximum number of
# independent replications allowed is also configurable, with a current
# default of 100. With those defaults, the simulator requires up to 200,000
# (2000 x 100) independent random number streams.
#
# NumPy recommends the use of either spawn() or jumped() to generate
# independent bit generators from a single base generator; see:
#
# https://numpy.org/doc/stable/reference/random/parallel.html#id8
#
# We are currently using jumped(), though spawn should work as well. 
# When we think of the 2000 x 100 array of bit generators, we can think of 
# them as being created by a 2000 x 100 array of jumps; the first row is 0-1999, 
# the second 2000-3999, and so on. The first generator in the first row 
# (run 1, stream 1) is zero jumps from the base generator while he last 
# generator in that row (run 1, stream 2000) is 1999 jumps from the base.
# And run 2, stream 1 is 2000 jumps from the base.
#
# This technique should support more than sufficient stream independence
# for millions of streams, which should be adequate for our purposes.
#
# SimDistribution provides static methods that return generators for a
# variety of NumPy-implemented probablility distributions. When it makes sense,
# distribution parameters may be specified as SimTime instances. When the
# client supplies a SimTime parameter value, the generated values will all be
# SimTime objects (in the time unit of the first SimTime parameter supplied).
# When no SimTime parameters are specified by the client, the generated values
# are all scalar numerics.
#
# Each SimDistribution method includes a streamNum parameter that allows the
# client to specify a specific stream to be sampled from. This allows
# modeling code to ensure that different model components sample from
# different, independent random number streams. The default streamNum is 1.
# 
# SimDistribution also provides static methods that enable a UI to inform the 
# user of available distributions and their arguments, as well as facilitate 
# the serialization of distribution specifications in a simulation model 
# definition file.
#===============================================================================
__all__ = ['SimDistribution']

import os
import itertools
from functools import partial
import numpy as np

from simprovise.core import SimError
from simprovise.core.simtime import SimTime
from simprovise.core.simlogging import SimLogging

from simprovise.core.simtime import Unit as tu
from simprovise.core.apidoc import apidoc, apidocskip
import simprovise.core.configuration as simconfig

logger = SimLogging.get_logger(__name__)

# Base seed generated via a one-time offline call to secrets.randbits(), per
# https://numpy.org/doc/stable/reference/random/index.html#recommend-secrets-randbits
_BASE_SEED = 339697402671268427564149969060011333618
_BASE_BIT_GENERATOR = np.random.PCG64DXSM(seed=_BASE_SEED)

# The number of independent streams allowed per model (run) 
_NSTREAMS = simconfig.get_PRNstreams_per_run()
logger.info("Initialized random number streams per run to %d based on configuration setting",
            _NSTREAMS)

# The maximum number of replications (runs) supported 
_MAX_REPLICATIONS = simconfig.get_max_replications()
logger.info("Initialized maximum replications/max run number to %d based on configuration setting",
            _MAX_REPLICATIONS)

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

    if run_number <= 0:
        msg = "Requested run number ({0}) must be greater than zero"
        raise SimError(_RNG_INITIALIATION_ERROR, msg, run_number)

    if run_number > max_run_number():
        msg = "Requested run number {0} exceeds the configured maximum number of runs ({1})"
        raise SimError(_RNG_INITIALIATION_ERROR, msg, run_number, max_run_number())

    global _rng

    # Create a new random number generator instance for each substream
    
    # start by jumping ahead based on the run number, and adding
    # one stream delta increment for good measure
    #runjumps = (run_number - 1) * _RUN_DELTA + _STREAM_DELTA
    
    # We need separate, independent bit generators for each stream in each run.
    # (Each bit generator is used to initialize a separate NumPy Generator 
    # object, which actually generates the psuedo-random number stream.)
    # We can think of that as a max_streams by max_runs array of bit
    # generators. Each row (the generators for a single run) is created by
    # jumping from the first generator in the row (stream 1). The first
    # bit generator for run 1 is the base bit generator; for subsequent runs,
    # we must do max_streams jumps per run.
    # Note:
    # We could use NumPy's spawn() instead; see
    # https://numpy.org/doc/stable/reference/random/parallel.html#id8
    # for a discussion of methods for generating multiple independent
    # streams. Our choice of the jumped() technique is arbitrary
    ns = max_streams()    
    runjumps = (run_number - 1) * ns
    run_bit_generator = _BASE_BIT_GENERATOR.jumped(runjumps)
    
    # Create the list of generators, one for each possible stream
    _rng = [np.random.Generator(run_bit_generator.jumped(i)) for i in range(ns)]


def get_random_generator(streamNum=1):
    """
    Returns the pseudo-random number generator for a specified stream,
    for client code that needs to access that directly (e.g., to use
    a distribution not supported by :class:`SimDistribution`).
    
    :param streamNum: Identifies the random stream to sample from.
    :type streamNum:  `int` in range [1 - :func:`max_streams`]
    
    :return: The requested PRNG
    :rtype:  :class:`numpy.random.Generator`
    """
    # validate the selected random number stream
    if streamNum <= 0 or streamNum > max_streams():
        msg = "Requested stream number ({0}) must be in range 1 - {1}"
        raise SimError(_RAND_PARAMETER_ERROR, msg, streamNum, max_streams())

    return _rng[streamNum-1]

@apidoc
class SimDistribution(object):
    """
    The SimDistribution class is a namespace defining a number of static
    methods used to generate values from both deterministic and pseudo-random
    distributions.

    These methods (when parameterized with their passed arguments) return
    generators that yield samples from a specified distribution.
    ``uniform(a, b, streamNum=5)``, for example, returns a generator that
    produces numbers uniformly distributed between ``a`` and ``b`` based
    on sampling from random number stream ``5``. All of the methods for
    pseudo-random probability distributions take a ``streamNum`` parameter,
    which defaults to ``1``.

    In many (if not most) cases, these methods are being used to generate
    time values (class :class:`~.simtime.SimTime`) - e.g., if we need a
    generator for interarrival times. If any of the arguments passed to 
    a ``SimDistribution`` method are :class:`~.simtime.SimTime` instances, the
    resulting generator will also return :class:`~.simtime.SimTime` instances
    (in the units of the first SimTime argument). The generator takes care
    of unit conversion - i.e., it is OK to pass SimTime arguments with 
    different time units. For example, the following returns a generator
    yielding SimTime values uniformly distributed between 30 and 120 seconds::
    
       SimDistribution.uniform(SimTime(30, tu.SECONDS),
                               SimTime(2, tu.MINUTES))

    Additional notes on the use of :class:`~.simtime.SimTime` parameters:
    
    - When provided multiple ``SimTime`` parameters, the generated values will
      have the units of the first SimTime provided - e.g. the example above
      will generate ``SimTime`` values in ``SECONDS``.
      
    - If there is at least one SimTime parameter value, any scalar parameter
      values will be assumed to be SimTime values with the same units as the
      first ``SimTime`` parameter. e.g., for the following call, the second
      parameter value will be assumed to be 200 seconds::
    
          SimDistribution.uniform(SimTime(30, tu.SECONDS), 200)
       
    Finally, note that in a few cases (:meth:`round_robin`, :meth:`choice`)
    the values returned can be non-numeric and non-time. We could, for
    example, define an entity generator (for a
    :class:`~.entitysource.SimEntitySource` object) that instantiates a
    randomly-selected :class:`~.entity.SimEntity` subclass via::

       entity_classes = (MyEntity1, MyEntity2, MyEntity3)
       et_generator = SimDistribution.choice(entity_classes)
 
    """
    functionDict = {}
    
    # These two methods (:meth:`~function` and :meth:`.function_names`) are
    # provided for the benefit of a UI. :meth:`function_names` provides a 
    # sequence of distribution functions by name (e.g., for populating a 
    # list box), while :meth:`function` maps those names back to a function 
    # object.
    
    @apidocskip
    @staticmethod
    def function_names():
        """
        Returns a sequence of the available (defined) distribution function
        names
        """
        return SimDistribution.functionDict.keys()

    @apidocskip
    @staticmethod
    def function(functionName):
        """
        Returns the SimDistribution distribution function mapped to the passed
        name
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
        Returns a generator that yields a specified constant value.
        
        :param constValue: The value to be returned by the function/generator
        :type constValue:  Any
        
        """
        def f(): return constValue
        return SimDistribution._random_generator(f)
    functionDict["constant"] = constant

    @staticmethod
    def round_robin(choices):
        """
        Returns a generator that yields values from a passed sequence of
        choices, cycling through them deterministically. For example, to
        create a generator that yields the sequence (2,4,6,2,4,6,2...)::

            SimDistribution.round_robin((2,4,6))

        :param choices: A sequence of values to be cycled through and returned,
                        one at a time, by the generator.
        :type choices:  Sequence
        
        """
        cycle = itertools.cycle(choices)
        def f():
            return next(cycle)
        
        return SimDistribution._random_generator(f)
    functionDict["roundRobin"] = round_robin

    @staticmethod
    def choice(choices, streamNum=1):
        """
        Returns a generator that yields a pseudo-randomly chosen value from
        the passed sequence of choices. The below returns a generator that
        yields a random sequence containing only the values 2, 4 or 6::

            SimDistribution.choice((2,4,6))

        :param choices:  A sequence of the possible values to be returned by
                         the function/generator.
        :type choices:   Sequence

        :param streamNum: Identifies the random stream to sample from.
        :type streamNum:  `int` in range [1 - :func:`max_streams`]

        """
        f =  lambda: _rng[streamNum-1].choice(choices)
        return SimDistribution._random_generator(f, streamNum)
    functionDict["choice"] = choice

    @staticmethod
    def exponential(mean, *, streamNum=1):
        """
        Returns a generator that yields pseudo-random values from the
        exponential distribution with a specified mean. To generate
        exponentially distributed values with a mean of 42 use::

            SimDistribution.exponential(42)
                        
        :param mean:     The mean value (or scale) of the desired exponentially
                         distributed sample.
        :type mean:      Either numeric or a :class:`~.simtime.SimTime`

        :param streamNum: Identifies the random stream to sample from.
        :type streamNum:  `int` in range [1 - :func:`max_streams`]
           
        """
        scalarArgs, timeUnit = SimDistribution._scalar_args(mean)
        try:
            m = float(scalarArgs[0])
        except ValueError:
            msg = "Exponential Distribution: invalid (non-numeric) mean value ({0})"
            raise SimError(_RAND_PARAMETER_ERROR, msg, mean)
        
        f =  lambda: _rng[streamNum-1].exponential(*scalarArgs)
        return SimDistribution._random_generator(f, streamNum, timeUnit)
    
    functionDict["exponential"] = exponential

    @staticmethod
    def uniform(low, high, *, streamNum=1):
        """
        Returns a generator that yields pseudo-random values from the uniform
        distribution with the specified bounds. Sample usage::

            SimDistribution.uniform(SimTime(10, tu.SECONDS),
                                    SimTime(1.5, tu.MINUTES),
                                    streamNum=12)
                                            
        :param low:      The low bound of the desired uniformly distributed
                         sample. 
        :type low:       Either numeric or a :class:`~.simtime.SimTime`
                        
        :param high:     The high bound of the desired uniformly distributed
                         sample. 
        :type high:      Either numeric or a :class:`~.simtime.SimTime`

        :param streamNum: Identifies the random stream to sample from.
        :type streamNum:  `int` in range [1 - :func:`max_streams`]

        """        
        scalarArgs, timeUnit = SimDistribution._scalar_args(low, high)
        low2, high2 = scalarArgs
        try:
            x = float(low2)
            y = float(high2)
        except ValueError:
            msg = "Invalid uniform distribution parameters: low ({0}) or high ({1}) is non-numeric"
            raise SimError(_RAND_PARAMETER_ERROR, msg, low, high)        
             
        if low2 > high2:
            msg = "Invalid uniform distribution parameters: low ({0}) is greater than high ({1})"
            raise SimError(_RAND_PARAMETER_ERROR, msg, low, high)
        
        f =  lambda: _rng[streamNum-1].uniform(*scalarArgs)
        return SimDistribution._random_generator(f, streamNum, timeUnit)
    functionDict["uniform"] = uniform

    @staticmethod
    def triangular(low, mode, high, *, streamNum=1):
        """
        Returns a generator that yields pseudo-random values from the triangular
        distribution with the specified bounds. Must be: low <= mode <= high
                                            
        :param low:      The low bound of the desired triangular distribution. 
        :type low:       Either numeric or a :class:`~.simtime.SimTime`
                        
        :param mode:     The mode of the desired triangular distribution. 
        :type mode:      Either numeric or a :class:`~.simtime.SimTime`
                        
        :param high:     The high bound of the desired triangular distribution. 
        :type high:      Either numeric or a :class:`~.simtime.SimTime`

        :param streamNum: Identifies the random stream to sample from.
        :type streamNum:  `int` in range [1 - :func:`max_streams`]

       """       
        scalarArgs, timeUnit = SimDistribution._scalar_args(low, mode, high)
        low2, mode2, high2 = scalarArgs
        
        try:
            x = float(low2)
            x = float(mode2)
            x = float(high2)
        except ValueError:
            msg = "Invalid (non-numeric) triangular distribution parameter(s): low ({0}), mode ({1}), or high ({2})"
            raise SimError(_RAND_PARAMETER_ERROR, msg, low, high)        
        
        if not (low2 <= mode2 and mode2 <= high2):
            msg = "Invalid triangular distribution parameters: must be low ({0}) <= mode ({1}) <= high ({2})"
            raise SimError(_RAND_PARAMETER_ERROR, msg, low, mode, high)
        
        f =  lambda: _rng[streamNum-1].triangular(*scalarArgs)
        return SimDistribution._random_generator(f, streamNum, timeUnit)
    functionDict["triangular"] = triangular

    @staticmethod
    def normal(mu, sigma, floor=0, *, streamNum=1):
        """
        Returns a generator that yields pseudo-random values from the normal
        (Gaussian) distribution with the specified mu (mean) and sigma
        (standard deviation). 

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

        :param streamNum: Identifies the random stream to sample from.
        :type streamNum:  `int` in range [1 - :func:`max_streams`]      

        """
        scalarArgs, timeUnit = SimDistribution._scalar_args(mu, sigma, floor)
        mu, sigma, floor = scalarArgs
        try:
            x = float(mu)
            x = float(sigma)
            if floor is not None:
                x = float(floor)
        except ValueError:
            msg = "Invalid (non-numeric) normal distribution parameter(s): mu({0}), sigma ({1}), or floor ({2})"
            raise SimError(_RAND_PARAMETER_ERROR, msg, mu, sigma, floor)        
        
        if floor is None:
            f = lambda: _rng[streamNum-1].normal(mu, sigma)
        else:
            f = lambda: max(_rng[streamNum-1].normal(mu, sigma), floor)
        
        return SimDistribution._random_generator(f, streamNum, timeUnit)
    functionDict["normal"] = normal

    @staticmethod
    def weibull(a, *, streamNum=1):
        """
        Returns a generator that returns pseudo-random values from the weibull
        distribution with the specified alpha (shape) parameter. 
                        
        :param a:        The shape of the of the desired weibull distribution.
        :type a:         Either numeric or a :class:`~.simtime.SimTime`

        :param streamNum: Identifies the random stream to sample from.
        :type streamNum:  `int` in range [1 - :func:`max_streams`]

        """
        scalarArgs, timeUnit = SimDistribution._scalar_args(a)       
        try:
            x = float(scalarArgs[0])
        except ValueError:
            msg = "Invalid (non-numeric) weibull distribution parameter(s): a ({0})"
            raise SimError(_RAND_PARAMETER_ERROR, msg, a)        
        
        f =  lambda: _rng[streamNum-1].weibull(*scalarArgs)
        return SimDistribution._random_generator(f, streamNum, timeUnit)
    functionDict["weibull"] = weibull

    @staticmethod
    def pareto(alpha, *, streamNum=1):
        """
        Returns a generator that yields pseudo-random values from the pareto
        distribution with the specified alpha (shape) parameter. S
                        
        :param alpha:    The shape of the of the desired pareto distribution.
        :type alpha:     Either numeric or a :class:`~.simtime.SimTime`

        :param streamNum: Identifies the random stream to sample from.
        :type streamNum:  `int` in range [1 - :func:`max_streams`]

        """
        scalarArgs, timeUnit = SimDistribution._scalar_args(alpha)       
        try:
            x = float(scalarArgs[0])
        except ValueError:
            msg = "Invalid (non-numeric) pareto distribution parameter(s): a ({0})"
            raise SimError(_RAND_PARAMETER_ERROR, msg, alpha)        

        f =  lambda: _rng[streamNum-1].pareto(*scalarArgs)
        return SimDistribution._random_generator(f, streamNum, timeUnit)
    functionDict["pareto"] = pareto

    @staticmethod
    def lognormal(mean, sigma, *, streamNum=1):
        """
        Returns a generator that yields pseudo-random values from the log-
        normal distribution with the specified mean and sigma parameters.
                       
        :param mean:     The mean of the underlying normal distribution.
        :type mean:      Either numeric or a :class:`~.simtime.SimTime`
                        
        :param sigma:    The standard deviation of the underlying normal
                         distribution. Must be greater than zero.
        :type sigma:     Either numeric or a :class:`~.simtime.SimTime` 

        :param streamNum: Identifies the random stream to sample from.
        :type streamNum:  `int` in range [1 - :func:`max_streams`]

        """
        scalarArgs, timeUnit = SimDistribution._scalar_args(mean, sigma)       
        try:
            x, y = scalarArgs
            x = float(x)
            x = float(y)
        except ValueError:
            msg = "Invalid (non-numeric) lognormal distribution parameter(s): mu({0}) or sigma ({1})"
            raise SimError(_RAND_PARAMETER_ERROR, msg, mean, sigma)        

        if sigma <= 0:
            msg = "Invalid Lognormal sigma ({0}); value must be greater than zero"
            raise SimError(_RAND_PARAMETER_ERROR, msg, sigma)
        
        f =  lambda: _rng[streamNum-1].lognormal(*scalarArgs)
        return SimDistribution._random_generator(f, streamNum, timeUnit)
    functionDict["lognormal"] = lognormal

    @staticmethod
    def beta(alpha, beta, *, streamNum=1):
        """
        Returns a generator that yields pseudo-random values from the beta
        distribution with the specified alpha (shape) and beta (scale) parameters.
        
        :param alpha:    Shape parameter of the of the desired beta distribution.
                         Must be greater than zero.
        :type alpha:     Either numeric or a :class:`~.simtime.SimTime`
                       
        :param beta:     Scale parameter of the of the desired beta distribution.
                         Must be greater than zero.
        :type beta:      Either numeric or a :class:`~.simtime.SimTime`

        :param streamNum: Identifies the random stream to sample from.
        :type streamNum:  `int` in range [1 - :func:`max_streams`]
        
        """
        scalarArgs, timeUnit = SimDistribution._scalar_args(alpha, beta)       
        try:
            x, y = scalarArgs
            x = float(x)
            x = float(y)
        except ValueError:
            msg = "Invalid (non-numeric) beta distribution parameter(s): alpha({0}) or beta ({1})"
            raise SimError(_RAND_PARAMETER_ERROR, msg, alpha, beta)        

        if alpha <= 0:
            msg = "Beta Distribution: invalid alpha value ({0}); alpha and beta parameters must be greater than zero"
            raise SimError(_RAND_PARAMETER_ERROR, msg, alpha)
        if beta <= 0:
            msg = "Beta Distribution: invalid beta value ({0}); alpha and beta parameters must be greater than zero"
            raise SimError(_RAND_PARAMETER_ERROR, msg, beta)
        
        f =  lambda: _rng[streamNum-1].beta(*scalarArgs)
        return SimDistribution._random_generator(f, streamNum, timeUnit)
    functionDict["beta"] = beta

    @staticmethod
    def gamma(alpha, beta, *, streamNum=1):
        """
        Returns a generator that yields pseudo-random values from the gamma
        distribution with the specified alpha (shape) and beta (scale)
        parameters.

        :param alpha:    Shape parameter of the of the desired gamma
                         distribution. Must be non-negative.
        :type alpha:     Either numeric or a :class:`~.simtime.SimTime`
                       
        :param beta:     Scale parameter of the of the desired gamma
                         distribution. Must be non-negative.
        :type beta:      Either numeric or a :class:`~.simtime.SimTime`

        :param streamNum: Identifies the random stream to sample from.
        :type streamNum:  `int` in range [1 - :func:`max_streams`]

        """
        scalarArgs, timeUnit = SimDistribution._scalar_args(alpha, beta)       
        try:
            x, y = scalarArgs
            x = float(x)
            x = float(y)
        except ValueError:
            msg = "Invalid (non-numeric) gamma distribution parameter(s): alpha({0}) or beta ({1})"
            raise SimError(_RAND_PARAMETER_ERROR, msg, alpha, beta)        

        if alpha < 0:
            msg = "Gamma Distribution: invalid alpha value ({0}); alpha and beta parameters must be non-negative"
            raise SimError(_RAND_PARAMETER_ERROR, msg, alpha)
        if beta < 0:
            msg = "Gamma Distribution: invalid beta value ({0}); alpha and beta parameters must be non-negative"
            raise SimError(_RAND_PARAMETER_ERROR, msg, beta)

        f =  lambda: _rng[streamNum-1].gamma(*scalarArgs)
        return SimDistribution._random_generator(f, streamNum, timeUnit)
    functionDict["gamma"] = gamma

    @staticmethod
    def geometric(rho, *, streamNum=1):
        """
        Returns a generator that returns pseudo-random values from the geometric
        distribution with the specified rho (probability of success of a single
        trial) parameter. 

        :param rho:      The probability of success of an individual trial.
                         0.0 < rho <= 1.0
        :type rho:       `float`
                       
        :param streamNum: Identifies the random stream to sample from.
        :type streamNum:  `int` in range [1 - :func:`max_streams`]

        """
        try:
            rho = float(rho)
        except ValueError:
            msg = "Geometric Distribution: invalid (non-numeric) rho value ({0}); must be > 0 and <= 1"
            raise SimError(_RAND_PARAMETER_ERROR, msg, rho)
            
        if rho <= 0 or rho > 1:
            msg = "Geometric Distribution: invalid rho (probability) value ({0}); must > 0 and <= 1"
            raise SimError(_RAND_PARAMETER_ERROR, msg, rho)
                
        f =  lambda: _rng[streamNum-1].geometric(rho)
        return SimDistribution._random_generator(f, streamNum)
    functionDict["geometric"] = geometric

    @staticmethod
    def logistic(loc=0.0, scale=1.0, floor=0, *, streamNum=1):
        """
        Returns a generator that yields pseudo-random values from the logistic
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
                       
        :param streamNum: Identifies the random stream to sample from.
        :type streamNum:  `int` in range [1 - :func:`max_streams`]

        """
        scalarArgs, timeUnit = SimDistribution._scalar_args(loc, scale, floor)
        loc, scale, floor = scalarArgs
        try:
            x = float(loc)
            x = float(scale)
            if floor is not None:
                x = float(floor)
        except ValueError:
            msg = "Invalid (non-numeric) logistic distribution parameter(s): loc({0}), scale ({1}), or floor ({2})"
            raise SimError(_RAND_PARAMETER_ERROR, msg, loc, scale, floor)        
        
        if floor is None:
            f = lambda: _rng[streamNum-1].logistic(loc, scale)
        else:
            f = lambda: max(_rng[streamNum-1].logistic(loc, scale), floor)
        
        return SimDistribution._random_generator(f, streamNum)
    functionDict["logistic"] = logistic    

    @staticmethod
    def binomial(n, rho, *, streamNum=1):
        """
        Returns a generator that yields pseudo-random values from the binomial
        distribution with the specified n (number of trials) and rho
        (probability of success of a single trial) parameter. 

        :param n:       The number of trials, >= 0
        :type n:       `int`
        
        :param rho:      The probability of success of an individual trial.
                         0.0 <= rho <= 1.0
        :type rho:       `float`
                       
        :param streamNum: Identifies the random stream to sample from.
        :type streamNum:  `int` in range [1 - :func:`max_streams`]

        """
        try:
            if int(n) != float(n) or int(n) < 0:
                msg = "Binomial Distribution: invalid (non-integer) n value ({0}); must be >= 0 "
                raise SimError(_RAND_PARAMETER_ERROR, msg, n)
                
        except ValueError:
            msg = "Binomial Distribution: invalid (non-numeric) n value ({0}); must be >= 0 "
            raise SimError(_RAND_PARAMETER_ERROR, msg, n)
        
        try:
            rho = float(rho)
        except ValueError:
            msg = "Binomial Distribution: invalid (non-numeric) rho value ({0}); must be >= 0 and <= 1"
            raise SimError(_RAND_PARAMETER_ERROR, msg, rho)
                      
        #if n < 0:
            #msg = "Binomial Distribution: invalid n value ({0}); must >= 0"
            #raise SimError(_RAND_PARAMETER_ERROR, msg, n)
        if rho < 0 or rho > 1:
            msg = "Binomial Distribution: invalid rho (probability) value ({0}); must >= 0 and <= 1>"
            raise SimError(_RAND_PARAMETER_ERROR, msg, rho)
        
        f =  lambda: _rng[streamNum-1].binomial(n, rho)
        return SimDistribution._random_generator(f, streamNum)
    functionDict["binomial"] = binomial
    
    # TODO Add  , poisson, power distributions from numpy
    
    @staticmethod
    def _scalar_args(*args):
        """
        Takes the list of passed positional arguments, converting any SimTime
        values into scalar values using the time unit of  the first SimTime
        argument encountered.
        
        Returns the updated/converted list of arguments and the time unit used
        (or None if no SimTime values were found)
        
        Called by distribution methods whose parameters may optionally be
        SimTime values. The returned scalar argument list and time unit are
        then typically passed to _random_generator() create a generator object
        for a parameterized distribution function.
        """
        timeUnits = None
        
        def scalar_arg(a):
            nonlocal timeUnits
            if isinstance(a, SimTime):
                if timeUnits is None:
                    timeUnits = a.units
                    return a.value
                else:
                    return a.to_units(timeUnits).value
            else:
                return a
            
        scalarArgs = [scalar_arg(a) for a in args]
        return scalarArgs, timeUnits            
    
    @staticmethod
    def _random_generator(f, streamNum=1, timeUnit=None):
        """
        First validates the passed random stream number.
        
        Then creates and returns a generator wrapping the passed SimDistribution
        parameterized function. If the passed timeUnit parameter is not None, 
        the generated values will be SimTime objects of the specified time unit.
        Otherwise, the generated values will be scalars (or whatever type
        is output from the passed function).
        
        Called by the SimDistribution methods above to create a sampling
        generator based on the specified distribution and parameters.
        
        Note that this design ensures that the passed function is not actually
        evaluated/executed until the first value is requested from the generator.
        Typically the generator is created prior to random number generator
        initialization (simrandom.initialize()); any attempt to by the function
        access a RNG prior to that will result in an error.
        """
        # validate the selected random number stream
        if streamNum <= 0 or streamNum > max_streams():
            msg = "Requested stream number ({0}) must be in range 1 - {1}"
            raise SimError(_RAND_PARAMETER_ERROR, msg, streamNum, max_streams())
        
        def sim_time_generator():
            while True:
                 yield SimTime(f(), timeUnit)
        
        def scalar_generator():
            while True:
                 yield f()
                 
        if timeUnit is None:
            return scalar_generator()
        else:
            return sim_time_generator()


if __name__ == '__main__':
    import time
    initialize()
    for n in SimDistribution.function_names():
        print(n)

    f = SimDistribution.function('exponential')
    gen = f(10)
    total = 0
    cpustart = time.process_time()
    for i in range(100000):
        total += next(gen)
    cpuend = time.process_time()
    print("SimDistribution number_generator exponential scalar from dict", cpuend - cpustart, "mean value:", total / 100000)
    
    gen = SimDistribution.constant(10)
    total = 0
    cpustart = time.process_time()
    for i in range(100):
        total += next(gen)
    cpuend = time.process_time()
    print("SimDistribution constant scalar", cpuend - cpustart, "mean value:", total / 100000)

    gen = SimDistribution.exponential(10)
    total = 0
    cpustart = time.process_time()
    for i in range(100000):
        total += next(gen)
    cpuend = time.process_time()
    print("SimDistribution number_generator exponential scalar", cpuend - cpustart, "mean value:", total / 100000)

    gen = SimDistribution.exponential(SimTime(9), streamNum=2)
    total = SimTime(0)
    cpustart = time.process_time()
    for i in range(100000):
        total += next(gen)
    cpuend = time.process_time()
    print("SimDistribution number_generator exponential SimTime", cpuend - cpustart, "mean value:", total / 100000)

    gen = SimDistribution.uniform(SimTime(10), SimTime(1, tu.MINUTES))
    total = 0
    cpustart = time.process_time()
    for i in range(100000):
        total += next(gen)
    cpuend = time.process_time()
    print("SimDistribution number_generator uniform time", cpuend - cpustart, "mean value:", total / 100000)

    gen = SimDistribution.triangular(SimTime(10), 35, SimTime(1, tu.MINUTES))
    total = 0
    cpustart = time.process_time()
    for i in range(100000):
        total += next(gen)
    cpuend = time.process_time()
    print("SimDistribution number_generator triangular time", cpuend - cpustart, "mean value:", total / 100000)

    args1 = [SimTime(10)]
    kwargs1 = {}
    kwargs1['high'] = SimTime(1, tu.MINUTES)
    kwargs1['mode'] = 35
    gen = SimDistribution.triangular(*args1, **kwargs1)
    total = 0
    cpustart = time.process_time()
    for i in range(100000):
        total += next(gen)
    cpuend = time.process_time()
    print("SimDistribution number_generator triangular time", cpuend - cpustart, "mean value:", total / 100000)


    gen = SimDistribution.normal(SimTime(10), 4)
    total = 0
    negativeCount = 0
    cpustart = time.process_time()
    for i in range(1000):
        nextVal = next(gen)
        total += nextVal
        if nextVal < 0: negativeCount += 1
    cpuend = time.process_time()
    print("SimDistribution number_generator gaussian time", cpuend - cpustart, negativeCount, "mean value:", total / 1000)

    gen = SimDistribution.normal(SimTime(10), 4, floor=None)
    total = 0
    negativeCount = 0
    for i in range(1000):
        nextVal = next(gen)
        total += nextVal
        if nextVal < 0: negativeCount += 1
    print("SimDistribution number_generator normal time no floor negative count:", negativeCount, "mean value:", total / 1000)

    gen = SimDistribution.choice((2, 4, 6))
    total = 0
    negativeCount = 0
    for i in range(1000):
        total += next(gen)
    print("SimDistribution number_generator choice expected mean 4, actual mean:", total / 1000)

    gen = SimDistribution.weibull(1.0)
    total = 0
    for i in range(1000):
        total += next(gen)
    print("SimDistribution number_generator weibull, actual mean:", total / 1000)

    gen = SimDistribution.pareto(1.0)
    total = 0
    for i in range(1000):
        total += next(gen)
    print("SimDistribution number_generator pareto, actual mean:", total / 1000)

    gen = SimDistribution.lognormal(10, 2.0)
    total = 0
    for i in range(1000):
        total += next(gen)
    print("SimDistribution number_generator lognormal, actual mean:", total / 1000)

    gen = SimDistribution.beta(10, 2.0)
    total = 0
    for i in range(1000):
        total += next(gen)
    print("SimDistribution number_generator beta, actual mean:", total / 1000)

    gen = SimDistribution.gamma(10, 2.0)
    total = 0
    for i in range(1000):
        total += next(gen)
    print("SimDistribution number_generator gamma, actual mean:", total / 1000)

    gen = SimDistribution.geometric(0.35)
    total = 0
    for i in range(1000):
        total += next(gen)
    print("SimDistribution number_generator geometric, actual mean:", total / 1000)

    gen = SimDistribution.logistic(0, 2)
    total = 0
    for i in range(1000):
        total += next(gen)
    print("SimDistribution number_generator logistic, actual mean:", total / 1000)

    gen = SimDistribution.binomial(5, 0.2)
    total = 0
    for i in range(1000):
        total += next(gen)
    print("SimDistribution number_generator binomial, actual mean:", total / 1000)
