
===============================
The simprovise Package
===============================

The ``simprovise`` package provides a high-level API for:

* Executing simulation models, either as single runs or as multiple
  independent replications via class :class:`~simprovise.simulation.Simulation`.
  
* Generating and saving output data and analysis via class
  :class:`~simprovise.simulation.SimulationResult`.

See also:

* The :ref:`bank-1-tutorial-single-execution-label` tutorial for further 
  explanation on execution of a single simulation run.
  
* The :ref:`bank-1-tutorial-multiple-replications-label` tutorial on
  performing multiple independent replications of a simulation.

.. simprovise-simulation-label:

Simulation Execution
====================

.. autoclass:: simprovise.simulation.Simulation
    :members:
    
.. simprovise-simresult-label:

Simulation Output Reporting
===========================

.. autoclass:: simprovise.simulation.SimulationResult
    :members:
