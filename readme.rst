====================================
Simprovise
====================================

**Simprovise** is a Python library for discrete event simulation. It offers an
intuitive API for developing simulation models; it also provides APIs and tools 
for model execution and output analysis, including:

* Execution of multiple replications using independent psuedo-random number
  streams.
* Output data collection.
* Output analysis including summary statistics, through both batch means and
  replication analysis.

Simprovise implements process-based simulation using lightweight coroutines
provided by `greenlet. <https://pypi.org/project/greenlet/>` 
Greenlets are similar to the generator-based coroutines that are available
from the standard CPython distribution, while providing some additional
flexability. In particular, use of the **yield** keyword is not required;
nested methods/functions can be used as well. In 
the case of Simprovise, this allows blocking and process-switching to 
occur "under the covers" during a method call like ``acquire(resource)``.

Simprovise also uses
`NumPy <https://numpy.org/doc/stable/index.html>` for psuedo-random-number
generation, probability distribution sampling, and calculation of summary
statistics.