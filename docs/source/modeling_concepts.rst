============================
Simprovise Modeling Concepts
============================

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

**Entities** are the fundamental objects that flow through a Simprovise simulation.
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

**Locations** typically represent physical or logical locations. They may be
nested - i.e., locations can contain other sublocations. Locations can also
contain resources, entity sources and entity sinks.

Moveable objects - primarily entities - can move between locations.

In our bank example, teller windows and the customer queue can be represented
as locations.

.. _entity-source-concept-label:
Entity Sources
--------------

**Entity Sources** are location objects that create new entities and place them in
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

**Entity Sinks** are locations objects where entities go to exit the simulation.
Every process :meth:run method should end by moving the entity to an entity
sink.

.. _resource-concept-label:
Resources
=========

**Resources** are capacity-constrained objects required to complete some or 
all parts of a process. In our bank demo/tutorial, tellers are resources.
Some of the real world objects that might be represented by resources in
a simulation are:

* Human workers
* Space in a capacity-constrained location
* Machines or equipment
* Tools

*Processes* obtain resources through either the :meth:`acquire` or 
:meth:`acquire_from` methods - :meth:`acquire` is used to acquire a specific
resource object (or objects), while :meth:`acquire_from` acquires a more
looesly specified resource (by specifying a resource class).
:meth:`acquire_from` is typically used to request resource(s) from a 
resource pool. 

All resources have a *capacity*, which may be any positive integer; 
resource capacity generally defaults to one. A resource with capacity greater
than one may be used to model multiple instances/copies of the resource;
the first :ref:`bank <bank-1-tutorial-label>` demo model, for example, 
specifies the number of tellers
via the capacity of the Teller resource. Capacity might also be used to
model space or slots in a resource such as an oven.

When a process makes a request request it also specifies the number of
resources it would like to acquire. In this case, each unit of capacity
reflects one resource. If the process requests a specific resource object
via :meth:`acquire`, the number requested must not be greater than the
capacity of that resource.

Since resources are capacity constrained, they may not be available at the
time that the process attempts to acquire them; when that is the case,
the process :meth:`acquire` or :meth:`acquire_from` call will block until
the requested resource becomes available and is assigned to the process.

That assignment is performed by a resource assignment agent. 
Every resource has a resource assignment agent, which functions as the
resource's gatekeeper, assigning it to the correct process when it is/becomes
available. A resource can act as it's own agent, as with 
:class:`~simprovise.modeling.SimSimpleResource`. 
A single agent can also manage assignments for
multiple resources, as with :class:`~simprovise.modeling.SimResourcePool`. 

The :class:`SimSimpleResource` assignment agent assigns the resource (or
units of the resource if it is multiple capacity) by priority. 
Priority may be specified via a priority function; it is FIFO by default.
If the highest priority outstanding request cannot be currently assigned,
no lower priority requests will be processed. (This means that if the
highest priority request is for two resources and the current remaining
capacity of the resource is one, that remaining capacity will not be
assigned to a lower priority request.)

The base resource pool assignment algorithm is more complex, and 
described below.

If the resource assignment algorithms implemented by these classes to
not reflect the required behavior of modeling project, the modeler
may implement customized assignment logic by subclassing an assignment
agent class.

.. _resource-pool--concept-label:
Resource Pools
--------------

A **resource pool** is a resource assignment agent that manages a set
of resources. A pool may contain a heterogeneous collection of resources,
or they may all be resources of the same type. Resource pools give 
processes the flexibility to request a *type* of resource rather 
than a specific resource object via the :meth:`acquire_from` method.
The type is specified as a (Python) class, which must be 
:class:`~simprovise.modeling.SimResource` or (more typically) a subclass.

The base implementation of a resource pool is
:class:`~simprovise.modeling.SimResource`.
That class implements a resource assignment algorithm that maximizes the
number of resources assigned while ensuring that higher priority requests
are never blocked or delayed by assignments to a lower priority request.
In practice, this means that a lower priority request is fulfilled/assigned
only if all of the resources assigned could not be used for the outstanding
higher priority request.
See the class documentation for a more complete description.

