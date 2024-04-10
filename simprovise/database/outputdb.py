#===============================================================================
# MODULE outputdb
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines output database-related classes:
# - SimOutputDatabase, with subclasses SimLiveOutputDatabase and
#   SimArchivedOutputDatabase
# - SimDatabaseManager
# - SimDbDatasink and subclass SimDbTimeSeriesDatasink
# - Classes that query/process an output database in order to generate
#   data for output displays (charts and tables)
#===============================================================================
___all__ = ['SimDatabaseManager', 'SimArchivedOutputDatabase', 'SimSummaryData', 
           'SimTimeSeriesData', 'SimOutputHistogramData', 'SimPercentileData']

import sqlite3
import os
from collections import namedtuple
import tempfile

from simprovise.core import (SimResource, SimLocation, SimEntitySource, SimEntitySink,
                            SimTime, SimClock, simtime, SimError, SimLogging,
                            simelement)

from simprovise.core.process import SimProcessElement
from simprovise.core.entity import SimEntityElement

_ELEMENT_TYPE_CLASSES = (SimProcessElement, SimResource, SimLocation, SimEntitySource,
                         SimEntitySink, SimEntityElement)
#_PROCESS_ELEMENT_TYPE = 1
#_ENTITY_ELEMENT_TYPE = 6

logger = SimLogging.get_logger(__name__)

_ERROR_NAME = "Sim Output Database Error"
_ENTRIES_DATASET_NAME = simelement.ENTRIES_DATASET_NAME

class SimElementTypeXXX(object):
    """
    Essentially an enumeration of element types, with the types corresponding
    to the values in the elementtype table.
    """
    process = 1
    resource = 2
    location = 3
    source = 4
    sink = 5
    counter = 6
    entity = 7


class SimDbDatasink(object):
    """
    An implementation of the datasink interface implicitly defined by
    Core/NullDataSink that writes non-time-weighted dataset values to the
    SQLite output database implemented by this module.  Defines a number of
    additional methods (on top of those defined by NullDataSink) that are
    specific to the SQLite implementation.

    TODO Perhaps also take the dataset as a parameter, which would facilitate
    summary datasinks (that record summary statistics only by grabbing
    min/max/mean from the datacollector) The problem with that approach is
    that it more or less requires the data collector to be reset for each
    interval, which may not be desirable. The alternative is for summary
    sinks to create their own collectors.
    """
    __slots__ = ('__dbConnection', '__datasetID', '__run', '__batch', '__valuesAreSimTime')
    commitRate = 1

    @staticmethod
    def set_commit_rate(rate):
        """
        Static method to globally set the commitRate for all SimDbSinks.  When 1,
        maybeCommit() always does a commit.  When zero, maybeCommit() never commits
        (i.e., we rely on flush() to flush the database)
        Generally the rate is left at 1 for animated runs, zero for background runs.
        TODO allow other positive rates, to do periodic (but not every put) commits.
        TODO A more robust implementation might tie the rate to the database/db manager,
        (rather than a global setting) but that would require a bit of refactoring.
        """
        SimDbDatasink.commitRate = rate

    def __init__(self, database, dataset, runNumber):
        """
        Initialize a new instance for a specified output database, dataset and
        simulation run.
        """
        self.__dbConnection = database.connection
        self.__datasetID = database.getDatasetID(dataset)
        self.__run = runNumber
        self.__batch = None
        self.__valuesAreSimTime = (dataset.valuetype is SimTime)

    @property
    def db_connection(self):
        return self.__dbConnection

    @property
    def db_cursor(self):
        return self.__dbConnection.cursor()

    @property
    def dataset_id(self):
        return self.__datasetID

    @property
    def run(self):
        return self.__run

    @property
    def batch(self):
        return self.__batch

    def initialize_batch(self, batchnum):
        """
        Initialize a new batch.
        """
        self.__batch = batchnum

    def finalize_batch(self, batchnum):
        """
        Finalize the current batch by flushing the dataset. For time series
        data, flush() will also update the last row for the batch to set the
        totimestamp to the end of the batch.
        """
        if batchnum != self.batch:
            raise SimError(_ERROR_NAME,
                           "finalizeBatch({0}) called when current batch is {1}",
                           batchnum, self.batch)
        self.flush()

    def maybe_commit(self):
        """
        If the class variable commitRate is set, commit put() values to disk.
        """
        if SimDbDatasink.commitRate:
            self.db_connection.commit()

    def put(self, value):
        """
        Insert a new dataset value into the output database (and perhaps
        committing that insertion to disk)
        """
        rowVals = (self.dataset_id, self.run, self.batch, SimClock.now().seconds(), self._to_scalar(value))
        self.db_cursor.execute('insert into datasetvalue (dataset, run, batch, simtimestamp, value) values (?, ?, ?, ?, ?)',
                              rowVals)
        self.maybe_commit()

    def _to_scalar(self, value):
        """
        If the dataset values are SimTime values, return the passed value in
        seconds. Otherwise, just return the value.

        TODO We may eventually choose the default unit to be configurable, on
        either a per-model or per-dataset basis, at which point this method
        should probably return the time in default units.
        """
        return value if not self.__valuesAreSimTime else value.seconds()

    def flush(self):
        """
        Commit any unsaved additions/changes to disk
        """
        self.db_connection.commit()


class SimDbTimeSeriesDatasink(SimDbDatasink):
    """
    A datasink implementation for time-weighted datasets, derived from
    SimDbDatasink.
    """
    __slots__ = ('__lastrowid', '__lastTimestamp', '__lastValue')
    def __init__(self, database, dataset, runNumber, initialValue=0):
        """
        Initialize a new instance for a specified output database, dataset,
        simulation run and initial dataset value.  (Since this is for a
        time-weighted dataset, there must always be a current value)
        """
        super().__init__(database, dataset, runNumber)
        self.__lastrowid = None
        self.__lastTimestamp = None
        self.__lastValue = initialValue
        #self.put(initialValue, batch)

    def initialize_batch(self, batchnum):
        """
        Initialize a new batch. For time series data, insert the current
        value (self.__lastvalue) so that we have a row timestamped for the
        beginning of the batch.
        """
        super().initialize_batch(batchnum)
        tm = self._scalar_sim_now()
        self._insert_row(self.__lastValue, tm)
        self.db_connection.commit()
        self.__lastTimestamp = tm

    def _scalar_sim_now(self):
        """
        Return a scalar time value for the current simulated time
        (SimClock.now()) based on the dataset time unit.

        TODO Currently works only if that timeunit is seconds
        """
        return SimClock.now().seconds()

    def _update_last_to_time(self, toTime):
        """
        Update/set the totimestamp column value of the most recently inserted row
        """
        if self.__lastrowid is not None:
            sqlstr = "update datasetvalue set totimestamp = ? where rowid = ?"
            self.db_cursor.execute(sqlstr, (toTime, self.__lastrowid))

    def _insert_row(self, value, tm):
        """
        Insert a new row into dataset value (without a totimestamp) and save
        the rowid of that row as __lastrowid
        """
        insertStmt = 'insert into datasetvalue (dataset, run, batch, simtimestamp, value) values (?, ?, ?, ?, ?)'
        rowVals = (self.dataset_id, self.run, self.batch, tm, value)
        cursor = self.db_cursor
        cursor.execute(insertStmt, rowVals)
        self.__lastrowid = cursor.lastrowid

    def put(self, value):
        """
        Insert a new dataset value into the output database (and perhaps
        committing that insertion to disk)
        """
        value = self._to_scalar(value)
        if value == self.__lastValue:
            return

        tm = self._scalar_sim_now()
        cursor = self.db_cursor

        if tm == self.__lastTimestamp and self.__lastrowid is not None:
            sqlstr = "update datasetvalue set value = ? where rowid = ?"
            cursor.execute(sqlstr, (value, self.__lastrowid))
        else:
            self._update_last_to_time(tm)
            self._insert_row(value, tm)

        self.maybe_commit()

        self.__lastValue = value
        self.__lastTimestamp = tm

    def flush(self):
        """
        Commit any unsaved additions/changes to disk
        """
        tm = self._scalar_sim_now()
        self._update_last_to_time(tm)
        self.db_connection.commit()

class SimDatabaseManager(object):
    """
    SimDatabaseManager provides functionality for creating, closing, saving
    and accessing simulation output databases, while hiding the database
    implementation.
    """
    def __init__(self):
        self.database = None

    def create_output_database(self, model, inMemory=False):
        """
        Creates a new "live" output database - a database for a simulation
        that is being (or is about to be) executed - and initializes it based
        on information obtained from the passed model object. If inMemory is
        True, that new database is an in-memory SQLite database.

        If an output database is already open, that database is closed first.
        Relies on called methods to raise a SimError if they fail.
        """
        self.close_output_database()
        self.database = SimLiveOutputDatabase()
        self.database.initialize(model, inMemory)
 
    def open_existing_database(self, model, dbpath, *, isTemporary=False):
        """
        Open an existing live output database, typically when we are about to
        start an additional run/replication. Close the currently open database
        first, if any. Either operation may raise a SimError on failure.
        """
        self.close_output_database()
        self.database = SimLiveOutputDatabase()
        self.database.initialize_existing(model, dbpath, isTemporary)

    def initialize_run(self, runNumber):
        """
        Initialize the database in preparation for a run, typically by removing
        any dataset values for the specified run number.
        """
        if self.database:
            self.database.initialize_run(runNumber)
        else:
            raise SimError(_ERROR_NAME, "initializeRun() failure. There is no open database")

    def set_commit_rate(self, commitRate):
        """
        Sets the global rate for database commits.  If zero, commits only occur at the
        end of batches.  If one, commits occur on every database update.  Generally we
        use zero for background runs (replications), and one for interactive (animated)
        runs.
        """
        SimDbDatasink.set_commit_rate(commitRate)

    def open_archived_database(self, dbpath, isTemporary=False):
        """
        Open an archived database - a database saved by the user after one or
        more simulation runs. Close an open database first. Either operation
        may raise a SimError on failure.
        """
        self.close_output_database()
        self.database = SimArchivedOutputDatabase(dbpath, isTemporary)

    def has_open_database(self):
        """
        Returns True if the manager has a currently-open database, False otherwise
        """
        return self.database is not None

    @property
    def current_database_path(self):
        """
        The dbPath of the currently open database, or None if no database is open
        """
        if self.database:
            return self.database.db_path
        else:
            return None

    def current_datasets(self):
        """
        Returns all datasets for the current model/database (if a database is open)
        Raises an error if no database is currently open.
        """
        self._raise_if_database_not_open()
        return self.database.datasets

    def flush_datasets(self):
        """
        Flushes all datasets if a database is open; a no-op otherwise.
        """
        if self.database:
            self.database.flush_datasets()

    def has_unsaved_database(self):
        """
        Returns True if there is an open, temporary (or in-memory) database
        with dataset values (in other words, a simulation run is in progress)
        """
        return self.database and self.database.is_temporary and self.database.has_dataset_values()

    def default_savepath(self):
        """
        Returns a default save path if the currently open database is temporary.
        Returns None if no database is open or the open database is not
        temporary.
        """
        if self.database and self.database.is_temporary:
            return self.database.default_dbpath
        else:
            return None

    def close_output_database(self, *, savePath=None, delete=True):
        """
        Initiate a close for the currently-open database, if there is one.
        If the database is temporary, provides the ability to save the
        closed database to a specified path.
        
        For temporary database files, the logic is a bit circuitous:
        
        - If a savePath is specified, the temporary database is renamed
          to savePath regardless of whether or not delete is True
          
        - If there is no savePath, the temporary database is deleted
          only if the delete parameter is true. This provides the means
          for the SimReplicator to hold onto a temporary database for
          awhile longer.
          
        This implies some rules on the legal savePath and delete parameter
        values:
        
        - savePath can only be specified if the database is temporary
        - delete can only be set True if the database is temporary
        
        Raises a SimError if any of these database operations
        (close/rename/remove) fail.
        """
        if not self.database:
            return 

        dbPath = self.database.db_path
        isTemporary = self.database.is_temporary
        assert not (delete and not isTemporary), "closeOutputDatabase() called with delete=True on a not-temporary database"
        assert not savePath or isTemporary, "closeOutputDatabase() attempt to save a non-temporary database"

        self.database.close_database()
        
        if isTemporary:
            if savePath:
                try:
                    # os.replace() will overwrite an existing file - os.rename() will not
                    os.replace(dbPath, savePath)
                except OSError as e:
                    logger.exception("Failure saving temporary database %s to: %s: %s",
                                     dbPath, savePath, e)
                    raise SimError(_ERROR_NAME, "Failure saving output database to {0}", savePath)                   
            elif delete:
                try:
                    os.remove(dbPath)
                except (OSError, FileNotFoundError) as e:
                    logger.exception("Failure deleting temporary database %s: %s", dbPath, e)
                    raise SimError(_ERROR_NAME, "Failure saving output database to {0}: {1}",
                                   savePath, e)                   
                    
        self.database = None

    def _raise_if_database_not_open(self):
        """
        Utility method that raises a SimError if the manager does not have a
        currently-open database.
        """
        if not self.database:
            msg = "No output database is currently open."
            raise SimError(_ERROR_NAME, msg)

