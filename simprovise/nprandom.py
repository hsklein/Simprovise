import numpy as np
#import math
from functools import partial
from simprovise.core import simrandom, SimDistribution, SimTime, simtime

_BASE_SEED = 197624893858926
_BASE_BIT_GENERATOR = np.random.PCG64DXSM(seed=_BASE_SEED)

#_NSTREAMS = 2000
#_MAX_REPLICATIONS = 100
#_STREAM_DELTA = pow(2,48) * 42
#_RUN_DELTA = _STREAM_DELTA * _NSTREAMS


#def initialize_rngs(runNumber):
    #"""
    #"""
    ## start by jumping ahead based on the run number, and adding
    ## one stream delta increment for good measure
    #runjumps = (runNumber - 1) * _RUN_DELTA + _STREAM_DELTA
    #bit_generator = _BASE_BIT_GENERATOR.jumped(runjumps)
    
    ## Create and return the list of generators, one for each possible stream
    ## in the run.
    #sdelta = _STREAM_DELTA
    #ns = _NSTREAMS    
    #rngs = [np.random.Generator(bit_generator.jumped(i * sdelta)) for i in range(ns)]
    
    #return rngs

x = 42

def gentest():
    while True:
        yield x
        
def _scalar_args(*args):
    """
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

        
        
def random_generator(f, rnStream, timeUnit=None):
    print("stream", rnStream)
    
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
 
            
def exponential(mean, rnStream=1):
    scalarArgs, timeUnit = _scalar_args(mean)
    print(timeUnit)
    f =  lambda: simrandom._rng[rnStream-1].exponential(*scalarArgs)
    return random_generator(f, rnStream, timeUnit)
    #return random_generator(lambda: simrandom._rng[rnStream-1].exponential(mean))
      
stimeGenerator = SimDistribution.exponential(SimTime(10.0), streamNum=10)

f = SimDistribution.normal
tGenerator = f(SimTime(3, simtime.MINUTES), SimTime(2, simtime.HOURS), 0)
#tGenerator = SimDistribution.normal(SimTime(3, simtime.MINUTES), SimTime(2, simtime.HOURS), 0)

    
    
if __name__ == '__main__':
    
    #gen = _BASE_BIT_GENERATOR
    #print(gen.state)
    
    stateset = set()
    nruns = simrandom.max_run_number()
    nstreams = simrandom.max_streams()
    
    for i in range(1, nruns+1):
        simrandom.initialize(i)
        for j in range(simrandom.max_streams()):
            bg = simrandom._rng[j].bit_generator
            stateval = bg.state['state']['state']
            stateset.add(stateval)

    print(len(stateset), nruns * nstreams)
        
    #for i in range(10):   
        #print(next(tGenerator))
        
    #g = gentest()
    #print(next(g))
    
    #x = 31
    #print(next(g))
        