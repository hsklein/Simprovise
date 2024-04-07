============================
Simprovise Modeling Concepts
============================

This section describes the conceptual building blocks that can be used to
construct and represent a model in Simprovise. These building blocks include:

* Entities
* Locations
* Processes
* Resources
* Entity Sources
* Entity Sinks

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

Agents
======

Transient Objects
=================

'Transient Objects' are model objects that exist for only part of a simulation run.

Entities
--------

Static Objects
==============

Locations
---------

Resources
---------

Entity Sources
--------------

Entity Sinks
------------


Processes
=========

Counters
========

Simulated Time
==============

Pseudo-Random Value Generation
==============================

Random Number Streams
---------------------

Sampling from Random Distributions
----------------------------------