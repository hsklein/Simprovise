====================================
simprovise Configuration
====================================

A number of Simprovise parameters and settings may be configured via
`.ini` configuration files. A default `simprovise.ini` is installed
with simprovise; any or all of it's settings may be overridden with
user or model-specific `.ini` files.

Configuration Settings
===========================

All settings are case-insensitive unless otherwise noted.

`SimTime` Section Settings
--------------------------
   
Parameters for the :mod:`simtime` module

.. csv-table:: 
   :header: "Setting/Option", "Values", "Description"

   "BaseTimeUnit", "seconds, minutes, hours or none", "`None` indicates dimensionless SimTime values"

`Logging` Section Settings
----------------------------

.. csv-table:: 
   :header: "Setting/Option", "Values", "Description"

   "enabled", "on/off, yes/no, true/false, 1/0", "Logging enabled/disabled"
   "level", "debug, info, warning, error or critical", "Default logging level, if logging is enabled"
   "<module name>", "debug, info, warning, error or critical", "Override logging level for specified simprovise module"

Disabling logging will improve performance (though probably not dramatically).

`<module name>` is the fully-qualified name of a simprovise module, e.g.
``simprovise.core.simevent``. Multiple modules may be specified via multiple
lines in the configuration file.

`SimRandom` Section Settings
----------------------------

Parameters for initializing/defining pseudo-random number streams.

.. csv-table:: SimRandom Section Settings
   :header: "Setting/Option", "Values", "Description"

   "StreamsPerRun", "integer > 0", "The number of pseudo-random number streams available to the model"
   "MaxReplications", "integer > 0", "The maximum number of independent replications/maximum run number"


`SimTrace` Section Settings
----------------------------

Parameters for the :mod:`simtime` module

.. csv-table:: 
   :header: "Setting/Option", "Values", "Description"

   "enabled", "on/off, yes/no, true/false, 1/0", "Tracing enabled/disabled"
   "TraceType", "Table or CSV", "Output type, either formatted table or CSV"
   "MaxEvents", "integer", "If positive, the maximum number of events in trace output"
   "Destination", "stdout or file", "Trace output destination; if 'file', see below"
   
If the `Destination` setting is 'file', the output will be written to 
``<model_name>_trace.txt`` in the current directory. The filename itself 
cannot be specified via configuration.

`Output Report` Section Settings
--------------------------------

Parameter for the simulation output summary report; applies only if the
modeling code calls :meth:`~simprovise.simulation.SimulationResult.print_summary` 
and does not specify a destination.

.. csv-table:: 
   :header: "Setting/Option", "Values", "Description"

   "Destination", "stdout or file", "Simulation output report destination; see below"
   
* If the `Destination` setting is 'file', the output will be written to 
  ``<model_name>_trace.txt`` in the current directory. The filename itself 
  cannot be specified via configuration.
* If the `Destination` setting is 'stdout', the output will be written to 
  ``stdout``.

`Data Collection` Section Settings
----------------------------------

Parameters for reducing the amount of output data collected during simulation
execution by disabling output data collection for specified 
:class:`simulation elements <simprovise.core.simelement.SimElement>`
and/or :class:`datasets. <simprovise.core.datacollector.Dataset>`

.. csv-table:: 
   :header: "Setting/Option", "Values", "Description"

   "Disable Elements", "comma-delimited element ID pattern list", "See below"
   "Disable Datasets", "comma-delimited dataset ID pattern list", "See below"

An `element ID pattern` uses case-sensitive
`fnmatch <https://docs.python.org/3/library/fnmatch.html>`_
patterns to identify the ID(s) of simulation element(s) for which data 
collection should be disabled. (The first column of the standard output
summary report are element IDs.) For example:

* 'ServerLocation.Server*' matches `ServerLocation.Server1` and `ServerLocation.Server42`
*  'MyLocation*' matches not only any element starting with 'MyLocation', but every
   child element as well. (e.g., it also matches 'MyLocation42.Server')
   
A dataset ID pattern is actually either one or two patterns:

* If two patterns (separated by whitespace), the first matches an element ID,
  the second a dataset name (Column 2 in the standard output summary report).
* If one pattern, only the dataset name is matched (the element ID pattern
  is effectively '*')
  
For example, the following line:: 

   Disable Datasets : ServerLocation.Server* *Time, Population
   
* Disables  data collection for all datasets ending in 'Time' 
  ('ProcessTime' and 'DownTime') belonging to
  elements whose IDs start with 'ServerLocation.Server' (which in this case,
  we will assume are resources)
* Disables  data collection for all datasets in the model named 'Population'

.. note::

   Both element and dataset data collection can be disabled in code as well,
   via API calls 
   :meth:`SimElement.disable_data_collection <simprovise.core.simelement.SimElement.disable_data_collection>` 
   or :meth:`Dataset.disable_data_collection <simprovise.core.datacollector.Dataset.disable_data_collection>`.
   It is perfectly legal to use both techniques (API call and configuration 
   setting) on the same model.

Configuration .ini File Example
--------------------------------

