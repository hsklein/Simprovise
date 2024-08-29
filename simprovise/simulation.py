#===============================================================================
# MODULE simulation
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the Simulation class, which functions as a namespace for the global
# simulation generation and execution API; its methods are all static.
#
# Also defines the SimResults class, an instance of which is returned by the
# Simulation's execute/replicate methods.
#
# This program is free software: you can redistribute it and/or modify it under 
# the terms of the GNU General Public License as published by the Free Software 
# Foundation, either version 3 of the License, or (at your option) any later 
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT 
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#===============================================================================
import os, sys, shutil, types, csv
from contextlib import redirect_stdout
import numpy as np
import scipy.stats as st

#SCRIPTPATH = "models\\mm1.py"
#os.environ["SIMPROVISE_MODEL_SCRIPT"] = SCRIPTPATH


from simprovise.core.model import SimModel
from simprovise.runcontrol.replication import (SimReplication, SimReplicator)
from simprovise.runcontrol.simruncontrol import (SimReplicationParameters)
from simprovise.database import (SimDatabaseManager, SimDatasetSummaryData,
                                 SimDatasetValues)
from simprovise.core import SimError
from simprovise.core.simlogging import SimLogging
from simprovise.core.simtime import SimTime, Unit as tu
import simprovise.core.configuration as simconfig
import simprovise.core.stats as simstats
from simprovise.core.apidoc import apidoc, apidocskip

_ERROR_NAME = "Simulation Error"
_RESULT_ERROR = "Simulation Result Error"
_MIN_IQR_RUNS = 4
_DEFAULT_OUTPUTDB_EXT = ".simoutput"
_NAN = float('nan')
_REPORT_SUFFIX = '_report'
_REPORT_EXT = '.txt'

logger = SimLogging.get_logger(__name__)