Modelers can override this default algorithm by implementing their own
:class:`SimResourcePool` subclass, as illustrated by the 
:ref:`third bank <bank-3-tutorial-label>` demo model.

.. _process-concept-label:
Processes
=========

A **Process** is the task or collection of tasks performed by or on behalf
of an :ref:`entity <entity-concept-label>` during a simulation. In the 
bank demo models, a process consists of:

* Moving the entity (customer) into a queue
* Waiting for a teller (actually, acquiring a teller resource)
* Moving to the teller window
* Executing the customer transaction (waiting for the time
  required for the transaction, then releasing the teller resource)
* Leaving the bank (by moving to an :ref:`entity sink <entity-sink-concept-label>`)

Processes almost always run over some non-zero period of simulated time.
As illustrated above, they generally consist of some combination of:

* Moves from one :ref:`location <location-concept-label>` to another
* Acquisition (and later release) of :ref:`resource(s) <resource-concept-label>`
* Waiting for a specified period of simulated time.

All of these actions are implemented via code in the :meth:`run` of
a :class:`~simprovise.modeling.simprocess` subclass. 
(The base class :meth:`run` does nothing.)
Every Simprovise model will define at least one such subclass to implement 
process behavior for the
:ref:`entities <entity-concept-label>` in the model.

.. _counter-concept-label:
Counters
========

.. _simulated-time-concept-label:
Simulated Time
==============

.. _random-number-generation-concept-label:
Pseudo-Random Value Generation
==============================

In the vast majority of cases, variable or stochastic behavior is modeled
by sampling from one or more random probability distributions, each of
which start with values drawn from a psuedo-random number stream.


.. _random-number-streams-concept-label:
Random Number Streams
---------------------

A pseudo-random number stream is a stream of numeric values generated by a
single psuedo-random number generator instance. The generator is 
peusdo-random in the sense that it is actually deterministic; given the same
initial state, a psuedo-random generator will output the same values (in the
same order) every time (with one provise, see the 
:ref:`random-numpy-tech-note-label` below). 
For a well-constructed generator, these values will, however, appear random. 

In order to avoid correlation, some modelers may choose to use more than
one distinct pseudo-random stream. When analyzing the impact of changes to
a model, they may, for example, want to use separate stream(s) in the variable 
parts of the model.

Simprovise supports this by allowing the modeler to use as many streams
desired; each stream has a numeric identifier. (By default, each
model may use up to 2000 streams, numbered 1-2000, but that maximum can
be configured to another amount by the modeler.)

The Simprovise simulation replication infrastructure also ensures that
each replication of a simulation uses a different set of psuedo-random streams. 
If a model uses streams 1 through 100 and the modeler does a 20 replication
analysis (i.e., re-runs the simulation 20 times using the Simprovise 
replicator), each of those 20 runs will use a
separate distinct set of 100 pseudo-random number streams - e.g., stream 47 will 
be a completely different and (sufficiently independent) stream for each 
of those 20 runs. The maximum number of supported independent replications/runs
is also configurable; it defaults to 100.

.. _random-numpy-tech-note-label:
Implementation/Technical Note
*****************************

Simprovise uses the NumPy PCG-64 DXSM bit generator,
which is slated to become the default NumPy bit generator in a future 
release. See:

https://numpy.org/doc/stable/reference/random/bit_generators/pcg64dxsm.html

Numpy recommends several techniques for creating multiple streams (via 
multiple bit generators) that can reasonably be assumed to be sufficiently
independent of each other; see:

https://numpy.org/doc/stable/reference/random/parallel.html#id8

Simprovise uses the :meth:`jumped` method. It starts with a base generator
seeded with a large random integer - 339697402671268427564149969060011333618.
Each independent generator is created by calling :meth:`jump` on that 
base generator with a unique **jumps** parameter value. 

Finally... while we note that these streams are deterministic, that does
not absolutely mean that each generated stream will be exactly the same across
time and space. The stream results *might* change when run under a different
environment. See the following for details:

https://numpy.org/doc/stable/reference/random/compatibility.html

.. _random-number-distribution-concept-label:
Sampling from Random Distributions
----------------------------------