::

   [SimTime]
   # The base (and default) time unit for the simulation model
   # May be seconds, minutes, hours or none (dimensionless)
   BaseTimeUnit : none
   
   [Logging]
   # Logging may be disabled to maximize performance
   # If enabled, the (default) level may be set to one of the values supported by 
   # the python logging module - debug/info/warning/error/critical
   #
   # It is also possible to set logging level by module, where module name is
   # the key, e.g.
   #    simprovise.core.simevent : debug
   enabled     : yes
   level       : info
   #simprovise.core.simevent : debug
   
   [SimRandom]
   # Parameters for initializing/defining pseudo-random number streams:
   #
   # StreamsPerRun:   The number of streams available to the model - the
   #                  maximum value of a SimDistribution streamNum parameter
   # MaxReplications: The maximum number of independent replications that 
   #                  can be executed - i.e., the maximum run number 
   #
   # Note that changing NumModelStreams between replications could result
   # in identical random number streams being used by both replications,
   # so don't do that :)
   StreamsPerRun   : 2000
   MaxReplications : 100
   
   [SimTrace]
   # Parameters for the simtrace module:
   #
   # enabled:     A boolean indicating whether tracing is turned on.
   # TraceType:   Either 'csv' or 'table', where the latter is a formatted 
   #              text table.
   # MaxEvents:   Unless zero, trace stops after writing MaxEvents events
   # Destination: The output destination, either 'stdout' or 'file'. 
   #              If 'file', the output filename is based on the model script
   #              filename and is written to the working directory. (The 
   #              extension is either 'txt' or 'csv', depending on TraceType.)
   enabled     : no
   TraceType   : Table
   MaxEvents   : 100
   Destination : stdout
   
   
   [Output Report]
   # Parameter for the simulation output summary report:
   #
   # Destination: The output destination, either 'stdout' or 'file'. 
   #              If 'file', the output filename is based on the model script
   #              filename (<model name>_report.txt) and is written to the 
   #              working directory.
   #              Applies only if SimResult.print_summary() is called with
   #              `None` for the destination parameter
   Destination : stdout
   
   
   [Data Collection]
   # Parameters for customizing data collection
   #
   # Disable Elements: A comma-delimited list of UNIX shell-style wildcard 
   #                   patterns (as used by the fnmatch module). Any element ID
   #                   that case-sensitive-matches any of the patterns will have
   #                   data collection disabled.
   #
   # Disable Datasets: Another comma-delimited list; each entry in the list can
   #                   consist of either one or two (whitespace separated)
   #                   UNIX shell-style wildcard patterns, a-la above.
   #                   If the entry contains two patterns, the first is used
   #                   to match a dataset's element ID, the second the dataset ID.
   #                   If both match, data collection is disabled for the dataset.
   #                   If there is just one pattern, only the dataset ID is
   #                   matched; data collection is disabled for every dataset ID 
   #                   that matches for all elements.
   #                   Example: *TestLoc* Test*, DownTime
   #                      Disables every dataset named 'Test' in any element whose 
   #                      ID contains 'TestLoc'. Also disables every dataset 
   #                      named 'DownTime' in any element.
   #
   Disable Elements : *.Server3, MyLocation.Server42
   Disable Datasets : ServerLocation.Server* *Time, Population


Configuration File Locations and Precedence
===========================================

The simprovise :mod:`simprovise.core.configuration` module reads up to
four configuration ``.ini`` files in the following order:

1. ``simprovise.ini`` in the simprovise installation directory (part of the
   simprovise installation)
2. ``simprovise.ini`` in the user's working directory 
3. ``<filename>.ini`` in the same directory as ``<filename>.py`` (see note below)
4. ``<filename>.ini`` in the user's working directory.

When the same setting appears in multiple files, the last one read wins/takes
precedence.

By default, the ``<filename>`` in <filename>.ini is the path of the top-level
(main) script invoked by the user on the command line. 

.. note::

   It is expected that users and model developers will use ``<filename>.ini``  
   to address settings specific to a single model - i.e., if we're executing 
   `mymodel.py`, we'd like to set mymodel-specific settings in `mymodel.ini`.
   
   If we are running `mymodel.py` as the top-level script (as done in the
   :doc:`tutorial`), this works out nicely. If, however, we are executing
   `mymodel.py` from some other script, that other script's filename will be
   used, by default, in the search for configuration files. There are two ways
   to work around that:
   
   1. Set an environment variable (SIMPROVISE_MODEL_SCRIPT) to `mymodel.py`'s 
      path, or
   2. Call :meth:`~simprovise.core.configuration.set_modelscript_path` at the
      very **beginning** of the top-level script, before any other 
      simprovise imports::
     
           # First simprovise import
           import simprovise.core.configuration as simconfig
           simconfig.set_modelscript_path(path)
     
   This is admittedly awkward - we'd like the `modelpath` parameter to
   :meth:`~simprovise.simulation.Simulation.execute_script` or
   :meth:`~simprovise.simulation.Simulation.replicate`
   to be used automatically.
   
   Unfortunately, most of the configurable module parameters
   are set when the module is imported - hence the need to determine all of the
   files to be read up front. By the time a top-level script calls one of
   those methods it is too late.