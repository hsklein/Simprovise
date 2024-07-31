====================================
Simprovise Configuration
====================================

A number of Simprovise parameters and settings may be configured via
`.ini` configuration files. A default `simprovise.ini` is installed
with simprovise; any or all of it's settings may be overridden with
user or model-specific `.ini` files.

Configuration Settings
===========================

All settings are case-insensitive unless otherwise noted.
   

.. csv-table:: SimTime Section Settings
   :header: "Setting/Option", "Values", "Description"

   BaseTimeUnit", "seconds, minutes, hours or none", "None corresponds to dimensionless SimTime values"


.. csv-table:: Logging Section Settings
   :header: "Setting/Option", "Values", "Description"

   "enabled", "on/off, yes/no, true/false, 1/0", "Logging enabled/disabled"
   "level", "debug, info, warning, error or critical", "Default logging level, if logging is enabled"
   "<module name>", "debug, info, warning, error or critical", "Override logging level for specified simprovise module"

`<module name>` is the fully-qualified name of a simprovise module, e.g.
``simprovise.core.simevent``. Multiple modules may be specified via multiple
lines.


.. csv-table:: SimRandom Section Settings
   :header: "Setting/Option", "Values", "Description"

   "StreamsPerRun", "integer > 0", "The number of pseudo-random number streams available to the model"
   "MaxReplications", "integer > 0", "The maximum number of independent replications/maximum run number"


.. csv-table:: SimTrace Section Settings
   :header: "Setting/Option", "Values", "Description"

   "enabled", "on/off, yes/no, true/false, 1/0", "Tracing enabled/disabled"
   "TraceType", "Table or CSV", "Output type, either formatted table or CSV"
   "MaxEvents", "integer", "If positive, the maximum number of events in trace output"
   "Destination", "stdout or file", "Trace output destination; if 'file', see below"
   
If the `Destination` setting is 'file', the output will be written to 
``<model_name>_trace.txt`` in the current directory. The filename itself 
cannot be specified via configuration.


.. csv-table:: Output Report Section Settings
   :header: "Setting/Option", "Values", "Description"

   "Destination", "stdout or file", "Simulation output report destination; See below"
   
This setting only applies if the modeling code calls
:meth:`~simprovise.simulation.SimulationResult.print_summary` 
and does not specify a destination. In that case:

* If the `Destination` setting is 'file', the output will be written to 
  ``<model_name>_trace.txt`` in the current directory. The filename itself 
  cannot be specified via configuration.
* If the `Destination` setting is 'stdout', the output will be written to 
  ``stdout``.




Configuration Files and Locations
=================================
