#===============================================================================
# SCRIPT save_states_as_npy
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Utility script used as part of the process for creating the independent
# random number stream states file. Each state can be used to create a
# separate Mersenne Twister generator; each generator's output is considered
# to be statistically independent of the others.
#
# The number of independent streams required equals the supported number of 
# independent streams per model * the maximum supported number of replication 
# runs; e.g., if the simulator supports models with up to 100 independent 
# streams and allows up to 50 simulations replications, then 5,000 independent
# streams are required, and we will need 5,000 states to initialize those
# streams. See core.simrandom.py for further explanation.
#
# Command line arguments:
#     <nruns> The maximum number of supported simulation replications
#     <nsubstreams> The max number of supported independent streams per model
#     <inputfile>   The file of MT state data created by genmtstates.cpp
#     <outputfile>  The file created by this script, containing an
#                   nruns by nsubstreams two dimensional numpy array of MT
#                   generator states
#
# The process:
#
#     1. Run genmtstates.cpp, which uses the Boost Mersenne Twister 
#        implementation (mt19937) to generate the states for a specified number
#        of streams writes them in binary format to <inputfile>. (It does so by 
#        creating a single MT generator, and for each stream, skipping ahead 
#        2e50 values and saving/writing the generator state.)
#        
#     2. Run this script, which reads that file into a numpy array, reshapes
#        it into a [<nruns>, <nstreams>] 2 dimensional array, and saves that 
#        reshaped array to <outputfile>.
# 
#===============================================================================
import numpy as np
import sys

STATE_SIZE = 624

def printUsageAndExit(reason):
    print(reason)
    print("usage: python ", sys.argv[0], " <nruns> <nsubstreams> <input filename> <output npy filename>")
    raise SystemExit(1)
  
if len(sys.argv) != 5:
    printUsageAndExit("Missing or extra command line arguments")
           
try:     
    nruns = int(sys.argv[1])
except ValueError:
    printUsageAndExit("Non-numeric <nruns> argument")        
if nruns < 1:
    printUsageAndExit("<nruns> argument must be greater than zero")
       
try:     
    nstreams = int(sys.argv[2])
except ValueError:
    printUsageAndExit("Non-numeric <nsubstreams> argument")        
if nstreams < 1:
    printUsageAndExit("<nsubstreams> argument must be greater than zero")
    
inputfile = sys.argv[3]
outputfile = sys.argv[4]

dt = np.dtype("uint32")
rng_state_array = np.fromfile(inputfile, dt)
if rng_state_array.size != nruns * nstreams * STATE_SIZE:
    print("Input array size: ", rng_state_array.size)
    print("Expected input array size: ", nruns * nstreams * STATE_SIZE)
    printUsageAndExit("Unexpected input array size")
    
reshaped_array = rng_state_array.reshape(nruns, nstreams, STATE_SIZE)
np.save(outputfile, reshaped_array)
    