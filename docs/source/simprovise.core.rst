===========================
The simprovise.core Package
===========================

.. toctree::
   :maxdepth: 2

The Simprovise ``core`` package includes the basic infrastructure required for a
discrete event simulator:

* A :ref:`simulated clock <simclock-module-label>` and mechanisms to specify
  :ref:`simulated time <simtime-module-label>`
* :ref:`Pseudo-random number generation <simrandom-prng-label>` and
  :ref:`probability distributions <simrandom-simdistribution-label>` that
  use them.
* Simulation :ref:`output data collection <simelement-datacollection-label>`
* Various :ref:`utilities <utility-classes-label>` and programming
  infrastructure, including :ref:`exceptions, <simexception-module-label>`,
  :ref:`logging, <simlogging-module-label>` and 
  :ref:`event tracing. <simtrace-module-label>`
* A :ref:`model <model-module-label>` object that provides access to model
  elements for both modeling code and other packages.
* The event processing framework that is at the heart of a simulator.

This references focuses on classes, methods and functions that are used - 
either directly or through inheritance - to build and define simulation models.
In other words, it is oriented towards model builders.

Most of the modeling constructs not defined in ``simprovise.core`` - 
locations, resources, entities, processes, etc. - are found in the
:doc:`modeling <simprovise.modeling>` package.


(Simulated) Clock and Time Modules
==================================


.. _simclock-module-label:

simclock module
----------------

The simulated clock is initialized and advanced by the Simprovise 
infrastructure (primarily the event processor). It also provides one
method useful to modelers, :meth:`~simprovise.core.simclock.SimClock.now`,
which returns the current simulated time.

.. autoclass:: simprovise.core.simclock.SimClock
    :members:

.. _simtime-module-label:

simtime module
--------------

In Simprovise, simulated time (class :class:`~simprovise.core.simtime.SimTime`)
may be expressed in :enum:`units <simprovise.core.simtime.Unit>` 
(hours, minutes, seconds) or be unitless/dimensionless. 
Units larger than hour (e.g. day or week) are not
provided, as in our experience, the length specification of these units will 
vary from model to model. (Future releases may allow for customized additional
units).

Modelers may specify a base/default time unit via 
:doc:`configuration file <configuration>`. It may be accessed (but not modified) 
in code via :func:`~simprovise.core.simtime.base_unit`.
If the default time unit is dimensionless, then any use of dimensioned units
(hours/minutes/seconds) in model code will raise an exception. If the
default unit is *not* dimensionless, then any 
:class:`~simprovise.core.simtime.SimTime` value provided without an
explicit unit will default to the configured default unit.

Dimensionless time is useful when your model does not operate on the scale
of the provided units. While not currently the case, there are also possible
optimizations in future releases that could improve simulation execution 
performance for dimensionless models.

.. autoenum:: simprovise.core.simtime.Unit
    :members:

.. autofunction:: simprovise.core.simtime.base_unit

.. autoclass:: simprovise.core.simtime.SimTime
    :members:
    
.. _simrandom-module-label:

Random Value Generation and Probability Distributions (`simrandom` Module)
==========================================================================

The ``simrandom`` module provides facilities to create and access
multiple, sufficiently independent pseudo-random number streams for use
by simulation models and replication analysis. A more
:ref:`thorough <random-number-streams-concept-label>` discussion of 
Simprovise random number generation can be found in :doc:`modeling_concepts`.

The ``simrandom`` module also provides a variety of 
:ref:`probability distributions <simrandom-simdistribution-label>`
accessed as Python generators, which sample from the distribution using a
specified random number stream.

Both the pseudo-random number generation and probability distributions
are implemented using the NumPy ``random`` module; for further background
information see:

https://numpy.org/doc/stable/reference/random/


.. _simrandom-prng-label:

Pseudo-Random Number Generation Functions
-----------------------------------------

