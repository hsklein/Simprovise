====================================
simprovise
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
provided by `greenlet. <https://pypi.org/project/greenlet/>`_ 
Greenlets are similar to the generator-based coroutines that are available
from the standard CPython distribution, while providing some additional
flexability. In particular, use of the ``yield`` keyword is not required,
and ``greenlet`` switching can occur in nested method calls.
In the case of simprovise, this allows blocking and process-switching to 
occur "under the covers" during a method call like ``acquire(resource)``;
a model developer using simprovise should have no need to see, use or even
understand the ``greenlet`` API.

Status
======

Simprovise is under development, with an initial public release planned for
fall 2024. (So yes, the current development version should be considered 
unstable, though it includes almost all the features planned for the initial
release.)

Installation
============

For now, simprovise is only available via this repository; your PYTHONPATH
should be set to include the ``Simprovise.simprovise`` directory.
``greenlet`` and ``numpy`` can be installed from the Python Package Index 
(PyPI) via ``py install``. 
(The public release of simprovise, when ready, will be available via PyPI as 
well.)

Documentation
=============

The current (again mostly, but not entirely complete) documentation can be
found <here coming soon>

Other Dependencies
==================

Simprovise uses
`NumPy <https://numpy.org/doc/stable/index.html>`_ for psuedo-random-number
generation, probability distribution sampling, and calculation of summary
statistics.

Compatibility
=============

Simprovise has been developed using Python 3.12.2. 
It has been tested and runs on Linux (Ubuntu 22.04.4) 
running Python 3.9.19, 3.10.12, and 3.12.4.


License
=======