# DbElement is constructed from the element and elementtype tables
DbElement = namedtuple('DbElement',
                       ['element_id', 'className', 'elementType', 'elementTypeName'])


# DbDataset is constructed from the dataset and element tables in an output database.
# It has all of the (read) properties provided by the Core package Dataset class (Model
# element dataset objects are instances of that Core Dataset class.)
DbDataset = namedtuple('DbDataset',
                       ['element_id', 'name', 'valuetype', 'istimeweighted',
                        'timeunit', 'elementType'])

class SimOutputDatabase(object):
    """
    Base class for an object that encapsulates a simulation output database
    implemented via the sqlite3 module. There are two concrete subclasses:

    SimLiveOutputDatabase creates a new database, populates its static data
    (simulation elements and dataset definitions) and wires the model object
    dataset objects to this database in order to capture output data during
    the simulation run.

    SimArchivedOutputDatabase provides access to a database populated during
    a previous simulation run. It is intended to be read-only.
    """
    def __init__(self):
        self.__connection = None
        self.__dbpath = None
        self.__isTemporary = False

    @property
    def connection(self):
        """
        The currently open database connection (or None, if not open)
        """
        return self.__connection

    @property
    def db_path(self):
        """
        The database filepath that is/was open
        """
        return self.__dbpath

    @property
    def is_temporary(self):
        """
        Returns True if there is a connected database and it is a temporary
        (or in-memory) file.
        """
        if self.__dbpath:
            return self.__isTemporary

    def flush_datasets(self):
        """
        Default is a no-op - implemented for live output databases
        """
        pass

    def runs(self):
        """
        Returns a sequence of run numbers present in the database
        """
        result = self.runQuery("select distinct(run) from datasetvalue order by run")
        return [r[0] for r in result]

    @property
    def elements(self):
        """
        Returns a DbElement for each element row in the database.
        TODO We may want to cache this if performance becomes an issue.
        """
        sqlstr = """
                  select element.id, element.classname, element.type, elementtype.name from element
                  inner join elementtype on element.type = elementtype.id
                 """

        def elementTupleFactory(cursor, row): # pylint: disable=unused-argument
            return DbElement(*row)

        savedRowFactory = self.connection.row_factory
        try:
            self.connection.row_factory = elementTupleFactory
            result = self.runQuery(sqlstr)
            return result
        finally:
            self.connection.row_factory = savedRowFactory

    @property
    def datasets(self):
        """
        Returns a DbDataset for each dataset row in the database.
        TODO We may want to cache this if performance becomes an issue.
        """
        sqlstr = """
                  select element.id, dataset.name, dataset.valueType,
                  dataset.istimeweighted, dataset.timeunit, elementtype.name
                  from dataset
                  inner join element on dataset.element = element.id
                  inner join elementtype on element.type = elementtype.id
        """

        def datasetTupleFactory(cursor, row): # pylint: disable=unused-argument
            return DbDataset(*row)

        savedRowFactory = self.connection.row_factory
        try:
            self.connection.row_factory = datasetTupleFactory
            result = self.runQuery(sqlstr)
            return result
        finally:
            self.connection.row_factory = savedRowFactory

    def get_datasets(self, element_id):
        """
        Returns all datasets in the database belonging to a single element
        (as specified by element_id)
        """
        sqlstr = """
                  select element.id, dataset.name, dataset.valueType,
                  dataset.istimeweighted, dataset.timeunit, elementtype.name
                  from dataset
                  inner join element on dataset.element = element.id
                  inner join elementtype on element.type = elementtype.id
                  where dataset.element = ?
        """

        def datasetTupleFactory(cursor, row): # pylint: disable=unused-argument
            return DbDataset(*row)

        savedRowFactory = self.connection.row_factory
        try:
            self.connection.row_factory = datasetTupleFactory
            result = self.runQuery(sqlstr, element_id)
            return result
        finally:
            self.connection.row_factory = savedRowFactory

    def last_batch(self, run):
        """
        Returns the last (highest) batch number for a specified run, or zero if
        there are none.
        """
        sqlstr = "select max(batch) from datasetvalue where run = ?"
        result = self.runQuery(sqlstr, run)

        # Since the query includes an aggregate, it will return a row - even if the from table
        # (datasetvalue) is empty.  If datasetvalue is empty, the resulting value will be None.
        if len(result) == 1:
            n = result[0][0]
            return 0 if n is None else n
        else:
            raise SimError(_ERROR_NAME, "lastBatch() query returned {0} row(s)".format(len(result)))

    def batch_time_bounds(self, run, batch):
        """
        Returns the current unitless (time) bounds for a specified run and batch,
        as specified by the lowest simtimestamp and highest totimestamp for that
        run/batch. Returns zero (or zeros) in case where there is not yet data for
        the specified batch.

        Note that this depends on there being at least one time-weighted dataset
        in the model, since totimestamps are only written (at batch boundaries) for
        time-weighted datasets. We check for this first.
        TODO - implement version that does not require a timeweighted dataset.
        """
        if not self.has_time_weighted_dataset():
            msg = "batchTimeBounds() requires at least one time-weighted dataset. There are none."
            raise SimError(_ERROR_NAME, msg)

        sqlstr = "select min(simtimestamp), max(totimestamp) from datasetvalue where run = ? and batch = ?"
        result = self.runQuery(sqlstr, run, batch)
        if len(result) == 1:
            row = result[0]
            low = 0 if row[0] is None else row[0]
            high = 0 if row[1] is None else row[1]
            return low, high
        else:
            raise SimError(_ERROR_NAME,
                           "batchTimeBounds() query returned {0} row(s)".format(len(result)))

    def has_time_weighted_dataset(self):
        """
        Returns true if the database has had at least one time-weighted dataset.
        """
        sqlstr = "select rowid from dataset where istimeweighted = 1 limit 1;"
        result = self.runQuery(sqlstr)
        return len(result) > 0

    def initialize_run(self, runNumber):
        """
        Implemented only for Live output databases
        """
        pass

    def has_dataset_values(self):
        """
        Returns true if the database has had at least one dataset value inserted.
        """
        sqlstr = "select rowid from datasetvalue limit 1;"
        result = self.runQuery(sqlstr)
        return len(result) > 0


    def close_database(self):
        """
        Close the database (if open) and set the connection to None. Raises
        a SimError if the sqlite3 close() operation fails.
        """
        if self.__connection is not None:
            try:              
                self.__connection.close()
            except sqlite3.Error as e:
                logger.exception("Failure closing database %s: %s", self.__dbpath, e)
                raise SimError(_ERROR_NAME, "Failure closing database {0}: {1}",
                               self.__dbpath, e)                                  
            self.__connection = None

    def get_element_type(self, elementID):
        """
        Return the element type ID of an element (as specified by element ID)
        """
        sqlstr = """
                 select elementtype.id from element
                 INNER JOIN elementtype ON element.type = elementtype.id
                 where element.id = ?
                 """
        result = self.runQueryForSingleRow(sqlstr, elementID)
        return result[0]

    def getDataset(self, elementID, datasetName):
        """
        Return the dataset for a specified elementID and dataset name.
        Raises an error if not found.
        """
        for dset in self.datasets:
            if dset.element_id == elementID and dset.name == datasetName:
                return dset
        raise SimError(_ERROR_NAME, "Dataset ({0}, {1}) not found",
                       elementID, datasetName)

    def getDatasetID(self, dataset):
        """
        Get the ID number of a dataset.
        Note that this ID may change from one database to another - even if
        both databases are created for the same model.
        """
        queryStr = 'select id from dataset where element = ? and name = ?'
        result = self.runQuery(queryStr, dataset.element_id, dataset.name)

        if len(result) == 1:
            return result[0][0]
        else:
            errstr = "Element {0}, Dataset: {1}".format(dataset.element_id,
                                                        dataset.name)
            if len(result) == 0:
                raise SimError("Output Database getDatasetID() Error: Dataset Not Found", errstr)
            else:
                raise SimError("Output Database getDatasetID() Error: Multiple Datasets Found", errstr)

    def getDatasetNames(self, elementID):
        """
        Retrieve names of all datasets for a specified element.
        """
        queryStr = 'select name from dataset where element = ?'
        results = self.runQuery(queryStr, elementID)
        names = [result[0] for result in results]
        if len(names) == 0:
            raise SimError(_ERROR_NAME, "getDatasetNames(): Element ID {0} not found or has no datasets", elementID)
        return names

    def _connect(self, dbpath, isTemporary):
        """
        Internal method - connects to a database on the specified path
        """
        self.__dbpath = dbpath
        self.__connection = sqlite3.connect(dbpath)
        self.__isTemporary = isTemporary

    def _runScript(self, scriptName, scriptDir=None):
        """
        Internal method that executes an SQL script on the open database.
        """
        if scriptDir is None:
            scriptDir = os.path.dirname(__file__)
        path = os.path.join(scriptDir, scriptName)
        with open(path) as scriptFile:
            script = scriptFile.read()
            cur = self.__connection.cursor()
            cur.executescript(script)

    def runQuery(self, sqlstr, *args):
        """
        Runs a query (as specified by a pass SQL string) on the current database.
        """
        try:
            cursor = self.__connection.cursor()
            cursor.execute(sqlstr, args)
            return cursor.fetchall()
        except Exception as e:
            raise SimError(_ERROR_NAME,
                           "Failure executing query: {0}; parameters: {1}; {2}",
                           sqlstr, args, str(e))

    def runQueryForSingleRow(self, sqlstr, *args):
        """
        Runs a query that should return exactly one row; raises an error if
        it does not.
        """
        result = self.runQuery(sqlstr, *args)
        if len(result) == 1:
            return result[0]
        else:
            raise SimError(_ERROR_NAME,
                           "Query: {0} expected to return exactly one row; {1} row(s) returned",
                           sqlstr, len(result))


