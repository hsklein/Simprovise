===============================
The simprovise.modeling Package
===============================

.. toctree::
   :maxdepth: 2

The ``modeling`` package defines the fundamental classes required to create a 
simulation model. These are the classes that the model builder is likely
to instantiate directly and/or use through inheritance:

* :ref:`Locations, <location-module-label>` including 
  :class:`~simprovise.modeling.location.SimLocation`, 
  :class:`~simprovise.modeling.location.SimQueue`, and
  :class:`~simprovise.modeling.location.SimRootLocation`.
* :ref:`Resource-related<resource-module-label>` classes including 
  :class:`~simprovise.modeling.resource.SimResource` and
  :class:`~simprovise.modeling.resource.SimResourcePool`.
* :ref:`Entity-related<entity-source-sink-label>` classes including 
  :class:`~simprovise.modeling.entity.SimEntity`, 
  :class:`~simprovise.modeling.entitysource.SimEntitySource`, and
  :class:`~simprovise.modeling.entitysink.SimEntitySink`.
* :ref:`transaction-process-label`, including
  :class:`~simprovise.modeling.process.SimProcess` and its base class 
  :class:`~simprovise.modeling.transaction.SimTransaction`.
* :ref:`counter-module-label`

The package also includes some base classes of the types noted above,
including:

* :ref:`agent-module-label`
* :ref:`static-transient-object-label`

See also:

* The :doc:`core <simprovise.core>` package for some of the more
  basic services and constructs, including the simulation clock and time,
  random number generation/probability distributions, and utilities including
  logging, exceptions, and event tracing.
* :doc:`modeling_concepts` for further background on the intent and use
  of the underlying modeling concepts implemented by this package.

.. _agent-module-label:

Agent and Message Classes
=========================

.. autoclass:: simprovise.modeling.agent.SimMessage
    :members:

.. autoclass:: simprovise.modeling.agent.SimMsgType
    :members:

.. autoclass:: simprovise.modeling.agent.SimAgent
    :members:

.. _static-transient-object-label:

Static and Transient Simulation Object Base Classes
===================================================


.. autoclass:: simprovise.modeling.simobject.SimLocatableObject
    :members:
    :show-inheritance:

.. autoclass:: simprovise.modeling.simobject.SimTransientObject
    :members:
    :show-inheritance:

.. autoclass:: simprovise.modeling.location.SimStaticObject
     :show-inheritance:

.. _location-module-label:

The `location` Module
=====================

.. autoclass:: simprovise.modeling.location.SimLocation
    :members:
    :show-inheritance:

.. autoclass:: simprovise.modeling.location.SimQueue
    :members:
    :show-inheritance:

.. autoclass:: simprovise.modeling.location.SimRootLocation

.. _resource-module-label:

The `resource` Module
========================

The ``resource`` module defines a number or resource and resource-related
classes:

* :class:`~simprovise.modeling.resource.SimResource`: the base class for all
  resources
* :class:`~simprovise.modeling.resource.SimSimpleResource`: A "simple" resource
  that can (but does not have to) act as its own resource assignment agent.
  Model-specific resource classes usually inherit from SimSimpleResource.
* :class:`~simprovise.modeling.resource.SimResourcePool`: a base implementation
  of a resource pool, in which a single assignment agent manages multiple 
  resources. Modelers may derive from this class to implement custom pool
  assignment behavior.
* :class:`~simprovise.modeling.resource.ResourceAssignmentAgentMixin` and
  :class:`~simprovise.modeling.resource.SimResourceAssignmentAgent`: 
  defines the resource assignment agent interface and provides a default
  implementation (used by 
  :class:`~simprovise.modeling.resource.SimSimpleResource`).
* :class:`~simprovise.modeling.resource.SimResourceAssignment`: a data class
  specifying the resources assigned to a process as result of a 
  :meth:`~simprovise.modeling.process.SimProcess.acquire` or
  :meth:`~simprovise.modeling.process.SimProcess.acquire_from` call.
* :class:`~simprovise.modeling.resource.SimResourceRequest`: a class
  encapsulating the number and type of resources requested via an
  :meth:`~simprovise.modeling.process.SimProcess.acquire` or
  :meth:`~simprovise.modeling.process.SimProcess.acquire_from` call.

The module also defines some :ref:` exceptions<resource-module-exceptions-label>`
related specifically to resources.

See also: :ref:`The Modeling Concepts Resource section <resource-concept-label>`

Classes
-------

.. autoclass:: simprovise.modeling.resource.SimResource
    :members:
    :show-inheritance:
    
.. autoclass:: simprovise.modeling.resource.SimSimpleResource
    :members:
    :show-inheritance:

.. autoclass:: simprovise.modeling.resource.SimResourcePool
    :members:
    :show-inheritance:

.. autoclass:: simprovise.modeling.resource.ResourceAssignmentAgentMixin
    :members:
    :show-inheritance:

.. autoclass:: simprovise.modeling.resource.SimResourceAssignmentAgent
    :members:
    :show-inheritance:

.. autoclass:: simprovise.modeling.resource.SimResourceAssignment
    :members:
    :show-inheritance:
    
.. autoclass:: simprovise.modeling.resource.SimResourceRequest
    :members:
    :show-inheritance:
    
.. _resource-module-exceptions-label:

Exceptions
----------

  
.. autoexception:: simprovise.modeling.resource.SimResourceDownException
    :members:
    :show-inheritance:
  
.. autoexception:: simprovise.modeling.resource.SimResourceUpException
    :members:
    :show-inheritance:
 
.. _entity-source-sink-label:

Entity-Related Classes
======================

.. autoclass:: simprovise.modeling.entity.SimEntity
    :members:
    :show-inheritance:

.. autoclass:: simprovise.modeling.entitysource.SimEntitySource
    :members:
    :show-inheritance:

.. autoclass:: simprovise.modeling.entitysink.SimEntitySink
    :members:
    :show-inheritance:

.. _transaction-process-label:

Transactions and Processes
==========================

.. autoclass:: simprovise.modeling.transaction.SimTransaction

.. autoclass:: simprovise.modeling.process.SimProcess
    :members:
    :show-inheritance:

.. _counter-module-label:

Counters
========

.. autoclass:: simprovise.modeling.counter.SimCounter
    :members:
    :show-inheritance:


