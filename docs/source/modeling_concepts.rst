============================
Simprovise Modeling Concepts
======================entity======

This section describes the conceptual building blocks that can be used to
construct and represent a model in Simprovise. These building blocks include:

* :ref:`entity-concept-label`
* :ref:`location-concept-label`
* :ref:`process-concept-label`
* :ref:`resource-concept-label`
* Entity :ref:`entity-source-concept-label`
* Entity :ref:`entity-sink-concept-label`

'Entities' are transitory objects typically representing units of work in a
simulation model. In a simple model simulating a bank lobby, customers would
almost certainly be represented as entities.

'Locations' typically represent physical or logical locations. They may be
nested - i.e., locations can contain other sublocations. Locations can also
contain resources, entity sources and entity sinks (as described below).
In our bank example, teller windows and the customer queue can be represented
as locations.

A 'Process' represents the activity or task(s) that need to be accomplished by (or on
behalf of) an entity. Every entity is associated with its own process object. The
process typically reads as a set of instructions. In the case of our bank example,
that would look something like "enter the customer queue, wait for a teller, go
to the teller window, ask the teller to perform a transaction, wait for the
teller to complete the transaction, and then leave the bank."

'Resources' are the physical or logical objects needed to perform a process.
They are typically a system constraint. In our example, tellers are resources - the
customer process has to 'acquire' a teller in order to execute their transaction;
the teller is 'released' when the transaction is completed.

An 'entity source' is an object that creates entities and their associated
processes, and then initiates execution of those processes. Every model requires
at least one entity source. Our bank model might have a single entity source
object generating customer entities and processes.

An 'entity sink' is an object that entities must go to when associated process
is complete - the process specification must explicitly move the entity to a
sink. In our bank model, the "leave the bank" portion of the process would be
specified more along the lines of "move to the entity sink." Every model
requires at least one entity sink.

.. _agent-concept-label:
Agents
======

.. _transient-object-concept-label:
Transient Objects
=================

'Transient Objects' are model objects that exist for only part of a simulation run.



.. _entity-concept-label:
Entities
--------

*Entities* are the fundamental objects that flow through a Simprovise simulation.
They are are transitory objects typically representing units of work.
For example, in the :ref:`bank tutorial <bank-1-tutorial-label>`, customers are 
modeled as entities. Entities are objects of class `SimEntity` or a `SimEntity`
subclass.

Entities are created by :ref:`entity-source-concept-label`, along with an 
accompanying :ref:`process <process-concept-label>`, which defines the work and
actions performed by/on behalf of the entity. Every process must complete by
moving the entity to an :ref:`entity sink <entity-sink-concept-label>`, where
both the entity and process objects leave the simulation.

.. _static-object-concept-label:
Static Objects
==============

.. _location-concept-label:
Locations
---------

*Locations* typically represent physical or logical locations. They may be
nested - i.e., locations can contain other sublocations. Locations can also
contain resources, entity sources and entity sinks.

Moveable objects - primarily entities - can move between locations.

In our bank example, teller windows and the customer queue can be represented
as locations.

.. _entity-source-concept-label:
Entity Sources
--------------

*Entity Sources* are location objects that create new entities and place them in
the simulation. New entities are always paired with a process object (also 
created by the entity source). Once an entity is created and initialized,
the paired process is started, which will send the entity on it's way.
The typical :meth:`run` of a process will begin by immediately moving the
entity to another location.

Entity Sources create entities and processes via one or more Entity
Generators. These generators typically specify:

* The class of the entity objects to create
* The class of paired process objects to create
* A distribution defining the rate at which entities are created

.. _entity-sink-concept-label:
Entity Sinks
------------

*Entity Sinks* are locations objects where entities go to exit the simulation.
Every process :meth:run method should end by moving the entity to an entity
sink.

.. _resource-concept-label:
Resources
=========

*Resources* are capacity-constrained objects required to complete some or 
all parts of a process. In our bank demo/tutorial, tellers are resources.
Some of the real world objects that might be represented by resources in
a simulation are:

* Human workers
* Space in a capacity-constrained location
* Machines or equipment
* Tools

Processes obtain resources through either the :meth:`acquire` or 
:meth:`acquire_from` methods - :meth:`acquire` is used to acquire a specific
resource object (or objects), while :meth:`acquire_from` acquires a more
looesly specified resource (by specifying a resource class).
:meth:`acquire_from` is typically used to request resource(s) from a 
resource pool. 

Since resources are capacity constrained, they may not be available at the
time that the process attempts to acquire them; when that is the case,
the process :meth:`acquire` or :meth:`acquire_from` call will block until
the requested resource becomes available and is assigned to the process.

That assignment is performed by a resource assignment agent. 
Every resource has a resource assignment agent, which functions as the
resource's gatekeeper, assigning it to the correct process when it is/becomes
available. A resource can act as it's own agent, as with 
:class:`SimSimpleResource`. A single agent can also manage assignments for
multiple resources, as with :class:`SimResourcePool`. 
If the resource assignment algorithms implemented by these classes to
not reflect the required behavior of modeling project, the modeler
may implement customized assignment logic by subclassing an assignment
agent class.

.. _resource-pool--concept-label:
Resource Pools
--------------

.. _process-concept-label:
Processes
=========

.. _counter-concept-label:
Counters
========

.. _simulated-time-concept-label:
Simulated Time
==============

.. _random-number-generation-concept-label:
Pseudo-Random Value Generation
==============================

.. _random-number-streams-concept-label:
Random Number Streams
---------------------

.. _random-number-distribution-concept-label:
Sampling from Random Distributions
----------------------------------