class SimLiveOutputDatabase(SimOutputDatabase):
    """
    Encapsulates a "live" sqlite3 simulation database - that is, a database for a model
    that is (or is about to be) executed.

    SimLiveOutputDatabase creates a new database, populates its static data (simulation
    elements and dataset definitions) and wires the model object dataset objects to this
    database in order to capture output data during the simulation run.

    TODO We currently create a new database whenever we switch to animate/run mode, wiping out
    any previously created database.  Do we want to detect if the model has changed before doing this?
    We could also consider creating the database as either a temporary or in-memory file, and
    give the user the option of saving the database (as an archive) before returning to edit mode,
    opening a new model, or exiting.
    """
    def __init__(self):
        """
        """
        super().__init__()
        self.__model = None
        self.__saved = False

    def initialize_existing(self, model, dbpath, isTemporary=False):
        """
        Open an existing database.  Under the assumption that there may be concurrent
        writes, set the transaction type to IMMEDIATE.
        TODO.  I believe (but cannot confirm) that any competing connection will retry
        until the sqlite3.connect() timeout (default 5 seconds) is reached.
        """
        self.__model = model
        logger.info("Opening an existing output database at %s:", dbpath)
        self._connect(dbpath, isTemporary)
        self.connection.isolation_level = 'IMMEDIATE'

        # Make sure the existing database matches the model by finding a
        # database dataset row for each model dataset
        for dset in self.__model.datasets:
            try:
                self.getDatasetID(dset)
            except SimError as e:
                logger.error(e)
                msg = "Failure initializing existing output database {0} for model {1}; datasets do not match"
                raise SimError(_ERROR_NAME, msg, dbpath, model.filename)

    def initialize(self, model, inMemory=False):
        """
        Creates and initializes a new output database for based on the passed
        model and package manager (for process/entity elements).  Created
        database may be either in-memory or a temporary file.
        """
        self.__model = model
        if inMemory:
            self._create_in_memory_database()
        else:
            self._create_database()
        self._initialize_database(model)

    @property
    def default_dbpath(self):
        """
        Returns the filename, including absolute path, of the output database
        for the current model. It is of form <modelname>.simoutput and is
        located in the same directory as the model definition.
        """
        if not self.__model:
            return None
        root, modelExt = os.path.splitext(self.__model.filename)
        modelDir, fname  = os.path.split(root)
        databaseName = fname + ".simoutput"
        return os.path.join(modelDir, databaseName)

    def _create_in_memory_database(self):
        """
        Creates a new in-memory database and initializes the schema/fixed
        tables
        """
        logger.info("creating in-memory output database...")
        self._connect(":memory:", False)
        self._runScript('CreateOutputDb.sql')

    def _create_database(self):
        """
        Creates a new database in a temporary file and initializes the schema and
        fixed tables.
        """
        f, dbpath = tempfile.mkstemp(suffix='.simoutput')
        # _connect() will re-open the file, so close it here first - otherwise, attempts
        # to remove it will fail with "another process is working with this file" error
        os.close(f)
        logger.info("creating output database in temporary file %s:", dbpath)
        self._connect(dbpath, True)
        self._runScript('CreateOutputDb.sql')

    def _initialize_database(self, model):
        """
        Initialize the static portion of the output database, based on
        the model and passed package manager data.
        """
        self._load_elements()
        self._load_datasets()
        self.commit()

    def commit(self):
        """
        Commit any database changes.
        """
        self.connection.commit()
        
    def _load_elements(self):      
        """
        Populate the element table, one row per element in the model
        """
        def makeValues(element):
            typeID = self._element_typeid(element.__class__)
            return (element.element_id, element.full_class_name, typeID)
        
        elementValues = [makeValues(e) for e in self.__model.elements]

        insertStmt = 'insert into element (id, classname, type) values (?, ?, ?)'
        cur = self.connection.cursor()
        cur.executemany(insertStmt, elementValues)

    def _load_datasets(self):
        """
        Populate the dataset table, one row per dataset in the model
        """
        datasetValues = []
        dsetID = self._max_id('dataset') + 1
        assert dsetID == 1, "dataset table not empty before _load_datasets() call"
        
        for dset in self.__model.datasets:
            valueType = dset.valuetype.__name__
            dsetParms = (dsetID, dset.element_id, dset.name, valueType,
                         dset.is_time_weighted, dset.timeunit)
            datasetValues.append(dsetParms)
            dsetID += 1

        insertStmt = 'insert into dataset values (?, ?, ?, ?, ?, ?)'
        cur = self.connection.cursor()
        cur.executemany(insertStmt, datasetValues)

    def _element_typeid(self, elementClass):
        """
        Returns the ID (element type key) corresponding to a passed class.
        """
        for i in range(len(_ELEMENT_TYPE_CLASSES)):
            if issubclass(elementClass, _ELEMENT_TYPE_CLASSES[i]):
                return i+1
        msg = "Class {0} is not a valid element type."
        raise SimError(_ERROR_NAME, msg, elementClass.__name__)

    def _max_id(self, tablename):
        """
        Return the maximum ID for the passed tablename.
        """
        # Can't use parameter substitution (?) for a tablename.
        # At least check for an non-alphanumeric string, for a modicum of security
        if not tablename.isalnum():
            msg = "Non-alphanumeric tablename passed to maxID! ({0})"
            raise SimError(_ERROR_NAME, msg, tablename)

        sqlstr = "select max(id) from %s;" % tablename
        c = self.connection.cursor()
        c.execute(sqlstr)
        r = c.fetchone()
        if r[0]:
            return r[0]
        else:
            return 0

    def initialize_run(self, runNumber):
        """
        Initialize the database for the current run, by:
        1.  Deleting any existing data for that run
        2.  Loading the datasets for that run
        """
        self._delete_run(runNumber)
        self._create_datasinks(runNumber)
        self.commit()

    def _delete_run(self, runNumber):
        """
        Delete all data for the specified run.  Deletes datasetvaluye rows for a specified run
        """
        sqlstr = "delete from datasetvalue where run = ?;"
        try:
            cursor = self.connection.cursor()
            cursor.execute(sqlstr, (runNumber,))
            self.commit()
        except Exception as e:
            raise SimError(_ERROR_NAME, "Failure executing delete for run number: {0}; {1}",
                           runNumber, str(e))

    def _create_datasinks(self, runNumber):
        """
        Create datasinks for each of the model's datasets
        """
        for dset in self.__model.datasets:
            self._create_datasink(dset, runNumber)

    def _create_datasink(self, dataset, runNumber):
        """
        Create a DB datasink for the passed dataset, and assign it to the dataset
        """
        if dataset.is_time_weighted:
            dataset.datasink = SimDbTimeSeriesDatasink(self, dataset, runNumber)
        else:
            dataset.datasink = SimDbDatasink(self, dataset, runNumber)

    def flush_datasets(self):
        """
        Flush all of the datasets in the model (NOT the database) -
        which in turn flushes the active datasinks.
        """
        for dset in self.__model.datasets:
            dset.flush()


