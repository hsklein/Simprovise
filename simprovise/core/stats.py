#===============================================================================
# MODULE stats
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines functions for various statistical calculations - namely various
# confidence interval calculations and a weighted percentiles function.
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
import numpy as np
import scipy.stats
from enum import Enum
import warnings
from simprovise.core.simexception import SimError
from simprovise.core.simlogging import SimLogging

_NAN = float('nan')
_ERROR_NAME = "Stats (CI) Error"
logger = SimLogging.get_logger(__name__)

class CIType(Enum):
    """
    Enumeration of the currently supported confidence interval calculation types:
    
    * T: Confidence interval based on the Student's T distribution
    * NORMAL: Confidence interval based on the Normal distribution
    * QUANTILE: A non-parametric confidence interval for estimates of quantiles
    """
    T = 'TDistribution'
    NORMAL = 'NormalDistribution'
    QUANTILE = 'NonParametricQuantile'    
    

def t_confidence_interval(values, confidence_level=0.95):
    """
    Use the SciPy stats module Student's t distribution to calculate a
    confidence interval. See:
    https://www.statology.org/confidence-intervals-python/
    
    Client code should generally execute this via :func:`confidence_interval`.
    
    :param values:           Sample values
    :type values:            Iterable of numeric values
    
    :param confidence_level: Desired confidence level. 
                             Defaults to 0.95 (95%).
    :type confidence_level:  `float` in range (.0, 1.0)
    
    :return:                 Low and high bound of confidence interval
    :rtype:                  tuple (numeric, numeric)
    
    """
    assert values
    assert confidence_level > 0. and confidence_level < 1.0
    
    n = len(values)
    df = n - 1
    loc = np.mean(values)
    scale = scipy.stats.sem(values)
    
    # Some data may all be zero, for which SciPy generates a RuntimeWarning
    # Suppress it - the ruturned NaNs are just fine
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=RuntimeWarning)
        return scipy.stats.t.interval(confidence_level, df, loc, scale)
    
def norm_confidence_interval(values, confidence_level=0.95):
    """
    Use the SciPy stats module normal distribution to calculate a
    confidence interval. See again:
    https://www.statology.org/confidence-intervals-python/
    
    (While it isn't checked, n should be relatively large, > 30)
    
    Client code should generally execute this via :func:`confidence_interval`.
    
    :param values:           Sample values
    :type values:            Iterable of numeric values
    
    :param confidence_level: Desired confidence level.
                             Defaults to 0.95 (95%).
    :type confidence_level:  `float` in range (.0, 1.0)
    
    :return:                 Low and high bound of confidence interval
    :rtype:                  tuple (numeric, numeric)
    
    """
    assert values
    assert confidence_level > 0. and confidence_level < 1.0
    
    loc = np.mean(values)
    scale = scipy.stats.sem(values)
    
    # Some data may all be zero, for which SciPy generates a RuntimeWarning
    # Suppress it - the ruturned NaNs are just fine
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=RuntimeWarning)
        return scipy.stats.norm.interval(confidence_level, loc, scale)
   
   
def quantile_confidence_interval(values, quantile=0.5, confidence_level=0.95):
    """
    Calculate a non-parametric confidence interval for a quantile; z-critical
    value obtained via ScyPi stats.norm.ppf() function. See:
    https://statisticalpoint.com/confidence-interval-for-median/.
    
    Client code should generally execute this via :func:`confidence_interval`.
    
    Underlying source of algorithm is:
    https://www.wiley.com/en-us/Practical+Nonparametric+Statistics%2C+3rd+Edition-p-9780471160687
    
    :param values:           Sample values
    :type values:            Iterable of numeric values
    
    :param quantile:         Quantile to calculate interval for. Defaults to
                             0.5 (median)
    :type quantile:          `float` in range (.0, 1.0)
    
    :param confidence_level: Desired confidence level.
                             Defaults to 0.95 (95%).
    :type confidence_level:  `float` in range (.0, 1.0)
    
    :return:                 Low and high bound of confidence interval
    :rtype:                  tuple (numeric, numeric)
    
    """
    assert values 
    assert quantile > 0. and quantile < 1.0
    assert confidence_level > 0. and confidence_level < 1.0
    
    n = len(values)
    q = quantile    
    
    # use norm.ppf() to calculate the Z critical value
    # https://www.statology.org/z-critical-value-python/
    z = scipy.stats.norm.ppf(1 - (1-confidence_level)/2)
    
    j = int(np.ceil(n*q - z * np.sqrt(n*q*(1-q))))
    k = int(np.ceil(n*q + z * np.sqrt(n*q*(1-q))))
    
    sorted_values = sorted(values)
    return sorted_values[j-1], sorted_values[k-1]


def confidence_interval(ci_type, values, confidence_level=0.95, *, quantile=0.5):
    """
    Calculate a confidence interval for a passed confidence level and values
    using a specified confidence interval type/calculation (T, normal or
    non-parametric quantile). For a quantile confidence interval, the
    passed quantile is also used. 
    
    :param ci_type:          Confidence interval type
    :type ci_type:           :class:`CIType`
    
    :param values:           Sample values
    :type values:            Iterable of numeric values
    
    :param confidence_level: Desired confidence level.
                             Defaults to 0.95 (95%).
    :type confidence_level:  `float` in range (.0, 1.0)
    
    :param quantile:         Quantile to calculate interval for. Defaults to
                             0.5 (median). Ignored when the ``ci_type`` is not
                             QUANTILE.
    :type quantile:          `float` in range (.0, 1.0)
    
    :return:                 Low and high bound of confidence interval, or
                             ``(nan, nan)`` if there are an insufficient number of
                             values.
    :rtype:                  `tuple` (numeric, numeric)

    :raises:                 :class:`~.simexception.SimError`
                             Raised if ``ci_type`` is invalid.
    
    """        
    if len(values) < 2:
        return (_NAN, _NAN)
    
    if ci_type == CIType.T:
        interval = t_confidence_interval(values, confidence_level)
    elif ci_type == CIType.NORMAL:
        interval = norm_confidence_interval(values, confidence_level)
    elif ci_type == CIType.QUANTILE:
        interval = quantile_confidence_interval(values, quantile, confidence_level)
    else:
        msg = "Passed ci_type ({0}) is not of type CIType"
        raise SimError(_ERROR_NAME, msg, ci_type)
    
    return interval


def weighted_percentiles(values, weights):
    """
    Calculate all weighted percentiles [0,100] for a weighted list of values.
    The passed values must be already sorted in ascending order. Returns a
    percentiles list such that percentiles[n] is the calculated nth percentile.
    
    :param values:  Data values for which percentiles are to be calculated
    :type values:   Iterable of numerics
    
    :param weights: Weights for each value in values
    :type weights:  Iterable of numerics; must be same length as values
    
    :return:        list of percentiles, indexed by the percentile, [0-100]
    :rtype:         `list`
    
    """
    # Once we move to NumPy 2.x, we can use np.percentile() (Starting with v2.0,
    # it has an optional weights parameter.) For now, use this solution from
    # https://stackoverflow.com/questions/21844024/weighted-percentile-using-numpy
    
    weights = np.array(weights)
    values = np.array(values)
    #weighted_quantiles = (np.cumsum(weights) - 0.5 * weights) / np.sum(weights)
    # The code below delivers (within a small margin of error) np.percentile
    # values when weights are equal
    weighted_quantiles = np.cumsum(weights) - 0.5 * weights
    weighted_quantiles -= weighted_quantiles[0]
    weighted_quantiles /= weighted_quantiles[-1]
    percentiles = [np.interp(i/100., weighted_quantiles, values) for i in range(0, 101)]
    return percentiles

    

        


if __name__ == '__main__':
    print("95% CI of the mean via t distribution:", t_confidence_interval((0, 0, 0, 0), 0.95))
    
    # example from https://statisticalpoint.com/confidence-interval-for-median/
    vals = (8, 11, 12, 13, 15, 17, 19, 20, 21, 21, 22, 23, 25, 26, 28)
    print("values:", vals)
    print("Mean:", np.mean(vals))
    print("95% CI of the mean via t distribution:", t_confidence_interval(vals, 0.95))
    print("95% CI of the mean via normal distribution:", norm_confidence_interval(vals, 0.95))
    print("Median:", np.median(vals), "Non-parametric median 95% CI:",
          quantile_confidence_interval(vals, 0.5, 0.95))
    
    vals = (8, 11, 12, 13, 15, 17, 19, 20, 21, 21, 22, 23, 25, 26, 28,
              5, 71, 33, 36, 25, 22, 54, 42, 54, 61, 12, 16, 6, 45, 36, 18)
    print("\nvalues:", vals)
    print("Mean:", np.mean(vals))
    print("95% CI of the mean via t distribution:",
          confidence_interval(CIType.T, vals, 0.95))
    print("95% CI of the mean via normal distribution:",
          confidence_interval(CIType.NORMAL, vals, 0.95))
    print("Median:", np.median(vals), "Non-parametric median 95% CI:",
          confidence_interval(CIType.QUANTILE, vals, 0.95))
    
    values = (2, 3, 3, 7, 8, 8, 11, 11, 11)
    weights = (1, 1, 1, 1, 1, 1, 1, 1, 1)
    print("unweighted median with dups:", np.median(values))
    pctiles = weighted_percentiles(values, weights)
    print("weighted median with dups:", pctiles[50])
    
    values1 = (2, 3, 7, 8, 11)
    weights = (1, 2, 1, 2, 3)
    pctiles = weighted_percentiles(values1, weights)
    print("weighted median", pctiles[50])
    print("weighted 1st percentile", pctiles[1])
    print("weighted 25th percentile", pctiles[25])
    print("weighted 75th percentile", pctiles[75])
    print("weighted 99th percentile", pctiles[99])
    print("weighted 100th percentile", pctiles[100])
    
    vals2 = list(range(100))
    weights = [2] * 100
    pctiles = weighted_percentiles(vals2, weights)
    print("weighted median", pctiles[50], np.median(vals2))
    print("weighted 1st percentile", pctiles[1], np.percentile(vals2, 1))
    print("weighted 25th percentile", pctiles[25], np.percentile(vals2, 25))
    print("weighted 75th percentile", pctiles[75], np.percentile(vals2, 75))
    print("weighted 99th percentile", pctiles[99], np.percentile(vals2, 99))
    
    
    #setup = '''
#from simprovise.core.stats import weighted_percentiles

#values1 = (2, 3, 7, 8, 11)
#weights = (1, 2, 1, 2, 3)    
    #'''
    
    #n = 10000
    #t1 = timeit.timeit('weighted_percentiles(values1, weights)', setup=setup, number=n)
    #print(t1/n)
    
    