@apidoc
class Simulation(object):
    """
    The Simulation class functions as a namespace providing, through
    static methods, high-level functions for the execution of simulation
    models.
    
    :meth:`execute` facilitates the execution of a single simulation run
    from within a model script. :meth:`execute_script` executes a single
    simulation run of a model defined by a passed model script path (and
    should not be called from within a model script). Finally,
    :meth:`replicate` executes multiple replications of a simulation model,
    again designated by a passed model script path; :meth:`replicate` can
    be used both from within and outside of a model script. All of these
    methods return a :class:`SimulationResult` object.
    
    These methods all provide the option to save the resulting output
    database to a specified file location. The database may also be saved
    via the :class:`SimulationResult` object; the advantage of doing so via
    the execute() methods is that the designated output path will be
    validated prior to the simulation; when doing so via :class:`SimulationResult`
    the validation won't occur until after the (potentially long running)
    simulation completes; if the output path is invalid, the simulation
    results are likely to be lost.
    """

    @staticmethod
    def execute(warmupLength=0, batchLength=None, nBatches=1, *,
                runNumber=1, outputpath=None, overwrite=False):
        """
        Execute the initialized populated Simulation.model().

        This method is designed to be called directly from the __main__ 
        scope of a model script, e.g.:

           with Simulation.execute(warmuplen, batchlen, nbatches) as simResult:
               # Do something with the simulation result
               
        The output database resulting from the simulation run may optionally
        be saved to a specified filepath.
               
        :param warmupLength: The length of the simulation warmup period,
                             in simulated time. Defaults to zero
        :type warmupLength:  :class:`~.simtime.SimTime`
        
        :param batchLength:  The length of each simulation batch, in
                             simulated time. Raises if not set or not greater
                             than zero.
        :type batchLength:   :class:`~.simtime.SimTime`
        
        :param nBatches:     Then number of batches to simulate. Raises if
                             not greater than zero
        :type nBatches:      int
        
        :param runNumber:    The designated run number of the simulation run.
                             Defaults to 1. Raises if not greater than zero.
        :type runNumber:     int
        
        :param outputpath:   The path (including filename, extension optional)
                             to which the output database should be saved after
                             execution. Defaults to None (the database is not saved)
        :type outputpath:    str
        
        :param overwrite:    Flag indicating whether any existing saved output
                             database can be overwritten. Defaults to False.
                             Should only be True if outputpath is not None
        :type overwrite:     bool
        
        :raises:             :class:`~.simexception.SimError`
                             Raised if parameters are invalid or an error
                             occurs during the simulation.
        
        :return:             Result object wrapping simulation output database
        :rtype:              :class:`SimulationResult`
        
        """
        # get an absolute path after validating - will raise if invalid
        outputpath = Simulation._valid_outputpath(outputpath, overwrite)
        
        model = SimModel.model()

        replication = SimReplication(model, runNumber,
                                     warmupLength, batchLength, nBatches)
        replication.execute()       
        if outputpath:
            Simulation._save_output(replication.dbPath, outputpath)
            
        return SimulationResult(replication.dbPath, model.filename, 
                                isTemporary=True)

    @staticmethod
    def execute_script(modelpath, warmupLength=None, batchLength=None,
                       nBatches=1, *, runNumber=1,
                       outputpath=None, overwrite=False):
        """
        Start a single in-process simulation run from a somewhere other
        than the model script.

        :param modelpath:    The full path of the model script file.
                             in simulated time. Defaults to zero
        :type modelpath:     str
        
        :param warmupLength: The length of the simulation warmup period,
                             in simulated time. Defaults to zero
        :type warmupLength:  :class:`~.simtime.SimTime`
        
        :param batchLength:  The length of each simulation batch, in
                             simulated time. Raises if not set or not greater
                             than zero.
        :type batchLength:   :class:`~.simtime.SimTime`
        
        :param nBatches:     Then number of batches to simulate. Raises if
                             not greater than zero
        :type nBatches:      int
        
        :param runNumber:    The designated run number of the simulation run.
                             Defaults to 1. Raises if not greater than zero.
        :type runNumber:     int
        
        :param outputpath:   The path (including filename, extension optional)
                             to which the output database should be saved after
                             execution. Defaults to None (the database is not saved)
        :type outputpath:    str
        
        :param overwrite:    Flag indicating whether any existing saved output
                             database can be overwritten. Defaults to False.
                             Should only be True if outputpath is not None
        :type overwrite:     bool
        
        :raises:             :class:`~.simexception.SimError`
                             Raised if parameters are invalid or an error
                             occurs during the simulation.
        
        :return:             Result object wrapping simulation output database
        :rtype:              :class:`SimulationResult`

        """
        # get an absolute path after validating - will raise if invalid
        outputpath = Simulation._valid_outputpath(outputpath, overwrite)
        
        model = SimModel.load_model_from_script(modelpath)
        
        logger.debug("\n loaded Model elements: ")
        for e in model.elements:
            logger.debug(e.element_id)            
             
        replication = SimReplication(model, runNumber,
                                     warmupLength, batchLength, nBatches)
        replication.execute()       
        if outputpath:
            Simulation._save_output(replication.dbPath, outputpath)
        
        return SimulationResult(replication.dbPath, modelpath, isTemporary=True)

    @staticmethod
    def replicate(modelpath, warmupLength=None, batchLength=None, nBatches=1,
                  *, fromRun=1, toRun=8, outputpath=None, overwrite=False):
        """
        Start one or more simulation replications (with different random
        number streams), each in their own process. Replications can run in
        parallel, depending on system configuration.
        
        Can be invoked from any script, including the model script. In either
        case,the top of the call stack should be within that top-level script's
        __main__ guard, since this call will ultimately involve use of a
        multiprocessing Pool.
        (See https://docs.python.org/3/library/multiprocessing.html#multiprocessing-programming)
        
        If the top-level invoking script is the model script itself, the
        modelpath parameter should be set to None, which will ensure  that
        the model script is never loaded via `SimModel.load_model_from_script()`;
        the replication processes created by the multiprocessing pool will
        import the top-level script on their own, so an additional load
        will generate errors.
        
        :param modelpath:    The full path of the model script file or None.
        :type modelpath:     str or None
        
        :param warmupLength: The length of the simulation warmup period,
                             in simulated time. Defaults to zero
        :type warmupLength:  :class:`~.simtime.SimTime`
        
        :param batchLength:  The length of each simulation batch, in
                             simulated time. Raises if not set or not greater
                             than zero.
        :type batchLength:   :class:`~.simtime.SimTime`
        
        :param nBatches:     Then number of batches to simulate. Raises if
                             not greater than zero
        :type nBatches:      int
        
        :param fromRun:      The run number for first replication. Must be
                             in range 1-100. Defaults to 1.
        :type runNumber:     int
        
        :param toRun:        The run number for first replication. Must be
                             in range 1-100, and >= fromRun. Defaults to 8.
        :type runNumber:     int
        
        :param outputpath:   The path (including filename, extension optional)
                             to which the output database should be saved after
                             execution. Defaults to None (the database is not saved)
        :type outputpath:    str
        
        :param overwrite:    Flag indicating whether any existing saved output
                             database can be overwritten. Defaults to False.
                             Should only be True if outputpath is not None
        :type overwrite:     bool
        
        :raises:             :class:`~.simexception.SimError`
                             Raised if parameters are invalid or an error
                             occurs during the simulation.
        
        :return:             Result object wrapping simulation output database
        :rtype:              :class:`SimulationResult`
        
        """
        # get an absolute path after validating - will raise if invalid
        outputpath = Simulation._valid_outputpath(outputpath, overwrite)
        
        if not modelpath or SimModel.model().filename == modelpath:
            model = SimModel.model()
        else:           
            model = SimModel.load_model_from_script(modelpath)

        replicationParameters = SimReplicationParameters()
        replicationParameters.set_replication_range(fromRun, toRun)
        replicator = SimReplicator(model, warmupLength, batchLength, nBatches)
        
        # Use the replicator as a context manager to best ensure temporary
        # database files are cleaned up.
        with replicator:            
            replicator.execute_replications(replicationParameters, asynch=False)
            if outputpath:
                Simulation._save_output(replicator.output_dbpath, outputpath)
            return SimulationResult(replicator.output_dbpath, model.filename, 
                                    isTemporary=True)

    @staticmethod
    def _valid_outputpath(outputpath, overwrite):
        """
        Validates passed output database path. If path does not include a
        file extension, it will add the default output database extension.
        Returns the (possibly refornatted) absolute path with extension.
        
        Raises a :class:`~.simexception.SimError` if:
        - overwrite is True and no output path is specified
        - the path exists and overwrite is not specified as True
        - the path is an existing directory (which presumably also means
          that no extension was provided)
        - the path includes a non-existing directory
        """
        #if not isinstance(outputpath, (types.NoneType, str)):
        # types.NoneType introduced in Python 3.10. This one change appears to
        # be sufficient to support Python 3.9
        if not isinstance(outputpath, str) and outputpath is not None:
            msg = "Invalid outputpath parameter value {0}: type must be str or None"
            raise SimError(_ERROR_NAME, msg, outputpath)
        
        nulloutputpath = not outputpath or outputpath.strip() == '' 
        if not overwrite and nulloutputpath:
            return None
            
        if overwrite and nulloutputpath:
            msg = "outputpath parameter must be specified when overwrite parameter is True"
            raise SimError(_ERROR_NAME, msg)
            
        outputpath = os.path.abspath(outputpath).strip()
        if os.path.splitext(outputpath)[1] == '':
            outputpath = outputpath + _DEFAULT_OUTPUTDB_EXT           
       
        if os.path.exists(outputpath) and not overwrite:
            msg = "Specified output filename {0} exists; set overwrite parameter to True to overwrite"
            raise SimError(_ERROR_NAME, msg, outputpath)
      
        outputdir = os.path.dirname(outputpath)
        if outputdir and not os.path.exists(outputdir):
            msg = "Specified output filename {0} does not specify an existing directory"
            raise SimError(_ERROR_NAME, msg, outputpath)
        
        return outputpath
    
    @staticmethod
    def _save_output(dbpath, outputpath):
        """
        Copies dbpath to outputpath, catching and re-raising any exceptions
        """
        try:        
            # Create the directory as required
            if os.path.dirname(outputpath):
                os.makedirs(os.path.dirname(outputpath), exist_ok=True)
            
            shutil.copy(dbpath, outputpath)
            print("copy of output database saved to:", outputpath)
        except Exception as e:
            msg = "Failure saving output database: failure copying {0} to {1}: {2}"
            raise SimError(_ERROR_NAME, msg, dbpath, outputpath, e)
            


