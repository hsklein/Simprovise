============================= 
Output Reporting and Analysis
=============================

By default, **simprovise** models write their collected output data to an
SQLite3 database (the output database). This section describes 
simprovise's built-in functionality for reporting on those data and
exporting it to comma-separated-value (CSV) files, which can then be
imported into spreadsheet or other data analysis applications.

Analysts can (with some caveats) query the output database directly.
See :doc:`output_database` for more information.

Also see :doc:`data_collection` for further information how data is 
collected and organized by simprovise.


.. note::

    It is possible for simprovise modelers to bypass the built-in data 
    collection mechanisms/database and write output data on their own from
    the model itself.
    When doing so, the modeler does, however, need to take care, particularly
    when executing multiple replications via
    :meth:`simprovise.simulation.Simulation.replicate`
    This method executes replications in parallel, and each in its own
    process - so, for example, writing output to a text file is likely only to
    work if each replication opens and writes to a different file.

Accessing, Managing and Saving a Simulation Output Database
===========================================================

There are a couple of high-level use cases for running simprovise models
and analyzing/reporting on results:

* Execute the simulation, immediately generate the needed 
  :ref:`reports <built-in-summary-reporting-label>` and/or
  :ref:`output CSV files <exporting-output-data-label>`, and then delete
  the no-longer-needed output database
* Execute the simulation, possibly generate reports and/or CSV files, and
  save the output database for later use.

Accessing the Output Database After Model Execution
---------------------------------------------------

The code snippet below illustrates a typical way to run and report on a
simulation model::

    with Simulation.replicate(None, warmup_length, batch_length, 1,
                              fromRun=1, toRun=nruns) as simResult:
        simResult.print_summary(rangetype='iqr')
        simResult.save_summary_csv('mm1_summary.csv')
        simResult.export_dataset('Server', 'ProcessTime', 
                                 filename='mm1_server_processtime.csv')
 
This code executes :meth:`simprovise.simulation.Simulation.replicate`,
returning a temporary output database to the 
:class:`~simprovise.simulation.SimulationResult` context manager object
(``simResult``). The code generates a report, saves summary statistics to a
CSV file, raw data from single dataset to a second CSV file, and then exits
the ``with:`` clause, thereby deleting the temporary output database.

Saving the Output Database For Later
------------------------------------

You always have the option to save the output database for later use,
whether to generate reports, call an export function, or run your own SQL
queries. Output databases can be saved in two ways:

* Calling the :meth:`~simprovise.simulation.SimulationResult.save_database_as`
  method on class :class:`~simprovise.simulation.SimulationResult`
* Specifying an ``outputpath`` parameter to any of the 
  :class:`~simprovise.simulation.Simulation` methods 
  (:meth:`~simprovise.simulation.Simulation.execute`,
  :meth:`~simprovise.simulation.Simulation.execute_script`, or
  :meth:`~simprovise.simulation.Simulation.replicate`)
  
Code demonstrating the first call::

    with Simulation.replicate(None, warmup_length, batch_length, 1,
                              fromRun=1, toRun=nruns) as simResult:
        simResult.print_summary(rangetype='iqr')
        simResult.save_database_as('mm_1.simoutput')
        
And the second::

    Simulation.execute(warmup_length, batch_length, nbatches, 
                       outputpath='mm_1', overwrite=True) 
                     
(When ``outputpath`` is specified without an extension, the extension defaults to
``.simoutput``)

Accessing a Saved Output Database
---------------------------------

Previously saved output databases may be opened and used by creating a 
:class:`~simprovise.simulation.SimulationResult` object::

   simResult = simprovise.simulation.SimulationResult('mm1.simoutput')
   simResult.print_summary(rangetype='iqr')

The database will be closed (but **not** deleted) when ``simResult`` goes out of
scope.

.. _built-in-summary-reporting-label:

Built-in Summary Reporting
==========================

Class :class:`~simprovise.simulation.SimulationResult` provides a method -
:meth:`~simprovise.simulation.SimulationResult.print_summary` - that
generates a summary report from a simprovise output database. The report,
which may be written either to ``stdout`` or a text file, includes a number of
summary statistics - mean, median, 25th percentile, 75th percentile, and
maximum - for each :ref:`dataset <simulation-datasets-label>`
in the model.

If the output database contains data from multiple runs/replications, a 
separate summary statistic value will be calculated for each replication. 
(If a replication has multiple batches, only the *last* batch will be used.)
Those separate values will then be averaged to generate a single point
estimate for the statistic. 

