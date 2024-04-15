#===============================================================================
# MODULE queuing_theory_calc
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# A function that calculates/prints expected queue time and size for either
# an m/m/1 or m/m/2 queuing model.
#
# Equations from: https://www.omnicalculator.com/math/queueing-theory#faq
#
# For old, simplified version (m/m/1 and m/m/2 only) see:
#      https://www.johndcook.com/blog/2022/01/12/mm2/
#===============================================================================
import math
from simprovise.core import simtime, SimTime

def theoryResultsOld(meanIATime, meanProcTime, nServers=1):
    lamb = 1.0 / meanIATime
    mu = 1.0 / meanProcTime

    if nServers == 1:       
        # rho is utilization
        rho = lamb / mu 
        queueTime = lamb / (mu * ( mu - lamb ))
        #queueSize1 = (rho**2) / (1-rho)
    elif nServers == 2:
        queueTime = lamb**2 / (mu * (4*mu**2 - lamb**2))
    
    queueSize = lamb * queueTime
    # rho is utilization
    rho = lamb / (mu * nServers)
        
    print ('Queuing Theory calculation:')
    print ('rho (utilization): ', rho)
    print ('Expected Queue Time: ', queueTime)
    print ('Expected Queue Size: ', queueSize)
    
    
def zero_customer_probability(lamb, mu, s):
    """
    lamb = 1 / mean interarrival time
    mu = 1 / mean service time
    s = number of servers
    """
    alpha = lamb / mu
    summation = 0
    for r in range(0, s):
        summation += (alpha ** r) / math.factorial(r)
        
    p0 = (summation + (alpha ** s / math.factorial(s)) * (1 - alpha / s) ** -1) ** -1
    
    return p0
        
    
def theoryResults(meanIATime, meanProcTime, nServers=1):
    """
    Calculate expected (mean) queue time and length for an m/m/s queueing
    system (with s servers)
    
    Algorithm lifted from:
    https://www.omnicalculator.com/math/queueing-theory#faq
    """
    lamb = 1.0 / meanIATime
    mu = 1.0 / meanProcTime
    s = nServers
    rho = lamb / (s * mu)
    alpha = lamb / mu
    
    p0 = zero_customer_probability(lamb, mu, s)
    print(p0)
    
    Wq = alpha ** s * p0 / (math.factorial(s) * s * mu * (1 - rho) ** 2)
    
    Lq = lamb * Wq
        
    print ('Queuing Theory calculation:')
    print ('rho (utilization): ', rho)
    print ('Expected Queue Time: ', Wq)
    print ('Expected Queue Size: ', Lq)
    
    
    
if __name__ == '__main__':
    meanServiceTime = SimTime(9)
    meanInterarrivalTime = SimTime(12)
    nservers = 2
    
    theoryResults(meanInterarrivalTime.seconds(), meanServiceTime.seconds(),
                  nservers)
