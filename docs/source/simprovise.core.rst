=======================
simprovise.core package
=======================

.. toctree::
   :maxdepth: 2

The ``core`` package includes the basic classes required to define a simulation model
as well as the event processing framework that lies at the heart of any discrete 
event simulator.

This references focuses on classes that are used - either directly or through inheritance -
to build and define simulation models.

Agent and Message Classes
-------------------------

.. automodule:: simprovise.core.agent
    :members:

Static and Transient Simulation Object Base Classes
---------------------------------------------------

.. automodule:: simprovise.core.simelement
    :members:
    :show-inheritance:

.. automodule:: simprovise.core.location
    :members:
    :show-inheritance:

.. automodule:: simprovise.core.simobject
    :members:
    :show-inheritance:

Resource-Related Classes
------------------------

.. automodule:: simprovise.core.resource
    :members:
    :show-inheritance:

Entity-Related Classes
----------------------

.. automodule:: simprovise.core.entity
    :members:
    :show-inheritance:

.. automodule:: simprovise.core.entitysource
    :members:
    :show-inheritance:

.. automodule:: simprovise.core.entitysink
    :members:
    :show-inheritance:

Transactions and Processes
--------------------------

.. automodule:: simprovise.core.transaction
    :members:
    :inherited-members:

.. automodule:: simprovise.core.process
    :members:
    :show-inheritance:


(Simulated) Time Classes
========================

SimClock
--------

.. automodule:: simprovise.core.simclock
    :members:

SimTime
-------

.. automodule:: simprovise.core.simtime
    :members:

Random Value Generation
=======================

.. automodule:: simprovise.core.simrandom
    :members:

Counters and Data Collection
============================

Counters
--------

.. automodule:: simprovise.core.counter
    :members:

Datasets and DataCollectors
---------------------------

.. automodule:: simprovise.core.datacollector
    :members:
    :show-inheritance:

Utility Classes
===============

Exceptions
----------

.. automodule:: simprovise.core.simexception
    :members:
    :undoc-members:
    :show-inheritance:

Logging
-------

.. automodule:: simprovise.core.simlogging
    :members:


