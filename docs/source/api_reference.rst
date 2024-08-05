========================
simprovise API Reference
========================

**simprovise** consists of five packages (not including the test and demo
code packages) Three of them (``simprovise``, ``simprovise.core`` and 
``simprovise.modeling``) constitute the primary simprovise public API.
  
The two other packages (``simprovise.database`` and ``simprovise.runcontrol``) 
are not intended for use by the typical model developer, so their APIs are 
considered "less public" (and less stable as well).

  
The two other packages are not intended for use by the typical model 
developer, so their APIs are considered "less public" and more subject to
change:

* **simprovise.runcontrol**: Provides lower-level interfaces for the 
  execution of simulation models; it is used by the ``simprovise`` package, but
  generally will not be accessed by most model developers.
* **simprovise.database**: Defines interfaces to the simulation output
  database and an implementation in sqlite3. Used by the 
  ``simprovise.runcontrol`` package, but again not by the typical modeler.


Public APIs
===========

The public API includes the packages/classes that **simprovise** users are
most likely to use to build and execute simulation models:

* **simprovise**: Includes the :class:`~simprovise.simulation.Simulation` 
  and :class:`~simprovise.simulation.SimulationResult` classes which
  provide high-level interfaces for executing and reporting on simulation
  runs.
* **simprovise.modeling**: Includes the modules and classes that implement
  most of the :doc:`modeling_concepts`; the classes/APIs that the model
  developer typically uses most often are in this package.
* **simprovise.core**: Provides the core classes and infrastructure used
  by all of the other simprovise packages (many of which will be used
  by model developers as well).

.. toctree::
   :maxdepth: 2

   simprovise
   simprovise.core
   simprovise.modeling
   
Non- (or Quasi-) Public APIs
=============================

**simprovise** includes two other packages that provide (generally)
non-public infrastructure:

* **simprovise.runcontrol**: Provides lower-level interfaces for the 
  execution of simulation models; it is used by the ``simprovise`` package, but
  generally will not be accessed by most model developers.
* **simprovise.database**: Defines interfaces to the simulation output
  database and an implementation in sqlite3. Used by the 
  ``simprovise.runcontrol`` package, but again not by the typical modeler.

Neither of these packages are likely to be accessed directly by the typical 
model-building user. The documentation may be of interest to 
maintainers and those building tools on top of the base simprovise library.

At this time, these at best quasi-public APIs can be considered less
stable than the public APIs documented in the previous section.

.. toctree::
   :maxdepth: 2
   
   simprovise.database
   simprovise.runcontrol