@apidoc
class SimulationResult(object):
    """
    SimulationResult wraps the output (database) of a simulation , and
    implements various operations (reports, database save, csv file
    generation) on that output. 
    
    :meth:`Simulation.execute`, :meth:`Simulation.executeScript` and
    :meth:`Simulation.replicate` all return SimulationResult objects.
    Client code may also generate reports and/or csv files from  saved output
    databases by creating a SimulationResult.

    SimulationResult instances are context managers that close the database
    on exit. If the database is temporary, the database is therefore deleted
    on exit unless explicitly saved.
    
        :param dbpath:      The path of the output database to read
        :type dbpath:       `str`
        
        :param modelpath:   The path of the model script file, if any
        :type modelpath:    `str` or `None` (if opening a previously saved DB)
       
        :param isTemporary: Flag indicating whether the database is temporary.
                            If temporary and not explicitly saved via
                            :meth:`save_database_as`, the database is deleted
                            on exit. Defaults to False.
        :type isTemporary:  `bool`
        
    """
    # NOTE on directing output to a file (7/26/24)
    #
    # 1. Add a destination parameter to print_summary(), which can be:
    #    - None, in which case use configuration to determine output
    #    - a string, which will be assumed to be the report output filepath
    #    - anything else is assumed to be a file object (possibly stdout)
    #    The default should be None
    #
    # 3. If output is to a file, the default filename should include the
    #    model name, so SimModel.filename or modelpath should be passed
    #    to the SimulationResult initializer
    
    def __init__(self, dbpath, modelpath=None, isTemporary=False):
        """
        Open the database (specified by dbpath) via SimDatabaseManager.
        If a model is specified, we assume the database is temporary; if no
        model is specified, the database was presumably saved previously and
        is opened as an archive.

        TODO look at gathering data (SimDatasetStatistic objects) in initializer,
        to be available to reporting/output methods.
        """
        logger.info("Simulation result created for output DB %s isTemporary: %s",
                    dbpath, isTemporary)
        self.modelpath = modelpath
        self.dbMgr = SimDatabaseManager()
        self.dbMgr.open_archived_database(dbpath, isTemporary)
        self.datasetStatistics = None

    @apidocskip
    def __enter__(self):
        return self

    @apidocskip
    def __exit__(self, typ, value, traceback):
        """
        Close the database if it is open. If the database is temporary, it will
        be deleted as well.
        """
        if self.dbMgr.has_open_database():
            if self.dbMgr.database.is_temporary:
                print("Closing and removing output database...")
                self.dbMgr.close_output_database(delete=True)
            else:
                print("Closing output database", self.dbMgr.database.db_path, "...")
                self.dbMgr.close_output_database()

    def _get_sim_dataset_statistics(self, dataset):
        """
        Internal method returns SimDatasetStatistics object for a specified
        dataset.

        Lazily initializes the datasetStatistics member dictionary, which
        when initialized contains a SimDatasetStatistics instance for each
        dataset in the current database; the dictionary is keyed by dataset
        element_id and dataset name.
        """
        if self.datasetStatistics is None:
            self.datasetStatistics = {}
            database = self.dbMgr.database
            assert database, "SimResult database not open"
            if not database.runs():
                raise SimError(_RESULT_ERROR,
                               "SimResult database has no simulation runs")

            datasets = database.datasets
            dsetstats = self.datasetStatistics
            for dset in datasets:
                dsetstats.setdefault(dset.element_id, {})[dset.name] = \
                    SimDatasetStatistics(database, dset)

        assert dataset.element_id in self.datasetStatistics, "Element ID not found"
        assert dataset.name in self.datasetStatistics[dataset.element_id], "Dataset name not found"

        return self.datasetStatistics[dataset.element_id][dataset.name]

    def save_database_as(self, filename):
        """
        Close the temporary output database and save it to a caller-specified
        location - otherwise, the database is deleted on exit.
        
        .. note::
        
            The "close database" side-effect means that:
            
            * Report/export methods **cannot be called after save_database_as()**
            * This method can only be called once - i.e., multiple saves to
              different locations cannot be invoked without re-opening the
              database.

        :param filename: The path/filename to which the output database is
                         saved. Extension would typically be '.simoutput', but
                         this is neither checked nor required.
        :type filename:  str

        """
        # TODO better error checking in closeOutputDatabase, overwrite checking?
        assert self.dbMgr.has_open_database(), "Cannot save non-open database"
        assert self.dbMgr.database.is_temporary, "Cannot save non-temporary (archive) database"

        print("Closing and saving output database to {0}...".format(filename))
        self.dbMgr.close_output_database(savePath=filename)

    def save_summary_csv(self, filename):
        """
        Save summary statistics for each dataset/run/batch as a comma-separated-
        values (csv) file.

        :param filename: Absolute path to which the csv file is saved. Extension
                         would typically be '.csv', but this is neither checked
                         nor required.
        :type filename:  str

        """
        unitName = ('seconds', 'minutes', 'hours')
        def unitstr(dataset):
            if dataset.valuetype == 'SimTime' and dataset.timeunit is not None:
                return unitName[dataset.timeunit]
            else:
                return ''

        database = self.dbMgr.database
        assert database, "SimResult database not open"
        runs = database.runs()
        if not runs:
            raise SimError(_RESULT_ERROR, "Result database has no simulation runs")
        #nbatches = database.last_batch(runs[0])
        datasets = database.datasets
        if not datasets:
            raise SimError(_RESULT_ERROR, "Result database has no datasets")
        
        runs = database.runs()
        assert runs, "No runs in output database"
        nbatches = database.last_batch(runs[0])
        
        if len(runs) > 1 or nbatches == 0:
            nsamples = len(runs)
            sample_type = 'Run'
        else:
            nsamples = nbatches
            sample_type = 'Batch'
            
        def print_row(dset, statistic_name, sample_values):
            if sample_values.n == 0:
                return
            
            print(dset.element_id, dset.name, unitstr(dset), statistic_name, 
                  sep=',', end='', file=f)            
            for value in sample_values:
                print(',', value, end='', file=f)
            print('', file=f) 
                                
        # Create the directory as required
        if os.path.dirname(filename):
            os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            print('ElementID', 'Dataset', 'Unit', 'Statistic', sep=',', end='', file=f)
            for i in range(nsamples):
                print(',', sample_type, i+1, end='', file=f)
            print('', file=f)
            
            for dset in datasets:
                dsetstats = self._get_sim_dataset_statistics(dset)
                if dset.name == 'Entries':
                    # For Entries datasets, the count is the only value
                    print_row(dset, 'Count', dsetstats.counts)
                elif dset.name == 'Utilization' or dset.name == 'DownTime':
                    # For Utilization and DownTime, the mean is the only useful value
                    print_row(dset, 'Mean', dsetstats.means)
                else:
                    # For other datasets, print the whole shabang
                    print_row(dset, 'Count', dsetstats.counts)
                    print_row(dset, 'Mean', dsetstats.means)
                    print_row(dset, 'Min', dsetstats.mins)
                    print_row(dset, 'Max', dsetstats.maxs)
                    print_row(dset, '5th Percentile', dsetstats.pct05s)
                    print_row(dset, '10th Percentile', dsetstats.pct10s)
                    print_row(dset, '25th Percentile', dsetstats.pct25s)
                    print_row(dset, 'Median', dsetstats.medians)
                    print_row(dset, '75th Percentile', dsetstats.pct75s)
                    print_row(dset, '90th Percentile', dsetstats.pct90s)
                    print_row(dset, '95th Percentile', dsetstats.pct95s)
 
 
    def print_summary(self, *, rangetype=None, destination=None):
        """
        Print a summary report for the simulation output. For each dataset,
        the report generates an estimate for the following summary statistics,
        all time-weighted as required:
        
        * Mean dataset value
        * Median dataset value
        * 25th percentile dataset value
        * 75th percentile dataset value
        * Maximum dataset value
        
        .. note::
            One assumption here is that this is essentially a steady-state
            simulation model and we have collected a large number of dataset
            values for each run/replication. For terminating simulations
            generating a single value for a measure of interest, different
            reporting and analysis techniques would apply.
        
        If multiple runs/replications of the simulation were performed, values
        for each of the above statistics are calculated for each replication.
        If only a single simulation run was performed, values are calculated for
        each batch within that run. For example, if we do 20 replications, we
        will have a set of 20 values for the mean dataset value, 20 values for
        the median, etc. The report uses those mean of those 20 values to
        construct a point estimate for each summary statistic. 
        
        If the rangetype parameter is specified, a spread indicator is also
        shown for each summary statistic; the indicators supported are:
                        
        * 'iqr' (Interquartile range)
        * '90ci' (90% confidence interval)
        * '95ci' (95% confidence interval)
        * 'total' (minimum and maximum)

        These spread range indicators refer to the calculated statistic, NOT the
        underlying dataset values. For example, if rangetype is 'total' and
        the database has 20 replication runs, then the "Sample Max" column for a
        dataset wll display the average of the maximum dataset values for each of
        those 20 replications, plus a range [min-max] that indicate the lowest
        and highest of those 20 observed maximums. For IQR, the range is the
        25th and 75th percentiles of those 20 maximum values. Confidence
        intervals are constructed using a T distribution.
        
        .. note::
            See Carson and Banks (3rd edition p. 440) re the choice to use
            the mean of the calculated summary statistic as the point estimate
            and the T distribution for confidence interval calculation.
            Use of a normal distribution for the CE  could be appropriate
            for a "sufficiently large" number of replications/batches, but
            we defer to the more conservative approach here.
                 
        If the destination parameter is ``None``, the destination is obtained
        from the configuration file, which should be either 'stdout' or
        'file'; if 'file', the destination will be a file in the current
        working directory named <model name>_report.txt
        
        :param rangetype:   '`iqr`', '`90ci`', '`95ci`','`total`' or `None`. 
        :type  rangetype:   ``str``
        
        :param destination: file object (can be stdout), filename or ``None``. 
        :type destination:  file object, ``str`` or ``None``
        
        :raises:            :class:`~.simexception.SimError`
                            Raised if rangetype is invalid.

        """
        if not self.dbMgr.has_open_database:
            raise SimError(_RESULT_ERROR, "SimulationResult database is not open")
        
        output_filename = None
        f = None

        if destination is None:
            # Get destination from configuration file
            if simconfig.get_output_report_destination() == 'stdout':
                f = sys.stdout
            elif self.modelpath:
                base = os.path.splitext(os.path.basename(self.modelpath))[0]
                output_filename = base +  _REPORT_SUFFIX + _REPORT_EXT
            else:
                dbpath = self.dbMgr.current_database_path
                assert not self.dbMgr.database.is_temporary
                assert dbpath
                base = os.path.splitext(os.path.basename(dbpath))[0]
                output_filename = base +  _REPORT_SUFFIX + _REPORT_EXT
        elif isinstance(destination, str):
            output_filename = destination
        else:
            f = destination
            
        if f == sys.stdout:
            self._print_summary_impl(rangetype)
        elif f:
            with redirect_stdout(f):
                self._print_summary_impl(rangetype)                
        else:
            # Create the directory as required
            if os.path.dirname(output_filename):
                os.makedirs(os.path.dirname(output_filename), exist_ok=True)
            with open(output_filename, 'w') as f:
                with redirect_stdout(f):
                    self._print_summary_impl(rangetype)                
                
            
    def _print_summary_impl(self, rangetype=None):
        """
        Print formatted summary statistics for the simulation output. In the
        base report, summary statistics for multiple runs/batches are shown as
        the mean of the statistic values calculated for each run/batch in
        the result database. (If the database has multiple runs, it is the
        average of the calculated result for each run; if it is a single run
        with multiple batches, it is the average of the calculated result for
        each batch.)

        If the rangetype argument is specified, a spread indicator is also
        shown for each summary statistic; the indicators supported are:
        
        * 'iqr' (Interquartile range)
        * '90ci' (90% confidence interval)
        * '95ci' (95% confidence interval)
        * 'total' (minimum and maximum)

        The spread range indicators refer to the calculated statistic, NOT the
        underlying dataset values. For example, if rangetype is 'total' and
        the database has 10 replication runs, then the "Median" column for a
        dataset wll display the mean of the calculated medians for each of
        those ten replications, plus a range [min-max] that indicate the lowest
        and highest of those ten calculated medians.
        
        :param rangetype: 'iqr', '90ci', '95ci', 'total' or None. 
        :type rangetype:  `str`
        
        :raises:          :class:`~.simexception.SimError`
                          Raised if rangetype is invalid.

        """
        database = self.dbMgr.database
        assert database
        datasets = database.datasets

        runs = database.runs()
        nruns = len(runs)
        if not runs:
            raise SimError(_RESULT_ERROR, "Result database has no simulation runs")
        nbatches = database.last_batch(runs[0])

        if nruns == 1 and nbatches == 1:
            # If there's only one run and one batch, there's no range to get
            rangetype = None
            
        confidence_level = None

        if rangetype is None:
            rangeprop = None
            rangelabel = ''
        elif rangetype.lower() == 'iqr':
            rangeprop = SimSample.iqr
            rangelabel = '   IQR'
        elif rangetype.lower() == '90ci':
            rangeprop = SimSample.confidence_interval90
            rangelabel = '   90% CI'
        elif rangetype.lower() == '95ci':
            rangeprop = SimSample.confidence_interval95
            rangelabel = '   95% CI'
        elif rangetype.lower() == 'total':
            rangeprop = SimSample.minmaxrange
            rangelabel = '  Range'
        else:
            raise SimError(_RESULT_ERROR, "Invalid range type specified: {}", rangetype)

        eidwidth, namewidth, numwidth, numcolwidth = self._getFormatWidths()

        meanwidth = numwidth + 8    # width of mean value with time unit string
        sdwidth = numwidth          # standard deviation is shown without time units
        iqrwidth = numwidth * 2 + 3 # IQR width is two numbers, plus braces and dash

        if nruns == 1:
            if nbatches > 1:
                batchstr = ', {:d} Batches'.format(nbatches)
            else:
                batchstr = ', 1 Batch'
        else:
            batchstr = ''

        replstr = 'Replications' if nruns > 1 else 'Replication'
        header0 = 'Results: {:d} {}{}'.format(nruns, replstr, batchstr)

        if rangetype:
            wmeans = meanwidth + sdwidth + iqrwidth + 2
            wrest = meanwidth + iqrwidth + 1
            header1fmt = '{:{ew}} {:{nw}} {:^{wm}} {:^{wr}} {:^{wr}} {:^{wr}} {:^{wr}}'
            header1 = header1fmt.format('Element ID', 'Dataset', 'Sample Mean',
                                        'Sample 25th Percentile', 'Sample Median',
                                        'Sample 75th Percentile', 'Sample Max',
                                         ew=eidwidth, nw=namewidth, wm=wmeans,
                                        wr=wrest)

            header2fmt = '{:{en}} {:^{mw}} {:>{mn}} {:{mr}}' + ' {:^{mw}} {:{mr}}' * 4
            header2items = ['', 'Mean', 'SEM', rangelabel] + ['Mean', rangelabel] * 4
            header2 = header2fmt.format(*header2items, en=eidwidth+namewidth+1,
                                        mw=meanwidth, mn=sdwidth, mr=iqrwidth)
        else:
            colwidth = meanwidth
            header1fmt = '{:{ew}} {:{nw}} {:^{numw}} {:^{cw}} {:^{cw}} {:^{cw}} {:^{cw}} {:^{cw}}'
            header1 = header1fmt.format('Element ID', 'Dataset',
                                        'Sample Size', 'Sample Mean',
                                        '25th Percentile', 'Median',
                                        '75th Percentile', 'Max',
                                        ew=eidwidth, nw=namewidth, numw=numwidth,
                                        cw=colwidth)
            header2 = ''

        print('-' * len(header1))
        print('{:^{headerlen}}'.format(header0, headerlen=len(header1)))
        print(header1)
        if header2:
            print(header2)
        print('-' * len(header1))

        for dset in datasets:
            dsetstats = self._get_sim_dataset_statistics(dset)
            if dsetstats.nsamples == 0:
                continue

            print("{:{ew}} {:{nw}}".format(dset.element_id, dset.name,
                                          ew=eidwidth, nw=namewidth),
                   end=' ')
            if rangetype:
                print(_value_to_string(dsetstats.means.mean, numwidth),
                      _value_to_string(dsetstats.means.stderr, numwidth, False),
                      _range_to_string(rangeprop.fget(dsetstats.means), numwidth, False),
                      _value_to_string(dsetstats.pct25s.mean, numwidth),
                      _range_to_string(rangeprop.fget(dsetstats.pct25s), numwidth, False),
                      _value_to_string(dsetstats.medians.mean, numwidth),
                      _range_to_string(rangeprop.fget(dsetstats.medians), numwidth, False),
                      _value_to_string(dsetstats.pct75s.mean, numwidth),
                      _range_to_string(rangeprop.fget(dsetstats.pct75s), numwidth, False),
                      _value_to_string(dsetstats.maxs.mean, numwidth),
                      _range_to_string(rangeprop.fget(dsetstats.maxs), numwidth, False)
                     )
            else:
                print(_value_to_string(dsetstats.counts.mean, numwidth, False),
                      _value_to_string(dsetstats.means.mean, numwidth),
                      _value_to_string(dsetstats.pct25s.mean, numwidth),
                      _value_to_string(dsetstats.medians.mean, numwidth),
                      _value_to_string(dsetstats.pct75s.mean, numwidth),
                      _value_to_string(dsetstats.maxs.mean, numwidth)
                     )

    def _getFormatWidths(self):
        """
        """
        datasets = self.dbMgr.current_datasets()
        eidwidth = max([len(dset.element_id) for dset in datasets])
        namewidth = max([len(dset.name) for dset in datasets])
        numberwidth = 9
        numcolwidth = numberwidth + 8 # add 8 for time unit string

        return eidwidth, namewidth, numberwidth, numcolwidth
    
    def export_dataset(self, elementid, datasetname, *, run=-1, batch=None, filename):
        """
        Export some or all of the raw values for a dataset specified by passed
        element ID and dataset name. The export can be limited to a single
        run (specified by run number) and/or a single batch (specified by
        number or ``None``, for the last batch in the run(s)).
        
        The export starts with a header row (column names); each subsequent
        row corresponds to a row in the output database ``datasetvalue`` table,
        with the following fields:
        
        * dataset number
        * run number
        * batch number
        * simulated timestamp
        * simulated to timestamp (for time-weighted datasets, empty for
          unweighted datasets)
        * dataset value
        * timeunit (as a string) - blank for non-SimTime dataset values
    
        :param elementid:  ID of element exported dataset belongs to
        :type elementid:   `str`
        
        :param datasetname: Name of dataset to export
        :type datasetname:  `str`
        
        :param run:         Run number or -1 for all runs
        :type run:          `int`
        
        :param batch:       Batch number or -1 for all batches, or `None` for 
                            last batch
        :type batch:        `int` or `None`
        
        :param filename:    Path/filename of CSV file to which exported data is
                            to be written. (Expected to have extension .csv,
                            but not required). If the path is not absolute, it
                            is relative to the current working directory.
        :type filename:     `str`
        
        """
        # Parameter validation
        if not elementid:
            raise SimError(_RESULT_ERROR, "export_dataset elementid parameter is null")
        if not datasetname:
            raise SimError(_RESULT_ERROR, "export_dataset datasetname parameter is null")
        if not isinstance(run, int):
            raise SimError(_RESULT_ERROR, "export_dataset run parameter is not an int")
        if batch is not None and not isinstance(batch, int):
            raise SimError(_RESULT_ERROR, "export_dataset batch parameter is not an int")
        
        if run != -1 and run < 1:
            msg = "export_dataset run parameter ({0}) must be -1 or positive"
            raise SimError(_RESULT_ERROR, msg, run)
        if batch is not None and batch < -1:
            msg = "export_dataset batch parameter ({0}) must be None, -1 or > 0"
            raise SimError(_RESULT_ERROR, msg, batch)
            
        database = self.dbMgr.database
        assert database, "SimResult database not open"
        runs = database.runs()
        
        # More parameter validation
        if not runs:
            raise SimError(_RESULT_ERROR, "Output database has no simulation runs")
        if run > 0 and not run in runs:
            msg = "export_dataset run parameter ({0}) not found in output database"
            raise SimError(_RESULT_ERROR, msg, run)
        if batch is not None and batch >= 0:
            maxbatch = database.last_batch(runs[0])
            if batch > maxbatch:
                msg = "export_dataset batch parameter ({0}) not found in output database"
                raise SimError(_RESULT_ERROR, msg, batch)
            
        if batch is None:
            batch = database.last_batch(runs[0])
        
        # Get the dataset (we rely on get_dataset to raise if not found)  
        dataset = database.get_dataset(elementid, datasetname)
                    
        # Get the requested datasetvalue rows
        dsetvalues = SimDatasetValues(database, dataset, run, batch)
        
        # Create the directory as required
        if os.path.dirname(filename):
            os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(dsetvalues.header_row)
            writer.writerows(dsetvalues.rows)
             