class SimArchivedOutputDatabase(SimOutputDatabase):
    """
    Encapsulates an "archived" sqlite3 simulation database - that is,
    a database created during a previous simulation run. It is intended to be
    read-only. If constructed with isTemporary = True, the database will
    be deleted after it is closed. That feature is primarily for the benefit
    of :class:`Simulation` execution methods, which pass the temporary
    database path to a SimResult object, which in turn opens it as a
    SimArchived database.
    """
    def __init__(self, dbpath, isTemporary=False):
        """
        """
        super().__init__()
        self._connect(dbpath, isTemporary)


class SimOutputHistogramData(object):
    """
    Class that retrieves, calculates and stores the data required to create a histogram
    for a single dataset (from a specified output database).
    TODO - allow a sequence of datasets, perhaps for plotting on a single chart? (or
    do we do that through multiple SimOutputHistogramData instances?)
    """
    def __init__(self, outputDb, dataset, run, batch=None):
        self.dataset = dataset
        self.run = run
        if batch is None:
            batch = outputDb.last_batch(run)
        self.batch = batch
        self.outputDb = outputDb
        self.values = None
        self.nbins = 10
        self.weights = None
        datasetID = outputDb.getDatasetID(dataset)

        if dataset.istimeweighted:
            self.getTimeWeightedData(datasetID, run, batch, outputDb)
        else:
            self.getUnweightedData(datasetID, run, batch, outputDb)

    def getTimeWeightedData(self, datasetid, run, batch, outputDb):
        """
        Get the data and weights (weight for each data value is total simulated time for that
        data value).  Then normalize those weights (total times) as a percentage of the total
        time of the entire sample.  Time-weighted data are actually plotted as a simple bar
        chart (not histogram), one bar per value, so no need to calculate the number of bins.
        """
        #sqlstr = 'select value, sum(simtime) from timeweighteddata where datasetid = ? and run = ? group by value;'

        sqlstr = """
                 SELECT value,
                        SUM(CASE WHEN totimestamp IS NULL THEN ?
                             ELSE totimestamp END - simtimestamp)
                 FROM datasetvalue
                 WHERE dataset = ? AND run = ? AND batch = ?
                 GROUP BY value;
                 """

        minTime, maxTime = outputDb.batch_time_bounds(run, batch)
        result = outputDb.runQuery(sqlstr, maxTime, datasetid, run, batch)
        if len(result) == 0:
            self.values = []
            self.weights = []
            return
        self.values, rawWeights = zip(*result)
        sumweights = sum(rawWeights)
        if sumweights:
            self.weights = [w / sumweights for w in rawWeights]
        else:
            self.values = []

    def getUnweightedData(self, datasetid, run, batch, outputDb):
        """
        Get data and set nbins for an unweighted dataset histogram.
        nbins is calculated according to the Freedman-Diaconis rule, but then rounded
        up to the nearest integer value.
        """
        sqlstr = """
                 select value from datasetvalue
                 where dataset = ? and run = ? and batch = ? order by value;
                 """
        result = outputDb.runQuery(sqlstr, datasetid, run, batch)
        n = len(result)
        if n == 0:
            self.values = []
            return

        self.values, = zip(*result)
        if n < 4:
            quartile1 = self.values[0]
            quartile3 = self.values[n-1]
        else:
            quartile1 = self.values[round(n/4)]
            quartile3 = self.values[round(n * 0.75)]

        iqr = quartile3 - quartile1
        totalRange = self.values[-1] - self.values[0]
        h = 2 * iqr / pow(n, 1/3)

        if iqr == 0 or round(h) == 0:
            self.nbins = max(totalRange, 1)
        else:
            self.nbins = max(round(totalRange/round(h) + 0.5), 1)


