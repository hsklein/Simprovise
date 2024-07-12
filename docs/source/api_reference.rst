========================
Simprovise API Reference
========================


Public APIs
===========

These ``simprovise``, ``simprovise.core`` and ``simprovise.modeling`` 
packages provide APIs that are intended for use in regular client  code.
In other words, these are the APIs that `Simprovise` users are
most likely to use to build and execute simulation models.

.. toctree::
   :maxdepth: 2

   simprovise
   simprovise.core
   simprovise.modeling
   
Non- (or Quasi-) Public APIs
=============================

The base `Simprovise` installation includes two other packages, 
``simprovise.database`` and ``simprovise.runcontrol``. 

The ``runcontrol`` package provides a lower level interface to simulation
execution; it is used to implement :class:`simprovise.simulation.Simulation`.
The ``database`` package provides lower-level interfaces to 
simulation output databases and the model linkages to use them.

Neither of these packages are likely to be accessed directly by the typical 
model-building user. The documentation may be of interest to 
maintainers and those building tools on top of the base Simprovise library.

At this time, these at best quasi-public APIs can be considered less
stable than the public APIs in the previous section.

.. toctree::
   :maxdepth: 2
   
   simprovise.database
   simprovise.runcontrol
