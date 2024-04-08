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
#===============================================================================
import os, sys, shutil, types
import numpy as np

from simprovise.core import SimModel
from simprovise.runcontrol.replication import (SimReplication, SimReplicator)
from simprovise.runcontrol.simruncontrol import (SimReplicationParameters)
from simprovise.database import (SimDatabaseManager, SimSummaryData,
                                SimPercentileData)
from simprovise.core import SimError, SimLogging, SimTime
from simprovise.core.apidoc import apidoc, apidocskip

_ERROR_NAME = "Simulation Error"
_RESULT_ERROR = "Simulation Result Error"
_MIN_IQR_RUNS = 4
_DEFAULT_OUTPUTDB_EXT = ".simoutput"

logger = SimLogging.getLogger(__name__)

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
    methods return a :class:`SimResult` object.
    
    These methods all provide the option to save the resulting output
    database to a specified file location. The database may also be saved
    via the :class:`SimResult` object; the advantage of doing so via
    the execute() methods is that the designated output path will be
    validated prior to the simulation; when doing so via :class:`SimResult`
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

           with Simulation.execute(warmupLength, batchLength) as simResult:
               # Do something with the simulation result
               
        The output database resulting from the simulation run may optionally
        be saved to a specified filepath.
               
        :param warmupLength: The length of the simulation warmup period,
                             in simulated time. Defaults to zero
        :type warmupLength:  :class:`SimTime`
        
        :param batchLength:  The length of each simulation batch, in
                             simulated time. Raises if not set or not greater
                             than zero.
        :type batchLength:   :class:`SimTime`
        
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
        
        :raise SimError:     Raised if parameters are invalid or an error
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
            
        return SimulationResult(replication.dbPath, isTemporary=True)

    @staticmethod
    def execute_script(modelpath, warmupLength=None, batchLength=None,
                       nBatches=1, *, runNumber=1,
                       outputpath=None, overwrite=False):
        """
        Start a single in-process simulation run from a script other
        than the model script - in particular, the simprovise command line
        interface.

        :param modelpath:    The full path of the model script file.
                             in simulated time. Defaults to zero
        :type modelpath:     str
        
        :param warmupLength: The length of the simulation warmup period,
                             in simulated time. Defaults to zero
        :type warmupLength:  :class:`SimTime`
        
        :param batchLength:  The length of each simulation batch, in
                             simulated time. Raises if not set or not greater
                             than zero.
        :type batchLength:   :class:`SimTime`
        
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
        
        :raise SimError:     Raised if parameters are invalid or an error
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
        
        return SimulationResult(replication.dbPath, isTemporary=True)

    @staticmethod
    def replicate(modelpath, warmupLength=None, batchLength=None, nBatches=1,
                  *, fromRun=1, toRun=8, outputpath=None, overwrite=False):
        """
        Start one or more simulation replications (with different random
        number streams), each in their own process. Replications can run in
        parallel, depending on system configuration.
        
        Can be invoked from any script, as well as the simprovise command line
        interface.
        
        :param modelpath:    The full path of the model script file.
        :type modelpath:     str
        
        :param warmupLength: The length of the simulation warmup period,
                             in simulated time. Defaults to zero
        :type warmupLength:  :class:`SimTime`
        
        :param batchLength:  The length of each simulation batch, in
                             simulated time. Raises if not set or not greater
                             than zero.
        :type batchLength:   :class:`SimTime`
        
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
        
        :raise SimError:     Raised if parameters are invalid or an error
                             occurs during the simulation.
        
        :return:             Result object wrapping simulation output database
        :rtype:              :class:`SimulationResult`
        
        """
        # get an absolute path after validating - will raise if invalid
        outputpath = Simulation._valid_outputpath(outputpath, overwrite)
        
        model = SimModel.load_model_from_script(modelpath)

        replicator = SimReplicator(model, warmupLength, batchLength, nBatches)
        replicationParameters = SimReplicationParameters()
        replicationParameters.set_replication_range(fromRun, toRun)
        replicator.execute_replications(replicationParameters, asynch=False)
        if outputpath:
            Simulation._save_output(replicator.output_dbpath, outputpath)
        return SimulationResult(replicator.output_dbpath, isTemporary=True)

    @staticmethod
    def _valid_outputpath(outputpath, overwrite):
        """
        Validates passed output database path. If path does not include a
        file extension, it will add the default output database extension.
        Returns the (possibly refornatted) absolute path with extension.
        
        Raises a SimError if:
        - overwrite is True and no output path is specified
        - the path exists and overwrite is not specified as True
        - the path is an existing directory (which presumably also means
          that no extension was provided)
        - the path includes a non-existing directory
        """
        if not isinstance(outputpath, (types.NoneType, str)):
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
    def _save_output(dbpath, outputhpath):
        """
        Copies dbpath to outputpath, catching and re-raising any exceptions
        """
        try:        
            shutil.copy(dbpath, outputhpath)
            print("copy of output database saved to:", outputhpath)
        except Exception as e:
            msg = "Failure saving output database: failure copying {0} to {1}: {2}"
            raise SimError(_ERROR_NAME, msg, dbpath, outputhpath, e)
            


@apidoc
class SimulationResult(object):
    """
    SimulationResult wraps the output (database) of a simulation , and
    implements various operations (reports, database save, csv file
    generation) on that output. The wrapped output database is temporary
    by default.
    
    :meth:`Simulation.execute`, :meth:`Simulation.executeScript` and
    :meth:`Simulation.replicate` all return SimulationResult objects.
    Client code may also generate reports and/or csv files from  saved output
    databases by creating a SimulationResult.

    SimulationResult instances are context managers that close the database
    on exit. If the database is temporary, the database is therefore deleted
    on exit unless explicitly saved.
    """
    
    def __init__(self, dbpath, isTemporary=False):
        """
        Open the database (specified by dbpath) via SimDatabaseManager.
        If a model is specified, we assume the database is temporary; if no
        model is specified, the database was presumably saved previously and
        is opened as an archive.

        TODO look at gathering data (SimDatasetStatistic objects) in initializer,
        to be available to reporting/output methods.
        """
        logger.info("Simulation result created for output db {0} {1}", dbpath, isTemporary)
        print("==========", dbpath, isTemporary)
        self.dbMgr = SimDatabaseManager()
        self.dbMgr.openArchivedDatabase(dbpath, isTemporary)
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
        if self.dbMgr.hasOpenDatabase():
            if self.dbMgr.database.isTemporary:
                print("Closing and removing output database...")
                self.dbMgr.closeOutputDatabase(delete=True)
            else:
                print("Closing output database", self.dbMgr.database.dbPath, "...")
                self.dbMgr.closeOutputDatabase()

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
        Save the temporary output database to a caller-specified location -
        otherwise, the database is deleted on exit.

        :param filename: The path/filename to which the output database is
                         saved. Extension would typically be '.simoutput', but
                         this is neither checked nor required.
        :type filename:  str

        """
        # TODO better error checking in closeOutputDatabase, overwrite checking?
        assert self.dbMgr.hasOpenDatabase(), "Cannot save non-open database"
        assert self.dbMgr.database.isTemporary, "Cannot save non-temporary (archive) database"

        print("Closing and saving output database to {0}...".format(filename))
        self.dbMgr.closeOutputDatabase(savePath=filename)

    def save_summary_csv(self, filename):
        """
        Save summary statistics for each dataset/run/batch as a comma-separated-
        values (csv) file.

        Args:
            filename (str): Absolute path to which csv file is saved. Extension
                            would typically be '.csv', but this is not checked.
        """
        unitName = ('seconds', 'minutes', 'hours')
        def unitstr(dataset):
            if dataset.valuetype == 'SimTime':
                return unitName[dataset.timeunit]
            else:
                return ''

        database = self.dbMgr.database
        assert database, "SimResult database not open"
        runs = database.runs()
        if not runs:
            raise SimError(_RESULT_ERROR, "Result database has no simulation runs")
        nbatches = database.lastBatch(runs[0])

        with open(filename, 'w') as f:
            print('ElementID', 'Dataset', 'Unit', 'Sample', 'Count', 'Mean',
                  'Min', 'Max', '5th Percentile', '10th Percentile',
                  '25th Percentile', 'Median', '75th Percentile',
                  '90th Percentile', '95th Percentile',
                  sep=',', file=f)
            datasets = database.datasets
            for dset in datasets:
                dsetstats = self._get_sim_dataset_statistics(dset)
                for i in range(dsetstats.nsamples):
                    print(dset.element_id, dset.name, unitstr(dset),
                          i+1, ' ', sep=',', end='', file=f)
                    print(dsetstats.counts[i], ',', end='', file=f)
                    print(dsetstats.means[i], ',', end='', file=f)
                    print(dsetstats.mins[i], ',', end='', file=f)
                    print(dsetstats.maxs[i], ',', end='', file=f)
                    print(dsetstats.pct05s[i], ',', end='', file=f)
                    print(dsetstats.pct10s[i], ',', end='', file=f)
                    print(dsetstats.pct25s[i], ',', end='', file=f)
                    print(dsetstats.medians[i], ',', end='', file=f)
                    print(dsetstats.pct75s[i], ',', end='', file=f)
                    print(dsetstats.pct90s[i], ',', end='', file=f)
                    print(dsetstats.pct95s[i], file=f)

    def print_summary(self, rangetype=None):
        """
        Print formatted summary statistics for the simulation output. In the
        base report, summary statistics for multiple runs/batches are shown as
        the mean of the statistic values calculated for each run/batch in
        the result database. (If the database has multiple runs, it is the
        average of the calculated result for each run; if it is a single run
        with multiple batches, it is the average of the calculated result for
        each batch.)

        If the rangetype argument is specified, a spread indicator is also
        shown for each summary statistic; the indicators supported are
        'iqr' (Interquartile range) and 'total' (minimum and maximum). These
        spread range indicators refer to the calculated statistic, NOT the
        underlying dataset values. For example, if rangetype is 'total' and
        the database has 10 replication runs, then the "Median" column for a
        dataset wll display the mean of the calculated medians for each of
        those ten replications, plus a range [min-max] that indicate the lowest
        and highest of those ten calculated medians.

        Args:
            rangetype (str): 'iqr', 'total' or None. A SimError is raised
                             for any other value.
        """
        database = self.dbMgr.database
        assert database, "SimResult database not open"
        datasets = database.datasets

        runs = database.runs()
        nruns = len(runs)
        if not runs:
            raise SimError(_RESULT_ERROR, "Result database has no simulation runs")
        nbatches = database.lastBatch(runs[0])

        if nruns == 1 and nbatches == 1:
            # If there's only one run and one batch, there's no range to get
            rangetype = None

        if rangetype is None:
            rangeprop = None
            rangelabel = ''
        elif rangetype.lower() == 'iqr':
            rangeprop = SimSample.iqr
            rangelabel = '   IQR'
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
            header1fmt = '{:{ew}} {:{nw}} {:^{cw}} {:^{cw}} {:^{cw}} {:^{cw}} {:^{cw}}'
            header1 = header1fmt.format('Element ID', 'Dataset', 'Sample Mean',
                                        '25th Percentile', 'Median',
                                        '75th Percentile', 'Max',
                                        ew=eidwidth, nw=namewidth, cw=colwidth)
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
                      _value_to_string(dsetstats.means.stdev, numwidth, False),
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
                print(_value_to_string(dsetstats.means.mean, numwidth),
                      _value_to_string(dsetstats.pct25s.mean, numwidth),
                      _value_to_string(dsetstats.medians.mean, numwidth),
                      _value_to_string(dsetstats.pct75s.mean, numwidth),
                      _value_to_string(dsetstats.maxs.mean, numwidth)
                     )

    def _getFormatWidths(self):
        """
        """
        datasets = self.dbMgr.currentDatasets()
        eidwidth = max([len(dset.element_id) for dset in datasets])
        namewidth = max([len(dset.name) for dset in datasets])
        numberwidth = 9
        numcolwidth = numberwidth + 8 # add 8 for time unit string

        return eidwidth, namewidth, numberwidth, numcolwidth

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
    unitsvalue = value.unitsString() if isinstance(value, SimTime) else ''

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
        units = ' ' + values[0].unitsString()
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
    """
    def __init__(self, database, dataset):
        """
        """
        self.database = database
        self.dataset = dataset
        self.valuetype = dataset.valuetype
        self.timeunit = dataset.timeunit

        self.counts = SimSample(dataset)
        self.means = SimSample(dataset)
        self.mins = SimSample(dataset)
        self.maxs = SimSample(dataset)
        self.medians = SimSample(dataset)
        self.pct05s = SimSample(dataset)
        self.pct10s = SimSample(dataset)
        self.pct25s = SimSample(dataset)
        self.pct75s = SimSample(dataset)
        self.pct90s = SimSample(dataset)
        self.pct95s = SimSample(dataset)
        runs = database.runs()
        self.nruns = len(runs)

        # If there is just a single run and multiple batches, collect
        # summary statistics from each batch
        if self.nruns == 1:
            nbatches = database.lastBatch(runs[0])
            batches = range(1, nbatches+1)
        else:
            batches = [None,]

        if dataset.name == 'Entries':
            # For Entries datasets, all values are  the count
            for run in runs:
                for batch in batches:
                    sdata = SimSummaryData(database, run,
                                           dataset.element_id, batch)
                    dsdata = sdata.getRawData(dataset)
                    count = dsdata.count
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
            pctileData = SimPercentileData(database)
            for run in runs:
                for batch in batches:
                    sdata = SimSummaryData(database, run,
                                           dataset.element_id, batch)
                    dsdata = sdata.getRawData(dataset)
                    self.counts.append(dsdata.count)
                    self.means.append(dsdata.mean)
                    self.mins.append(dsdata.min)
                    self.maxs.append(dsdata.max)
                    percentiles = pctileData.getPercentiles(dataset, run, batch)
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
    """
    def __init__(self, dataset):
        """
        """
        self.dataset = dataset
        self.valuetype = dataset.valuetype
        self.timeunit = dataset.timeunit
        self.values = []

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
        return self._convertSimTime(np.mean(self.values))

    @property
    def median(self):
        """
        Return the sample median, converted to SimTime as required
        """
        return self._convertSimTime(np.median(self.values))

    @property
    def stdev(self):
        """
        Return the sample standard deviation, converted to SimTime as required.
        If n <= 1, returns None
        """
        if self.n > 1:
            return self._convertSimTime(np.std(self.values, ddof=1))
        else:
            return None

    @property
    def iqr(self):
        """
        Return the sample interquartile range, converted to SimTimes as
        required
        """
        return (self._convertSimTime(np.percentile(self.values, 25)),
                self._convertSimTime(np.percentile(self.values, 75)))

    @property
    def minmaxrange(self):
        """
        Return the sample range (min, max), converted to SimTimes as required
        """
        return (self._convertSimTime(min(self.values)),
                self._convertSimTime(max(self.values)))

    def __getitem__(self, i):
        """
        """
        return self.values[i]

    def _convertSimTime(self, value):
        if self.valuetype == 'SimTime' and value is not None:
            return SimTime(value, self.timeunit)
        else:
            return value


if __name__ == '__main__':
    import logging
    
    warmupLength = SimTime(500)
    batchLength = SimTime(1000)
    #batchLength = SimTime(0)
    scriptpath = "models\\mm1.py"
    multi_replication = True
    
    SimLogging.setLevel(logging.WARN)
    SimLogging.setLevel(logging.INFO, 'simprovise.core.process')
    
    if not multi_replication:
        print("Running a single replication...")
        with Simulation.execute_script(scriptpath, warmupLength, batchLength, 10) as simResult:
            simResult.print_summary(rangetype='total')
    else:   
        print("Running 10 replications...")
        with Simulation.replicate(scriptpath, warmupLength, batchLength, 1,
                                  fromRun=1, toRun=10,
                                  outputpath=None, overwrite=False) as simResult:
            simResult.print_summary(rangetype='iqr')
                