class SimTimeSeriesData(object):
    """
    Class that retrieves, calculates and stores the data required to create a histogram
    for a single dataset (from a specified output database).
    TODO - allow a sequence of datasets, perhaps for plotting on a single chart? (or
    do we do that through multiple SimOutputHistogramData instances?)
    """
    def __init__(self,  outputDb, dataset, run, batch=None, windowSize = None):
        self.outputDb = outputDb
        self.dataset = dataset
        self.run = run
        if batch is None:
            batch = outputDb.last_batch(run)
        self.batch = batch
        self.windowSize = windowSize
        self.movingAvgWindowPct = 0.05
        self.timevalues = None
        self.yvalues = None
        self.accumulatedmean = None
        self.meantimevalues = None
        datasetID = outputDb.getDatasetID(dataset)

        if dataset.name == _ENTRIES_DATASET_NAME:
            self.getCumulativeCountData(outputDb, datasetID, run, batch)
        elif dataset.istimeweighted:
            self.getTimeWeightedData(outputDb, datasetID, run, batch)
        else:
            self.getUnweightedData(outputDb, datasetID, run, batch)

    def fromToTimestamps(self):
        """
        Return the from timestamp (lower bound of the query) based on the current maximum
        timestamp and the specified window size.  Also return that maximum timestamp, as it
        is the effective upper bound of the query.

        If windowSize is None, the effective window is the entire batch, so just return the
        start of the batch (as returned by SimOutputData.batchBounds()) as the lower bound.
        """
        minTime, maxTime = self.outputDb.batch_time_bounds(self.run, self.batch)
        if not self.windowSize:
            return minTime, maxTime
        else:
            # If the window is larger than the maximum timestamp, return zero
            convertedWindowSize = self.windowSize.toUnits(self.dataset.timeunit)
            return max(maxTime - convertedWindowSize.value, minTime), maxTime

    def getTimeWeightedData(self, outputDb, datasetid, run, batch):
        """
        For time-weighted data, simply return the timestamps (x values) and corresponding
        dataset values (y values) for all entries in the time window.

        We probably do not have entries with timestamps for the exact beginning and ending
        (from and to time) of the window.  So we find the initial window value by also
        selecting the row immediately before the start of the window, and adjusting it's
        time value to the start of the window.  The final retrieved value is also the value at
        the end of the window, so we append a row to the result set to reflect that.
        """
        fromTime, toTime = self.fromToTimestamps()
        sqlstr = """
                 select simtimestamp, value from datasetvalue
                 where dataset = ? and run = ? and batch = ? and
                 (simtimestamp >= ? or (simtimestamp < ? and totimestamp >= ?) or
                     (simtimestamp < ? and totimestamp is null))
                 order by simtimestamp;
                 """
        result = outputDb.runQuery(sqlstr, datasetid, run, batch,
                                   fromTime, fromTime, fromTime, fromTime)
        if len(result) > 0:
            firstTm, firstY = result[0]
            if firstTm < fromTime:
                result[0] = (fromTime, firstY)
            lastTm, lastY = result[-1]
            if lastTm < toTime:
                result.append((toTime, lastY))
            self.timevalues, self.yvalues = zip(*result)

    def getUnweightedData(self, outputDb, datasetid, run, batch):
        """
        For unweighted data, return timestamps and corresponding y values that represent a
        rolling average of the dataset values.  That rolling average is the average of
        all dataset values within a "moving avg time window" preceding the the corresponding
        timestamp. As with time-weighted data, only data within the overall time window  are
        returned.

        The moving average time window length is calculated as a percentage of the overall
        time window length, and the rolling average window itself ends at the corresponding
        timestamp.  For example, ifthe rolling average window is 100 seconds, then the y value
        at timestamp 900 seconds is the average value recorded between 800 and 900 seconds on
        the simulated clock.
        """
        minTime, maxTime = self.outputDb.batch_time_bounds(run, batch)
        if self.windowSize:
            convertedWindowSize = self.windowSize.toUnits(self.dataset.timeunit).value
        else:
            convertedWindowSize = maxTime - minTime
        movingAvgWindowSize = convertedWindowSize * self.movingAvgWindowPct

        # See http://stackoverflow.com/questions/10624902/sql-moving-average
        sqlstr = """
                 select d1.simtimestamp, avg(d2.value) as avgvalue
                 from datasetvalue as d1, datasetvalue as d2
                 where d1.dataset = ? and d2.dataset = ?
                 and d1.run = ? and d2.run = ?
                 and d2.simtimestamp between (d1.simtimestamp - ?) and d1.simtimestamp
                 and d1.simtimestamp > ?
                 group by d1.simtimestamp
                 """

        result = outputDb.runQuery(sqlstr, datasetid, datasetid, run, run, movingAvgWindowSize, minTime)
        if len(result) > 0:
            self.timevalues, self.yvalues = zip(*result)

    def getCumulativeCountData(self, outputDb, datasetid, run, batch):
        """
        For Entries datasets, we just want to accumulate the number of dataset values
        over time.
        """
        sqlstr = """
                 select simtimestamp from datasetvalue
                 where dataset = ? and run = ? and batch = ?
                 order by simtimestamp;
                 """
        result = outputDb.runQuery(sqlstr, datasetid, run, batch)
        self.timevalues = [r[0] for r in result]
        self.yvalues = list(range(1, len(result)+1))