The maximum number of random number streams per model and the maximum
number of supported independent replications can be set via 
:doc:`configuration file. <configuration>` Those maximums can be 
accessed (but not reset) via functions. The
:func:`~simprovise.core.simrandom.get_random_generator` also allows
code to directly access the generator for a specific stream in the 
current run, in case the modeler needs it.

.. autofunction:: simprovise.core.simrandom.max_streams

.. autofunction:: simprovise.core.simrandom.min_run_number

.. autofunction:: simprovise.core.simrandom.max_run_number

.. autofunction:: simprovise.core.simrandom.get_random_generator

    
.. _simrandom-simdistribution-label:

Probability Distributions
-------------------------


.. autoclass:: simprovise.core.simrandom.SimDistribution
    :members:


.. _simelement-datacollection-label:

Data Collection Classes
============================


Simulation Elements
-------------------

.. autoclass:: simprovise.core.simelement.SimElement
    :members: element_id, datasets

.. autoclass:: simprovise.core.simelement.SimClassElement
    :members: element_id

Datasets and DataCollectors (module datacollector)
--------------------------------------------------


.. autoclass:: simprovise.core.datacollector.Dataset
    :members:

.. autoclass:: simprovise.core.datacollector.SimDataCollector

.. autoclass:: simprovise.core.datacollector.SimUnweightedDataCollector
    :members:
    :show-inheritance:

.. autoclass:: simprovise.core.datacollector.SimTimeWeightedDataCollector
    :members:
    :show-inheritance:

DataSinks (datasink module)
---------------------------

.. autoclass:: simprovise.core.datasink.DataSink
    :members:

.. autoclass:: simprovise.core.datasink.NullDataSink

.. _model-module-label:

The SimModel Singleton
======================

.. autoclass:: simprovise.core.model.SimModel
    :members:



.. _utility-classes-label:

Utility Classes and Functions
=============================


.. _simexception-module-label:

Exceptions (simexception module)
---------------------------------

.. automodule:: simprovise.core.simexception
    :members:
    :undoc-members:
    :show-inheritance:

.. _simlogging-module-label:

Logging (simlogging module)
---------------------------

.. autoclass:: simprovise.core.simlogging.SimLogging
    :members:
    
.. _simtrace-module-label:

Simulation Event Tracing (simtrace module)
------------------------------------------

Simprovise simulation event tracing is enabled and for the most part,
configured via :doc:`configuration` file(s). The actual generation of
trace events is performed via the built-in infrastructure; at this time,
custom/model-specific trace events are not supported. (This may change
in a future release.)

The only simtrace function designed for use of the modeler is 
:func:`~simprovise.core.simtrace.add_trace_column`, which may be used
to customize the data displayed with each trace event. See the
:ref:`bank 1 tutorial <bank-1-event-tracing-tutorial-label>` for an
example.

.. autofunction:: simprovise.core.simtrace.add_trace_column

.. _simprovise-core-stats-label:

Statistical Calculation Functions (stats module)
------------------------------------------------

The functions in this module implement some of the statistical algorithms
required for :doc:`simulation output analysis. <output_analysis>` Most of the
work is delegated to The `NumPy <https://numpy.org/>`_  and/or
`SciPy. <https://scipy.org/>`_ The primary public API consists of two
functions, :func:`~simprovise.core.stats.confidence_interval` and
:func:`simprovise.core.stats.weighted_percentiles`.

.. autofunction:: simprovise.core.stats.weighted_percentiles

.. autoclass:: simprovise.core.stats.CIType
    :members:

.. autofunction:: simprovise.core.stats.confidence_interval

:func:`~simprovise.core.stats.confidence_interval` delegates to the following
functions, which may be used directly:

.. autofunction:: simprovise.core.stats.t_confidence_interval

.. autofunction:: simprovise.core.stats.norm_confidence_interval

.. autofunction:: simprovise.core.stats.quantile_confidence_interval