def _value_to_string(value, numwidth, showunits=True):
    """
    Internal helper method used by SimulationResult. Formats and returns a
    passed value as a string. The value should be either a number or a
    SimTime instance.

    The passed numwidth argument specifies the total width of the formatted
    numeric value; for floats, the number of digits to the right of the
    decimal place is hardwired to two.

    If the passed showunits argument is True, room in the formatted result
    will be provided for a time units string; if the passed value is not a
    SimTime instance, that extra room will be a padded blank space so that the
    returned result string has the same length regardless of value type.
    """
    numvalue = value.value if isinstance(value, SimTime) else value
    unitsvalue = value.units_string() if isinstance(value, SimTime) else ''

    if type(numvalue) is int:
        formatspec = '{:{w}d}'
    else:
        formatspec = '{:{w}.2f}'

    if showunits:
        formatspec += ' {:7}'

    return formatspec.format(numvalue, unitsvalue, w=numwidth)

def _range_to_string(values, numwidth, showunits=True):
    """
    Internal helper method used by SimulationResult. Formats and returns a
    passed pair of values as a string of form '[x-y']. The values should be
    either snumbers or SimTime instances.

    The numwidth and showunits arguments are used similarly to above. If
    showunits is True and the values are SimTime instances, the output for pair
    (25 seconds, 38 seconds) will be '[25-38 seconds]'
    """
    assert len(values) == 2, "values passed to _rangeToString should be a pair"
    assert isinstance(values[0], SimTime) == isinstance(values[1], SimTime), "values passed to _rangeToString should either both be or neither be SimTimes"

    def numvalue(value):
        return value.value if isinstance(value, SimTime) else value

    def typefmt(numvalue):
        return 'd' if type(numvalue) is int else '.2f'

    numvalues = [numvalue(value) for value in values]
    typefmts = [typefmt(value) for value in values]

    if showunits and isinstance(values[0], SimTime):
        units = ' ' + values[0].units_string()
    else:
        units = ''

    formatspec = '[{:{tf0}}-{:{tf1}}{}'
    rangestr = formatspec.format(numvalues[0], numvalues[1], units+']',
                                 tf0=typefmts[0], tf1=typefmts[1])

    # Return a value padded to allow for the maximum numwidth
    totalwidth = numwidth * 2 + 3 + (8 if showunits else 0)
    return '{:{w}}'.format(rangestr, w=totalwidth)


