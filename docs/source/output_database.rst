====================================
Simulation Output Database Reference
====================================

This section documents the current **simprovise** output database schema.
While users may certainly query these databases directly, they should be
aware that the schema is certainly subject to change, particularly during
the time period prior to a version 1 stable release.

Database Schema
===============

.. image:: outputdb_erd.svg

(or, if you prefer, the :doc:`SQL <output_database_create_sql>`)

Table Descriptions
==================

*elementtype* Table
----------------------

A pre-populated reference table with one row for each top-level
:ref:`simulation element <simulation-elements-label>`
type:

* Process
* Resource
* Location
* Entity
* (Entity) Source
* (Entity)Sink


*timeunit* Table
----------------------

A pre-populated reference table with one row for each simprovise time unit:

* Seconds 
* Minutes 
* Hours 
* None (dimensionless)


*element* Table
----------------------

A table populated with one row for every 
:ref:`simulation element <simulation-elements-label>`
in the executed simulation model. The table fields are:

* **id**: The  element's :attr:`~simprovise.core.simelement.SimElement.element_id`.
* **classname**: The element's module and class.
* **type**: a foreign key pointing to the *elementtype* table.


*dataset* Table
----------------------

A table populated with one row for every 
:ref:`dataset <simulation-datasets-label>`
in the executed simulation model. The table fields are:

* **id**: An autoincremented synthetic integer ID.
* **element**: The :attr:`~simprovise.core.simelement.SimElement.element_id`
  of the :ref:`simulation element <simulation-elements-label>` that owns
  the dataset. (Is a foreign key pointing to the *element* table.)
* **name**: The dataset's name (as specified when the 
  :class:`~simprovise.core.datacollector.Dataset` is created).
* **valuetype**: The (Python) type of the data values that are in this
  dataset (as of now, most likely ``int`` or ``float``).
* **istimeweighted**: A boolean that is ``True`` if this is a 
  :ref:`time-weighted <simulation-time-weighted-datasets-label>` dataset.
* **timeunit**: The *timeunit* of the dataset (which is actually the model's
  :func:`~simprovise.core.simtime.base_unit`), as a foreign key pointing to
  the *timeunit* reference table.


*datasetvalue* Table
----------------------

A table containing the actual dataset values collected during a simulation
run (or in the case of multiple replications, runs). The fields are:

* **dataset**: A foreign key pointing to a *dataset* table row.
* **run**: The run number (a positive integer) that this value was 
  collected in.
* **batch**: The number of the batch that this value was collected (zero
  represents the warmup).
* **simtimestamp**: For unweighted datasets, the (simulated) time (in
  *timeunits*) that the value was collected. For time-weighted datasets,
  the (simulated) time that this value became the current simulated value.
* **totimestamp**: For time-weighted datasets, the simulated time that this
  value *stopped* being the current value. (This should mean that the next
  row has a new value who's *simtimestamp* equals this row's *totimestamp*).