class LastValue(object):
    """
    """
    def __init__(self):
        self.last = None

    def step(self, value):
        self.last = value

    def finalize(self):
        return self.last

DatasetSummaryStatsRaw = namedtuple('DatasetSummaryStats',
         ['element_id', 'datasetName', 'valuetype', 'timeunit',
          'currentValue', 'count', 'min', 'max', 'mean'])

class DatasetSummaryStats(DatasetSummaryStatsRaw):
    """
    Wraps the namedtuple, converting values to SimTime objects as required.
    """
    # pylint doesn't like super() when the base class is a named tuple
    # pylint: disable=E1101
    def _convertSimTime(self, value):
        if self.valuetype == 'SimTime' and value is not None:
            return SimTime(value, self.timeunit)
        else:
            return value

    @property
    def currentValue(self):
        return self._convertSimTime(super().currentValue)

    @property
    def min(self):
        return self._convertSimTime(super().min)

    @property
    def max(self):
        return self._convertSimTime(super().max)

    @property
    def mean(self):
        return self._convertSimTime(super().mean)

class SimSummaryData(object):
    """
    Class that retrieves summary statistics from an output database, primarily for display in
    output table views on the simulation dashboard.

    TODO Add median?
    """
    def __init__(self, outputDb, run, elementID, batch=None):
        """
        """
        self.__resultDict = {}
        if batch is None:
            batch = outputDb.last_batch(run)
        rows = self._fetchData(outputDb, run, batch, elementID)
        for row in rows:
            rowkey = (row.element_id, row.datasetName)
            self.__resultDict[rowkey] = row

    def _fetchData(self, outputDb, run, batch, elementID):
        """
        Assume that dataset was flushed at startTime
        Note the multiplication by 1.0, to ensure that the result of a time-weighted
        mean is a float (and not rounded to an integer value if all values and
        timestamps are ints.)
        Data are returned as DatasetSummaryStats objects, whose properties
        convert time values to SimTime objects as required.
        """
        batchStartTm, batchEndTm = outputDb.batch_time_bounds(run, batch)
        sqlstr = """
        SELECT dataset.element, dataset.name, dataset.valueType, dataset.timeunit,
               last(datasetvalue.value),
               COUNT(datasetvalue.value), MIN(datasetvalue.value), MAX(datasetvalue.value),
               CASE WHEN dataset.istimeweighted = 1 THEN
                       SUM(datasetvalue.value * 1.0 *
                         (CASE WHEN datasetvalue.totimestamp IS NULL THEN ?
                              ELSE datasetvalue.totimestamp END - datasetvalue.simtimestamp)) / ?
                    ELSE AVG(datasetvalue.value) END
             FROM datasetvalue INNER JOIN dataset ON datasetvalue.dataset = dataset.id
             WHERE datasetvalue.run = ? AND datasetvalue.batch = ? AND dataset.element = ?
             GROUP BY datasetvalue.dataset;
            """

        def tupleFactory(cursor, row): # pylint: disable=unused-argument
            return DatasetSummaryStats(*row)

        outputDb.connection.create_aggregate("last", 1, LastValue)
        savedRowFactory = outputDb.connection.row_factory
        try:
            outputDb.connection.row_factory = tupleFactory
            result = outputDb.runQuery(sqlstr, batchEndTm,
                                       batchEndTm-batchStartTm,
                                       run, batch, elementID)
            return result
        finally:
            outputDb.connection.row_factory = savedRowFactory

    def getData(self, dataset):
        """
        Returns the DatasetSummaryStats for a specified dataset
        (DatasetSummaryStats property values are converted to SimTime values
        as needed/appropriate)
        """
        rowkey = (dataset.element_id, dataset.name)
        if rowkey in self.__resultDict:
            return self.__resultDict[rowkey]
        else:
            nullStats = DatasetSummaryStats(None, None, None, None, None,
                                            None, None, None, None)
            return nullStats

    def getRawData(self, dataset):
        """
        Returns the DatasetSummaryStatsRaw for a specified dataset -
        DatasetSummaryStatsRaw property values are straight from the
        database, and never SimTime objects.
        """
        return DatasetSummaryStatsRaw(*self.getData(dataset))