For example: if one of our datasets is Queue Size and we do 20 replications,
the summary report will calculate a median queue size from the last batch
for each of the 20
replications and then report the average of those 20 values as an estimate
of the median. Those 20 values will also be used to calculate an optional
range for that median - either an IQR (inter-quartile-range), confidence
interval, or the total range (the minimum and maximum of those 20 values).

If the output database contains data from a single run with multiple batches,
the calculations will be performed using the batches in place of replications - 
i.e., batch means analysis. So if we have, for example, one run with 20
batches, we will again calculate 20 values for each summary statistic, one
per batch, and combine them in the same way that we did for the
multiple replication analysis.

Specifying the Report Destination
---------------------------------

The output summary report may be directed to either standard output or a 
file; that destination may be specified by either the ``destination``
parameter to :meth:`~simprovise.simulation.SimulationResult.print_summary`
or a **simprovise** :doc:`configuration <configuration>` file.

Using the ``destination`` parameter
***********************************

The ``destination`` parameter to 
:meth:`~simprovise.simulation.SimulationResult.print_summary` must have one
of the following types of values:

* A file-like object, which may be either a writable file or ``stdout``
* A filename (as a ``str``). 
* ``None`` (the default value), in which case the destination will be obtained
  from the configuration.
  
Using the configuration .ini file
**********************************

If the :meth:`~simprovise.simulation.SimulationResult.print_summary`
destination parameter is ``None``, the report destination will be either 
``stdout`` or file ``<modelname>_report.txt`` in the current working directory.
See :ref:`output_report_settings-label`.
  
Summary Statistics Included
---------------------------

The :meth:`~simprovise.simulation.SimulationResult.print_summary` report
calculates the following summary statistics for each 
:ref:`dataset <simulation-datasets-label>` in the model; all statistics
are time-weighted as required:

* Mean value
* Median value
* 25th Percentile value
* 75th Percentile value
* Maximum value

Optional Range Reporting
------------------------

When the output database contains data from either multiple replications or
multiple batches, the `rangetype` parameter to
:meth:`~simprovise.simulation.SimulationResult.print_summary`
may be used to add additional range or confidence information to the 
point estimate for each summary statistic.

The rangetype parameter may be either ``None`` or one of the following string
values (case-insensitive):

* ``IQR``: Generate the Inter-Quartile-Range for each statistic. For example,
  if we have 20 replications, the report will find 20 values for the
  dataset Maximum, one per replication. The point estimate of the Maximum is
  the average of those 20 values. The IQR for the maximum is the 25th 
  and 75th percentile of **those 20 maximum values**. (Note that that is
  *completely separate* from the 25th and 75th percentile statistics for the
  entire dataset, which can be confusing.)
* ``TOTAL``: Generate the total range for each summary statistic. Using the 
  example above, the TOTAL range for the Maximum would be the minimum and
  maximum of the 20 maximum values, one per replication.
* ``90CI``: Calculate a 90% confidence interval for each summary statistic
  using a T distribution. Again per our example, the input values to the
  calculation are the 20 per-replication values.
* ``95CI``: Calculate a 95% confidence interval for each summary statistic (in
  the same way as for the 90% interval)
  
A few other notes:

* If ``rangetype`` is `None`, no ranges will be calculated.
* If there is only one batch and one replication in the database, no ranges
  will be calculated.
* If is more than one replication or more than one batch, but that number is
  **very** low (e.g 2-4), the range calculation may result in meaningless or
  NaN (Not a Number) results for the range values.


Implementation/Algorithm Notes
------------------------------

A few notes and caveats on the statistics generated by the summary report:

* The techniques used apply primarily to steady-state simulations; for
  terminating simulations, other techniques (instead of and/or in addition to
  these) should probably be used, as discussed in most texts covering 
  simulation output analysis.
  
* For steady-state simulations, the modeler/analyst must ensure that the
  warmup period is sufficiently long to reach steady-state.

* The statistical techniques used to generate point estimates, ranges, and
  confidence intervals assume that the batches or replications are 
  independent. In the case of batch means analysis, there is almost always
  going to be some auto-correlation between batches, but sufficiently
  long batches are likely to be "independent enough". It is again up to the
  modeler/analyst to make that determination.
  
* While replications should generate statistically independent results,
  the modeler/analyst must still ensure that the run length after warmup
  is sufficient to gather enough data and avoid cyclic effects that might be
  inherent in the model.
  