class SimDatasetStatistics(object):
    """
    Class that collects batch sample summary statistics from a specified
    output database for a single specified dataset. The summary statistics
    collected are: count, mean, minimum, maximum, median, first quartile
    and third quartile.

    When the passed output database contains multiple runs, summary
    statistic values are collected for the last batch in each run.

    When the passed output database contains a single run with multiple
    batches, summary statistic values are collected for each batch in
    that run.
    
    Some notes on the classes involved here (which have similar names,
    which adds to the confusion):
    
    * :class:`SimDatasetStatistics` (this class): the top-level holder for all
      summary statistic values for a *single* dataset for all relevant batches
      and runs.
    * :class:`~simprovise.database.outputdb.SimDatasetSummaryData`: a class in
      database.outputdb that queries the output database for dataset values
      for a *single* run/batch and calculates *all* of the summary statistics 
      for that run/batch (min, max, median, mean and all 100 percentiles).
    * :class:`SimSample`: Holds the values for a *single* summary statistic
      (e.g. "median" or "75th percentile") for *all* queried batches/runs.
      These are the data used to construct point estimates for that summary
      statistic (either mean or median) and confidence intervals for that
      estimate.
      
    Be aware of the possible level of indirection with SimSamples - e.g.,
    if the output database includes data for 20 runs, the median of the
    SimSample for the 75th percentile sample statistic is the median of
    the set of 20 values, on per run, where each  value is the 75th
    percentile dataset value for that run.
    """
    def __init__(self, database, dataset):
        """
        """
        self.database = database
        self.dataset = dataset
        self.valuetype = dataset.valuetype
        self.timeunit = dataset.timeunit
       
        # Note on ci_type (Confidence Interval Type):
        # We are assuming here that the SimSample values are summary 
        # statistics calculated from data collected from independent 
        # replications or batches of a steady state simulation. As such, the
        # mean of the replication/batch values is a reasonable point estimate of 
        # the summary statistic, and we can use a T distribution for
        # calculating a confidence interval (Carson & Banks, 2001, p. 440)
        # If the order statistics are single values gathered directly from 
        # replications of a terminating simulation, the non-parametric
        # estimate of confidence intervals would be more appropriate (p. 416)
        self.counts = SimSample(dataset, ci_type=simstats.CIType.T)
        self.means = SimSample(dataset, ci_type=simstats.CIType.T)
        self.mins = SimSample(dataset, ci_type=simstats.CIType.T)
        self.maxs = SimSample(dataset, ci_type=simstats.CIType.T)
        self.medians = SimSample(dataset, ci_type=simstats.CIType.T)
        self.pct05s = SimSample(dataset, ci_type=simstats.CIType.T)
        self.pct10s = SimSample(dataset, ci_type=simstats.CIType.T)
        self.pct25s = SimSample(dataset, ci_type=simstats.CIType.T)
        self.pct75s = SimSample(dataset, ci_type=simstats.CIType.T)
        self.pct90s = SimSample(dataset, ci_type=simstats.CIType.T)
        self.pct95s = SimSample(dataset, ci_type=simstats.CIType.T)
        runs = database.runs()
        self.nruns = len(runs)

        # If there is just a single run and multiple batches, collect
        # summary statistics from each batch
        if self.nruns == 1:
            nbatches = database.last_batch(runs[0])
            batches = range(1, nbatches+1)
        else:
            batches = [None,]

        if dataset.name == 'Entries':
            # For Entries datasets, all values are  the count
            for run in runs:
                for batch in batches:
                    sdata = SimDatasetSummaryData(database, dataset, run, batch)
                    count = sdata.count
                    self.counts.append(count)
                    self.means.append(count)
                    self.mins.append(count)
                    self.maxs.append(count)
                    self.medians.append(count)
                    self.pct05s.append(count)
                    self.pct10s.append(count)
                    self.pct25s.append(count)
                    self.pct75s.append(count)
                    self.pct90s.append(count)
                    self.pct95s.append(count)
        else:
            #pctileData = SimPercentileData(database)
            for run in runs:
                for batch in batches:
                    #sdata = SimSummaryData(database, run,
                                           #dataset.element_id, batch)
                    #dsdata = sdata.get_raw_data(dataset)
                    sdata = SimDatasetSummaryData(database, dataset, run, batch)
                    self.counts.append(sdata.count)
                    self.means.append(sdata.mean)
                    self.mins.append(sdata.min)
                    self.maxs.append(sdata.max)
                    percentiles = sdata.percentiles
                    self.medians.append(percentiles[50])
                    self.pct05s.append(percentiles[5])
                    self.pct10s.append(percentiles[10])
                    self.pct25s.append(percentiles[25])
                    self.pct75s.append(percentiles[75])
                    self.pct90s.append(percentiles[90])
                    self.pct95s.append(percentiles[95])

    @property
    def nsamples(self):
        """
        The number of samples from which summary statistics were collected -
        generally the number of runs or batches, but could be less for a
        dataset with no values.
        """
        return self.counts.n