class SimPercentileData(object):
    """
    Class that retrieves percentile values from an output database for a
    specified dataset, batch and run.
    """
    def __init__(self, outputDb):
        """
        """
        self.outputDb = outputDb

    def getPercentiles(self, dataset, run, batch=None):
        """
        Get percentile values for a specified dataset, run and batch
        """
        if batch is None:
            batch = self.outputDb.last_batch(run)

        rows = self._fetchData(self.outputDb, dataset, run, batch)
        return self._calculatePercentiles(rows)

    def _fetchData(self, outputDb, dataset, run, batch):
        """
        Assume that dataset was flushed at startTime.
        The choice of different queries (time-weighted vs. non-time-weighted
        datasets) is a performance optimization.  Execution time for
        non-time-weighted is reduced by better than 80%.
        """
        datasetid = self.outputDb.getDatasetID(dataset)
        if dataset.istimeweighted:
            batchStartTm, batchEndTm = outputDb.batch_time_bounds(run, batch)
            sqlstr = """
                SELECT value,
                        SUM(CASE WHEN totimestamp IS NULL THEN ?
                               ELSE totimestamp END - simtimestamp)
                     FROM datasetvalue
                     WHERE dataset = ? AND run = ? AND batch = ?
                     GROUP BY value;
                    """
            result = outputDb.runQuery(sqlstr, batchEndTm, datasetid, run, batch)
        else:
            sqlstr = """
                SELECT value, COUNT(value)
                     FROM datasetvalue
                     WHERE dataset = ? AND run = ? AND batch = ?
                     GROUP BY value;
                    """
            result = outputDb.runQuery(sqlstr, datasetid, run, batch)
        return result

    def _calculatePercentiles(self, rows):
        """
        Calculate and return a list of percentile values (0 through 100) based
        on the data in the passed row collection.
        """
        totalweight = sum(row[1] for row in rows)
        percentile = [None] * 101
        cumweight = 0
        currPercentile = 0
        for row in rows:
            value, weight = row
            cumweight += weight
            while 100.0 * cumweight / totalweight >= currPercentile:
                percentile[currPercentile] = value
                currPercentile += 1

        return percentile