* The use of the mean of the summary statistic values generated for
  each replication is perhaps not obvious and might be pushing it in some
  situations for some of the order statistics. That choice was made based
  on the Banks and Carson text 
  (*Discrete-Event System Simulation*, Prentice Hall, Third Edition p. 440)
  
* The report currently generates all confidence intervals using a 
  a T distribution, based again on the Banks and Carson reference above.
  Confidence intervals are calculated via the 
  `SciPy stats.t <https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.t.html#scipy-stats-t>`_ 
  ``interval`` function. Use of a normal distribution for calculating 
  confidence intervals *might* be appropriate if *n* (the number of 
  replications/batches) is "large enough", but we in the absence of more
  information, we defer to the more conservative approach. For analysts
  choosing their own adventure, confidence intervals via the normal distribution
  can be calculated via 
  `SciPy stats.norm <https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.norm.html#scipy.stats.norm>`_ 
  See also the :ref:`simprovise.core.stats module<simprovise-core-stats-label>`.
    
* The author considers themself to have some mathematical competency, but is
  most definitely **not** a professional statistician. Users are strongly
  urged to consult one and/or an appropriate text :-).

.. _exporting-output-data-label:

Exporting Output Data
=====================

Class :class:`~simprovise.simulation.SimulationResult` provides two methods
that export data from an output database to a comma-separated-value (CSV)
file:

* :meth:`~simprovise.simulation.SimulationResult.save_summary_csv` 
  :ref:`exports summary statistics <export-summary-statistics-label>` to a
  CSV file.
* :meth:`~simprovise.simulation.SimulationResult.export_dataset` 
  :ref:`exports the raw values from a single dataset <export-raw-data-label>` 
  to a CSV file.
  
.. _export-summary-statistics-label:

Exporting Summary Statistics
----------------------------

Method :meth:`~simprovise.simulation.SimulationResult.save_summary_csv` 
calculates and exports summary statistics for each 
:ref:`dataset <simulation-datasets-label>` in the model. 

Like the :ref:`summary report <built-in-summary-reporting-label>`, summary
statistics are calculated for either:

* The last batch in every replication, when there are multiple replications, or
* Every batch in a single replication

The export includes the following statistics, all time-weighted as required:

* Count: the number of values in the dataset for the batch/replication
* Mean: the mean dataset value for the batch/replication
* Min: the minimum dataset value for the batch/replication
* Max: the maximum dataset value for the batch/replication
* 5th Percentile: the 5th percentile dataset value for the batch/replication
* 10th Percentile: the 10th percentile dataset value for the batch/replication
* 25th Percentile: the 25th percentile dataset value for the batch/replication
* Median: the median dataset value for the batch/replication
* 75th Percentile: the 75th percentile dataset value for the batch/replication
* 90th Percentile: the 90th percentile dataset value for the batch/replication
* 95th Percentile: the 95th percentile dataset value for the batch/replication

.. note::

   For ``Entries`` datasets, only the ``Count`` statistic is exported; for
   ``Utilization`` and ``DownTime`` datasets, only the ``Mean`` is exported. 
   For these datasets, the other statistics are not applicable
   
Each row in the exported file contains the following comma separated values:

* Element ID
* Dataset Name
* Dataset Time Unit (if applicable)
* Summary Statistic Name
* Summary Statistic values for each replication/batch (comma separated)

*Unlike* the summary report, the export does **not** calculate or include
the mean value of each statistic over all replications/batches; as noted
above, it includes the values for each replication batch (each in their
own column). The analyst can than calculate/report overall results as they
see fit.

.. _export-raw-data-label:

Exporting Raw Data
------------------

Method :meth:`~simprovise.simulation.SimulationResult.export_dataset` exports
the raw dataset values for a single :ref:`dataset <simulation-datasets-label>` 
to a CSV file. The caller may export
data for every replication and batch in the output database, or limit the
export to a single replication and/or single batch.

Each row in the export contains the following comma-separated values:

* Dataset Number: The output database dataset key value
* Run/Replication Number
* Batch Number: zero for the warmup, 1+ for subsequent batches
* Timestamp: The simulated time for the data value, or, for time-weighted
  datasets, the time that this value was set
* To Timestamp: For time-weighted datasets, the simulated time that that
  this value was changed to something else (blank for unweighted datasets)
* Dataset Value
* Time Unit: The dataset time unit (blank for non-
  :class:`~simprovise.core.simtime.SimTime` datasets).