class SimSample(object):
    """
    Wraps a set of sample values, providing summary statistics for the sample:
    mean, median, sample std. deviation, interquartile range, and min/max range.

    SimSamples usually contain a set of summary statistic values for a single
    statistic over multiple batches or replications, allowing us, for example
    to estimate standard error of the mean (SimSample.mean for a SimSample
    containing mean values each of multiple replications.)
    
    If there are no values in the sample, the summary statistic properties
    return NaN (float('nan')). (Amongst other things, this ensures that
    the return value can be formatted by code above that expects a number.)
    """
    def __init__(self, dataset, *, ci_type=simstats.CIType.T,
                 quantile=0.5):
        """
        """
        self.dataset = dataset
        self.valuetype = dataset.valuetype
        self.timeunit = dataset.timeunit
        self.values = []
        
        # The confidence interval calculation type for this SimSample
        # Generally SimSamples for order statistics (min/max/median/percentile)
        # should use QUANTILE. Other summary statistics (mean, count) can
        # use T or NORMAL depending on sample size.
        self.ci_type = ci_type
        
        # The quantile when doing a non-parametric QUANTILE CI calculation
        self.quantile = quantile

    def append(self, value):
        """
        Add a raw (not SimTime) value to the sample (if the value is not None)
        """
        if value is not None:
            self.values.append((value))

    @property
    def n(self):
        """
        Return the size of the sample
        """
        return len(self.values)

    @property
    def mean(self):
        """
        Return the sample mean, converted to SimTime as required
        """
        if self.values:            
            return self._convertSimTime(np.mean(self.values))
        else:
            return _NAN

    @property
    def median(self):
        """
        Return the sample median, converted to SimTime as required
        """
        if self.values:           
            return self._convertSimTime(np.median(self.values))
        else:
            return _NAN

    @property
    def stdev(self):
        """
        Return the sample standard deviation, converted to SimTime as required.
        If n <= 1, returns NaN
        """
        if self.n > 1:
            return self._convertSimTime(np.std(self.values, ddof=1))
        else:
            return _NAN

    @property
    def stderr(self):
        """
        Return the sample standard error of the mean, converted to SimTime
        as required.
        If n <= 1, returns None
        """
        if self.n > 1:
            se = st.sem(self.values)
            return self._convertSimTime(se) 
        else:
            return _NAN

    @property
    def iqr(self):
        """
        Return the sample interquartile range, converted to SimTimes as
        required
        """
        if self.values:           
            return (self._convertSimTime(np.percentile(self.values, 25)),
                    self._convertSimTime(np.percentile(self.values, 75)))
        else:
            return (_NAN, _NAN)

    @property
    def minmaxrange(self):
        """
        Return the sample range (min, max), converted to SimTimes as required
        """
        if self.values:           
            return (self._convertSimTime(min(self.values)),
                    self._convertSimTime(max(self.values)))
        else:
            return (_NAN, _NAN)
        
    def confidence_interval(self, ci_type=None, *, confidence_level=0.95,
                            quantile=0.5):
        """
        Calculate a confidence interval for a passed confidence level using
        a specified confidence interval type/calculation (T, normal or
        non-parametric quantile). For a quantile confidence interval, the
        passed quantile is also used. 
        
        :param ci_type:          Confidence interval type - if None, use
                                 default_ci_type
        :type ci_type:           :class:`~simprovise.core.stats.CIType`
        
        :param confidence_level: Desired confidence level (e.g 95%) for if
                                 Defaults to 95% (0.95).
        :type confidence_level:  `float` in range (.0, 1.0)
        
        :param quantile:         Quantile to calculate interval for. Defaults to
                                 0.5 (median). Ignored when the ci_type is not
                                 QUANTILE.
        :type quantile:          `float` in range (.0, 1.0)
        
        :return:                 Low and high bound of confidence interval, or
                                 (nan, nan) if there are an insufficient number 
                                 of values, converted to
                                 :class:`~simprovise.core.simtime.SimTime` as
                                 required
        :rtype:                  `tuple` (numeric, numeric)
    
        :raises:                 :class:`~.simexception.SimError`
                                 Raised if ci_type is invalid.
                                 
        """
        if ci_type is None:
            ci_type = self.ci_type
            
        ci = simstats.confidence_interval(ci_type, self.values,
                                          confidence_level, quantile=quantile)
        return (self._convertSimTime(ci[0]), self._convertSimTime(ci[1]))
    
    @property
    def confidence_interval90(self):
        """
        Calculate and return a 90% confidence interval using the SimSample's
        confidence interval calculation type and quantile (if applicable)
        """
        return self.confidence_interval(self.ci_type, confidence_level=0.90,
                                        quantile=self.quantile)
    
    @property
    def confidence_interval95(self):
        """
        Calculate and return a 95% confidence interval using the SimSample's
        confidence interval calculation type and quantile (if applicable)
        """
        return self.confidence_interval(self.ci_type, confidence_level=0.95,
                                        quantile=self.quantile)
                   
    def __getitem__(self, i):
        """
        """
        return self.values[i]

    def _convertSimTime(self, value):
        if self.valuetype == 'SimTime' and value is not None and value is not _NAN:
            return SimTime(value, self.timeunit)
        else:
            return value


if __name__ == '__main__':
    warmupLength = SimTime(1000)
    batchLength = SimTime(10000)
    #batchLength = SimTime(0)
    scriptpath = "demos/mm_1.py"
    multi_replication = True
    nruns = 30
    
    thisdir = os.path.dirname(sys.argv[0])
    scriptpath = os.path.join(thisdir, scriptpath)
    print("scriptpath:", scriptpath)
    
    #SimLogging.set_level(logging.WARN)
    #SimLogging.set_level(logging.INFO, 'simprovise.core.process')
    
    if not multi_replication:
        print("Running a single replication...")
        with Simulation.execute_script(scriptpath, warmupLength, batchLength, 2) as simResult:
            simResult.print_summary(rangetype='total')
            simResult.export_dataset('Server', 'ProcessTime', filename='mm1.csv')
    else:   
        print("Running", nruns, "replications...")
        with Simulation.replicate(scriptpath, warmupLength, batchLength, 1,
                                  fromRun=1, toRun=nruns,
                                  outputpath=None, overwrite=False) as simResult:
            simResult.print_summary(rangetype='95ci')
                