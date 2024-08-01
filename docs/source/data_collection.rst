========================
Data Collection Concepts
========================

Simulation Elements
===================

**Simulation elements** are objects that exist for the entire life of a 
simulation run that also serve as containers for output data collection
during that run.

Broadly speaking, there are two types of simulation elements in simprovise:

* Static Objects, such as resources and locations.
* Class Elements, which serve as proxies for transient objects that may be
  created and destroyed over the life of the simulation, in particular 
  processes and entities.

Static Object Elements
----------------------

**Static Objects** are elements that are created (directly or indirectly)
by a model script and correspond to some of the basic modeling concepts 
outlined :doc:`here. <modeling_concepts>`. The primary static objects are:

* :ref:`Resources <resource-concept-label>`
* :ref:`Locations <resource-concept-label>` (including queues)
* :ref:`Entity Sources <entity-source-concept-label>`
* :ref:`Entity Sinks <entity-source-concept-label>`

While data are collected for entity sources and sinks, we tend focus on
resource and location data such as:

* Resource utilization, process time and down time
* Location population size, time-in-location, and the number of entities
  entering and leaving the location. 

Process and Entity Elements
---------------------------

Simulation entities (and their accompanying processes) come and go -
they are created many times over the course of a simulation run, they do
their thing (run their processes), and then they are destroyed.

We tend to be interested in data about entity and process objects as groups - 
more specifically, all of the objects of a given entity or process class.
To that end, simprovise creates a single proxy object - an **entity element**
or **process element** - for each 
:class:`~simprovise.modeling.entity.SimEntity` and
:class:`~simprovise.modeling.process.SimProcess` class imported into or 
defined in the model. (simprovise also creates an entity element for
:class:`~simprovise.modeling.entity.SimEntity` itself, since 
that class can be used directly - without subclassing - in a model.)

These proxy elements serve as containers for data collected about all
of the transient entity or process objects associated with them:

* Work-in-process
* Process time
* Total count (generally referred to as "Entries")

Datasets
========

Simprovise **datasets** are a collection of simulation output values for a
single measure and simulation element - e.g. process time for a single
process class, or population for a single location. As such, every
dataset belongs to one simulation element, and every simulation element can
have one or more datasets.

Most of the data references above each correspond to a dataset. These are
the datasets associated (by default) with each simulation element type:

* Resources: process time, utilization and down time.
* Locations: population, entries, and time-in-location
* Entity Elements: work-in-process and process time
* Process Elements: (work)-in-process, entries, and process time.

Entity sources have the same datasets as locations, though the actual data
(other than perhaps Entries) is generally not useful. Entity sinks do not
record any data.

These are, again, the default datasets for these element types. The 
modeler or user can choose to turn off data collection for any of these
datasets, as described :doc:`here <configuration>`, 
:meth:`here <simprovise.core.simelement.SimElement.disable_data_collection>` and
:meth:`here. <simprovise.core.datacollector.Dataset.disable_data_collection>`

The modeler can also add their own custom datasets to elements as
demonstrated in this :ref:`tutorial. <bank-4-tutorial-label>`

Time-Weighted and Unweighted Datasets
-------------------------------------

Simprovise currently supports two types of numeric datasets - time-weighted
and unweighted.

**Time-weighted** datasets represent numeric state that changes over
(simulated) time. Resource utilization, resource down time, work-in-process,
population, queue size and time-in-location are all 
time-weighted datasets.

When we collect time-weighted data, we effectively record the simulated
time spent at each data value; e.g. when we record a work-in-process value of
4, we also record the time it became 4 and the time it transitioned to 3 or 5.

When we calculate a summary statistic for time-weighted data, each value is
weighted by the total time spent at that value.

**Unweighted** datasets, on the other hand, are collections of point-in-time
data values or event counts such as entries, queue time and process time. 
When we calculate  average queue time, for example, we simply average the amount 
of time each entity spent in the queue during some period of simulated time
(such as a batch); there is no weighting involved.

Implementation Notes
====================

A few additional notes on simprovise APIs and architecture for those 
modelers who wish to create custom datasets and/or output reports.

.. note::
  The next section describes the process for creating new datasets (in
  addition to those automatically create by objects in the simprovise
  library) which in turn write their data to a simprovise output database.  
  In addition, it is certainly possible for model developers
  to bypass this existing infrastructure entirely and collect, write and
  report output data in their own format, using whatever Python API they 
  would like.


Counters and Data Collectors
----------------------------

:class:`~simprovise.core.datacollector.Dataset` objects should not be
instantiated directly by model developers who wish to create a custom
dataset; rather, the new datasets are created indirectly through the 
instantiation of other objects, typically
:class:`counters <simprovise.modeling.conter.SimCounter>` for time-weighted data
and :class:`unweighted data collectors <simprovise.core.datacollector.SimUnweightedDataCollector>`
for unweighted data.

Unweighted datasets are created and populated by creating 
:class:`~simprovise.core.datacollector.SimUnweightedDataCollector` objects,
making sure to specify non-``None`` `element` and `name` parameters.
Modeling code adds values to the dataset via 
:meth:`~simprovise.core.datacollector.SimUnweightedDataCollector.add_value`
calls.

When a counter is constructed with non-``None`` values for the `element`
and `name` parameters, it automatically creates a time-weighted dataset for 
that element where a value is added every time the counter is incremented or
decremented. (An initial zero value is added at the start.) The `normalize`
parameter can be set to ``True`` when the modeler would like to report counter
statistics as a percentage of it's capacity (e.g. for utilization).

If counter objects do not meet the model's needs, time-weighted datasets
may also be created by creating a
:class:`~simprovise.core.datacollector.SimTimeWeightedDataCollector` object,
and calling its
:meth:`~simprovise.core.datacollector.SimTimeWeightedDataCollector.add_value` 
method whenever the current value needs to change.


Output Database
---------------

By default, each value added to a simprovise dataset (time-weighted or 
unweighted) is written to the ``datasetvalue`` table in a simprovise (SQLite) 
output database.  The reports generated via class
:class:`~simprovise.simulation.SimulationResult`
all obtain their data from this database.

Modelers can choose to save this database
(via :meth:`~simprovise.simulation.SimulationResult.save_database_as`)
and then use their own queries to read these data and generate their own
output. Modelers can also save summary data as a CSV file via
:meth:`~simprovise.simulation.SimulationResult.save_summary_csv` if they
wish to analyze/format/report on those data in a spreadsheet.

See :doc:`output_database` for further details.