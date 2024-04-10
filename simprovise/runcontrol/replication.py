#===============================================================================
# MODULE replication
#
# Copyright (C) 2014-2015 Howard Klein - All Rights Reserved
#
# Defines SimReplication and SimReplicator classes. SimReplicator instances
# are used to run one or more simulation run replications via SimReplication
# instances.
#
# When SimReplicator is used by a Qt-based UI, it communicates replication
# status updates to the UI via Qt Signals. When used in an environment without
# PySide, the Signal class is replaced by a mock whose methods are no-ops.
#===============================================================================
import sys, os, time
import multiprocessing, threading
import tempfile, shutil
import sqlite3
import logging
from traceback import format_tb

# Use PySide if it is installed; otherwise replace with mock object classes
try:
    from PySide.QtCore import QObject, Signal
except ImportError:
    from simprovise.runcontrol.mockqt import MockQObject as QObject
    from simprovise.runcontrol.mockqt import MockSignal as Signal

from simprovise.core import (SimModel, SimClock, SimError, SimTime,
                             SimLogging, simtime, simrandom)
from simprovise.core.simevent import EventProcessor
from simprovise.database import SimDatabaseManager
from simprovise.runcontrol.simruncontrol import (SimRunControlParameters,
                                                 SimRunControlScheduler,
                                                 SimReplicationParameters)
from simprovise.runcontrol.messagequeue import (SimMessageQueue,
                                                SimMessageQueueSender)

logger = SimLogging.get_logger(__name__)

_ERROR_NAME = "Replication Error"
_STATUS_NOT_STARTED = 'NOT_STARTED'
_STATUS_IN_PROGRESS = 'IN_PROGRESS'
_STATUS_COMPLETE = 'COMPLETE'
_STATUS_CANCELLED = 'CANCELLED'


def execute_replication(modelPath, dbpath, runNumber, warmupLength,
                       batchLength, nBatches, queue=None):
    """
    Simple function that creates and executes a replication, and captures
    any failures that occurred during that execution.  Exceptions raised
    by the model are captured in the replication exception member; exceptions
    raised during event processing "should" just propagate to here, where we
    in turn catch them.

    Designed as a task to be executed by a multiprocessing Pool.  Returns
    the replication run number, the path of the temporary database populated
    by the replication, and any exception that was raised (or None)
    """
    tbstring = None
    try:
        print("executeReplication for run", runNumber, "pid", os.getpid(), modelPath)
        model = SimModel.load_model_from_script(modelPath)
        replication = SimReplication(model, runNumber, warmupLength, batchLength,
                                     nBatches, dbpath, queue)
        replication.execute()
    except Exception as e:
        print("executeReplication exception:", e)
        replication.exception = e
        lines = format_tb(e.__cause__.__traceback__)
        tbstring = "".join(lines)

    return runNumber, dbpath, replication.exception, tbstring

class SimReplication(QObject):
    """
    Encapsulates a single replication - i.e., a single run of the simulation
    model as defined by the passed model and run control parameters.

    The initializer may also be passed a database path, which should be an output
    database that is fully initialized - i.e., has it's dataset table
    populated - but does not contain any datasetvalues.  By doing this, we
    ensure that every replication in a set has the same dataset table data -
    and therefore the same dataset integer IDs for a given dataset
    (element name/dataset name)  If we create the database from scratch,
    dataset integer IDs can vary from replication replication, meaning that
    the datasetvalue row data could not be simply copied from one replication
    database to another.

    The database path may be None; that should only be used if we are doing
    a single stand-alone run - e.g., using SimReplication to execute a model
    in-process. When the database path is none, we do create a new database
    and initialize it during initialization;
    
    TODO: Don't think this needs to be a QObject, since it doesn't emit or
    connect to any Qt Signals
    """
    def __init__(self, model, runNumber, warmupLength,
                 batchLength, nBatches, dbPath=None, queue=None):
        super().__init__()
        """
        Initialize a replication with the path to the model, an initialized
        output database, and the run control parameters.  The initializer
        sets up a non-animated run, initializes the random number generators
        for this run, initializes the simulation clock, and loads the model.
        """
        SimLogging.set_level(logging.WARN)
        self.__databaseManager = SimDatabaseManager()
        self.__dbPath = dbPath
        self.__model = model
        self.__runControlParameters = \
            SimRunControlParameters(runNumber, warmupLength, batchLength,
                                    nBatches)
        
        self.__totalRunLength = warmupLength + nBatches * batchLength
        self.__hasExecuted = False
        self.exception = None
        if not self.__totalRunLength > 0:
            msg = 'Total Simulation run time not greater than zero'
            raise SimError(_ERROR_NAME, msg)

        self.__msgQueue = None
        if queue:
            self.__msgQueue = SimMessageQueueSender(runNumber, queue)

    @property
    def dbPath(self):
        return self.__dbPath

    def execute(self):
        """
        Actually execute the replication/simulation run.
        """
        if self.__hasExecuted:
            raise SimError(_ERROR_NAME,
                           "Replication has already executed (and cannot be re-executed)")

        runNumber = self.__runControlParameters.run_number
        logger.info("starting replication for run number %d ...", runNumber)
        try:
            simrandom.initialize(runNumber)
            SimClock.initialize()
             
            # Create the event processor before loading the model, as the
            # EventProcessor initializer re-initializes/empties the events chain
            # (and model static initialization adds source generation events to
            # the chain)
            eventProcessor = EventProcessor()
            
            # Invoke staticInitialize on all static objects in the model
            #for staticobj in self.__model.static_objects:
            for e in self.__model.elements:
                e.final_initialize()
            
            # Do any model initialization functions (a TODO)
               
            # Do output database initialization
            if self.__dbPath:
                self.__databaseManager.open_existing_database(self.__model, self.__dbPath)
            else:
                self.__databaseManager.create_output_database(self.__model)
                self.__dbPath = self.__databaseManager.current_database_path
                
            self.__databaseManager.set_commit_rate(0)
            self.__databaseManager.initialize_run(runNumber)
            
            # Initialize the first batch
            for dset in self.__model.datasets:
                dset.initialize_batch(self._initial_batch_number())
                
            # TODO replication/background scheduler
            runControlScheduler = SimRunControlScheduler(self.__model,
                                                         self.__runControlParameters,
                                                         progressIntervalPct=10,
                                                         msgQueue=self.__msgQueue)
            runControlScheduler.schedule_run_control_events()

            startTime = time.time()
            self._send_status_message(SimMessageQueue.STATUS_STARTED)
            nEvents = eventProcessor.process_events(self.__totalRunLength)
            print("Run", self.__runControlParameters.run_number,
                  "execution complete:", nEvents, "events processed. Process Time:",
                  time.time()-startTime)
            self.__databaseManager.close_output_database(delete=False)
        except Exception as e:
            try:
                self.__databaseManager.close_output_database(delete=True)
            except Exception as dbexcpt:
                closemsg = "Unable to close/delete temporary output database: %s"
                logger.error(closemsg, dbexcpt)
            raise SimError(_ERROR_NAME, str(e)) from e
        finally:
            self.__hasExecuted = True

    def _send_status_message(self, status):
        if self.__msgQueue:
            self.__msgQueue.send_status_message(status)
            
    def _initial_batch_number(self):
        """
        Returns the (integer) number of the first batch.
        
        By convention, the warmup is batch number zero. So if a warmup
        is specified, the initial batch number is zero; if not, te
        initial batch is one.
        """
        if self.__runControlParameters.warmup_length > 0:
            return 0
        else:
            return 1


class SimReplicator(QObject):
    """
    The SimReplicator manages/executes a set of SimReplications.

    The SimReplicator is initialized with a model and run control parameters.
    The primary public method is executeReplications(), which takes replication
    parameters as an arugment and executes the replications as tasks on a
    multiprocessing pool allowing tasks to execute in parallel (in separate
    processes).  The replication parameters specifies the maximum number of
    processes to run concurrently.

    executeReplications() also takes an optional asynch parameter.  When True,
    the method returns immediately, with a background thread emitting a
    ReplicationsComplete signal once all tasks have finished.  If False,
    executeReplications() will block until all replication tasks complete (at
    which point it will emit the ReplicationsComplete signal as well.)  When
    executed asynchronously, a ReplicationFinished signal is emitted after
    each replication.

    If executeReplications() is called with asynch=True, the client may cancel
    in-progress and remaining tasks via a cancel() call, which invokes the
    pool's terminate() method and emits a ReplicationsCancelled signal.

    All replication output is written to a temporary output database, created
    by the replicator.  The path to that database is available via property.
    The code that creates the replicator is responsible for cleaning up this
    temporary file by either moving it to a permanent location or deleting it.

    Finally, there are a number of properties which either:
    - indicate the status of the replication execution
    - If completed, indicate the number of tasks/number of failed tasks
    - provide the path of the output database created by the replicator.

    In order to minimize database contention between replications executing
    in parallel, each replication writes to its own (temporary) output
    database.  An "empty" database(with Element and Dataset tables populated,
    but no dataset values) is created by the replicator, with a copy being
    sent to each replication.  This ensures that each replication uses
    an identical dataset table.  When the first (successful) replication
    completes, it's database becomes the master; when subsequent replications
    complete, their dataset values are merged into the master.

    Concurrency/Thread Safety

    Replications have a process to themselves when executing, so there shouold
    be no safety issues there.  The results of each replication (a simple run
    number, database path and exception tuple) are processed by a callback
    function that runs on a separate thread in the main process.  Every callback
    runs on the same thread, so the database merge calls should never occur
    in parallel.  If executeReplications() is invoked with asynch=True, there
    is a third thread, which joins the pool.  Changes to the __status member
    variable should be threadsafe in a Python context, and the result
    accessors should prevent the results (or output database) from being
    accessed until after the pool has finished processing and both of these
    background threads are done.  When running in a Qt environment (see below),
    this third thread emits a ReplicationsComplete Qt signal when the pool is
    joined.  If the signal is connected to a QObject created on the main thread,
    the slot function will be executed on the main thread (per Qt behavior).

    Also... in many respects a cleaner design would involve passing an
    external SimDatabaseManager instance into the replicator, which would open
    and take ownership of the output database.  The problem is that sqlite3
    connection objects can operate only in the thread in which they are created.
    If a database object (and it's connection) is created in the callback
    thread, it cannot be used to access the database in the main thread.  So
    instead, we close the connection after replications are completed/cancelled
    and provide access to the output database path, which may then be opened by
    a database manager in the main thread.
    
    Qt Issues
    
    The SimReplicator (in conjunction with its SimMessageQueue) is designed to
    be used by a PySide Qt GUI application (and can also be used outside of one).
    It facilitates Qt application that can stay responsive to user input while
    it's SimReplicator executes replications asynchronously, and receives/reports 
    on status updates during the execution. The basic flow:
    
     1. The SimReplicator creates a SimMessageQueue during initialization.
    
     2. The SimReplicator passes the SimMessageQueue's multiprocessing
        queue to each replication process, which executes a SimReplication.
        the replication processes are launched via a multiprocessing pool.
        Each SimReplication object creates A SimMessageQueueSender, which
        puts status update messages into the queue. In this scenario, 
        :meth:`execute_replications` should be called with parameter asynch
        set to True; in that case, execute_replications() returns after
        creating a separate thread to wait on completion of all of the
        replication processes, at which point a Qt Signal is emitted.
                
     3. The SimReplicator's SimMessageQueue creates a separate thread and
        listens for messages from the SimReplication senders on that
        thread. It responds to messages by emitting Qt Signals, which can
        then be  connected to and processed by the Qt GUI application running
        on the main thread. Essentially the listener just converts recieved
        queue messages into Qt Signals, and relies on the GUI app to connect
        those signals to slots in the GUI app.
        
    When operating outside of a Qt GUI (e.g. a command line application),
    the SimReplicator would typically execute replications synchronously.
    PySide is not required for that type of application, and if it is
    not installed, mock versions of Qt classes QObject and Signal are used
    in their place. In that case all Signal-related calls are no-ops.
    """
    ReplicationsComplete = Signal()
    ReplicationsCancelled = Signal()
    ReplicationStarted = Signal(int)
    ReplicationFinished = Signal(int, bool, str)
    ReplicationProgress = Signal(int, int)

    def __init__(self, model, warmupLength, batchLength, nBatches):
        super().__init__()
        """
        Set up the replication sequence based on the model, run control
        parameters, and replication parameters.  Also create the initial
        "template" output database, which will be copied and populated
        by each replication.
        """
        # create a SimRunControlParameters object just to validate
        # those parameters (raising if invalid) before things get going
        testRunControlParameters = \
            SimRunControlParameters(1, warmupLength, batchLength,
                                    nBatches)
        self.__model = model
        self.__modelPath = model.filename
        self.__warmupLength = warmupLength
        self.__batchLength = batchLength
        self.__nBatches = nBatches
        self.__pool = None
        self.__status = _STATUS_NOT_STARTED
        self.__nRepsStarted = 0
        self.__nRepsFailed = 0
        self.__nRepsFinished = 0
        self.__results = {}
        self.__msgQueue = SimMessageQueue()
        self.__masterDbPath = None
        self.__masterDbConnection = None
        self.__initializedDbPath = None
        self._create_initialized_database()
        self.__msgQueue.StatusMessageReceived.connect(self._replication_started)
        self.__msgQueue.ProgressMessageReceived.connect(self.ReplicationProgress)
        # Should we be doing something with msgQueue.LogMessageReceived?


    @property
    def warmup_length(self):
        """
        Run Control - warmup length for each replication
        """
        return self.__warmupLength

    @property
    def batch_length(self):
        """
        Run Control - batch length for each replication
        """
        return self.__batchLength

    @property
    def nbatches(self):
        """
        Run Control - number of batches for each replication
        """
        return self.__nBatches

    @property
    def status(self):
        """
        Current status of the replicator - NOT_STARTED, IN_PROGRESS or
        COMPLETE
        """
        return self.__status

    @property
    def msg_queue(self):
        """
        Return the message queue instance, primarily so that clients can
        connect it's signals
        """
        return self.__msgQueue

    @property
    def not_started(self):
        """
        Returns True if replication execution has not yet started
        """
        return self.__status == _STATUS_NOT_STARTED

    @property
    def in_progress(self):
        """
        Returns True if execution is in progress (but not complete)
        """
        return self.__status == _STATUS_IN_PROGRESS

    @property
    def complete(self):
        """
        Returns True if execution is completed - i.e., all replications have
        finished.
        """
        return self.__status == _STATUS_COMPLETE

    @property
    def cancelled(self):
        """
        Returns True if execution was cancelled
        """
        return self.__status == _STATUS_CANCELLED

    @property
    def output_dbpath(self):
        """
        Returns the path to the (temporary) output database, once it is created
        (after the first replication completes).  Should generally not be called
        during execution, and raises an exception if the path has not yet been set.
        """
        if self.__masterDbPath:
            return self.__masterDbPath
        else:
            raise SimError(_ERROR_NAME, "outputDbPath() called before any replications complete")

    @property
    def started_count(self):
        """
        Returns the number of replications that have started
        """
        return self.__nRepsStarted

    @property
    def in_progress_count(self):
        """
        Returns the number of replications that are currently in progress
        """
        return self.__nRepsStarted - self.__nRepsFinished

    @property
    def finished_count(self):
        """
        Returns the number of replications that have finished (successes
        and failures)
        """
        return self.__nRepsFinished

    @property
    def success_count(self):
        """
        Returns the number of replications that have succeeded
        """
        return self.__nRepsFinished - self.__nRepsFailed

    @property
    def failure_count(self):
        """
        Returns the number of replications that failed
        """
        return self.__nRepsFailed

    def cancel(self):
        """
        Cancel replications in progress
        """
        if not self.in_progress:
            logger.info("replications not executing - nothing to cancel")
            return

        assert self.__pool, "__pool member not set for cancel() call"
        self.__status = _STATUS_CANCELLED
        self.__pool.terminate()
        self.ReplicationsCancelled.emit()

    def results(self):
        """
        Returns a copy of the results dictionary (keyed by run number) for
        all runs executed by this replicator - potentially over multiple
        runs. (In other words, if we execute runs 1-10 followed by runs 8-18,
        results will contain a result object for runs 1-18).  Each result
        contains the exception generated if the run failed, or None if the
        run succeeded.

        The making of the copy is protected by a lock, as the results
        dictionary gets updated in a separate thread.
        """
        lock = threading.Lock()
        with lock:
            return dict(self.__results)

    def cleanup(self):
        """
        Delete temporary files (except for output database, which is the
        responsibility of the replicator's owner/caller)
        """
        if self.__initializedDbPath:
            logger.info("removing temporary file: ", self.__initializedDbPath)
            os.remove(self.__initializedDbPath)
            self.__initializedDbPath =  None

    def execute_replications(self, replicationParameters, asynch=False):
        """
        Executes replications using a multiprocessing Pool, with the
        replication runs (and the size of the pool) sepcified via the passed
        replication parameters.  If this is the first call to
        executeReplications(), a new temporary output database is created,
        with all replication outputs merged into that database (including
        replications generated by subsequent executeReplications() calls.)

        The size (maximum number of simultaenous child processes) of the pool
        is specified by the caller. We started out specifying maxtasksperchild
        as 1, which starts a new process for each replication (rather than
        reusing processes once we have more than n replications)  by allowing
        process re-use, we speed up overall execution - for one example with
        24 replications, the total time decreased from about 14 to 10 seconds.
        """
        if self.in_progress:
            raise SimError(_ERROR_NAME, "Replications are currently in progress")

        self.__status = _STATUS_IN_PROGRESS
        n = replicationParameters.max_concurrent_replications
        pool = multiprocessing.Pool(processes=n)
        self.__pool = pool
        firstRun, lastRun = replicationParameters.replication_range
        self.__nRuns = lastRun +1 - firstRun
        self.__nRepsStarted = 0
        self.__nRepsFailed = 0
        self.__nRepsFinished = 0
        self.__msgQueue.start_listening()

        for runNumber in range(firstRun, lastRun+1):
            dbpath = self._clone_initialized_database()
            ar = pool.apply_async(execute_replication,
                                  self._execute_args(runNumber, dbpath),
                                  callback=self._callback)

        pool.close()
        logger.info("Running replications on thread %d", threading.get_ident())
        if asynch:
            self._async_join(pool)
        else:
            pool.join()
            self.__status = _STATUS_COMPLETE
            self.__msgQueue.stop_listening()
            self.ReplicationsComplete.emit()
            logger.info("(synchronous) replications complete")

    def _async_join(self, pool):
        """
        An asynchronous join the to the passed multiprocessing pool, allowing
        a UI to be responsive during replication execution.  Emits a
        ReplicationsComplete after the join - unless the replication tasks were
        cancelled by the client (via a cancel() call)

        The pool.join() is executed on a separate thread, emitting a
        ReplicationsComplete signal once that completes.  Connecting that
        signal to a an object running on the main thread should work (i.e.
        execute the slot call) as long as the main thread is running a Qt event
        loop.  (If no event loop is running, the signal seems to disappear
        into the ether.)
        """
        def joinAndSignal(pool):
            startTime = time.time()
            pool.join()
            self.__msgQueue.stop_listening()
            if self.cancelled:
                logger.info("Cancel requested.  Exiting execute")
            else:
                self.__status = _STATUS_COMPLETE
                logger.info("(asynchronous) replications complete. Total execution time = %f",
                            time.time() - startTime)
                self.ReplicationsComplete.emit()

        t = threading.Thread(target=joinAndSignal, args=(pool,))
        t.daemon = True
        t.start()

    def _create_initialized_database(self):
        """
        Create an output database for this model and initialize it to include
        a populated dataset table - but no datasetvalue rows.  We'll make a
        copy of this database for each replication, ensuring that each
        replication defines datasets (including dataset integer IDs) the same
        way.
        """
        self.cleanup()
        #simrandom.initialize(1)
        #SimClock.initialize()
        
        # Invoke staticInitialize on all static objects in the model
        #for staticobj in self.__model.static_objects:
        #    staticobj.staticInitialize()
        
        databaseManager = SimDatabaseManager()
        databaseManager.create_output_database(self.__model)
        self.__initializedDbPath = databaseManager.database.db_path
        databaseManager.close_output_database(delete=False)

    def _clone_initialized_database(self):
        """
        Make a copy of the initialized database created by
        _createInitializedDatabase() in a temporary file and
        return that file's path.
        """
        f, clonepath = tempfile.mkstemp(suffix='.simoutput')
        os.close(f)
        shutil.copyfile(self.__initializedDbPath, clonepath)
        return clonepath

    def _execute_args(self, runNumber, dbpath):
        """
        Returns the arguments to an executeReplication() call for the
        specified run number as a sequence, so that they may be passed
        in as part of a pool.apply_async() call.
        """
        args = (self.__modelPath, dbpath, runNumber,
                self.__warmupLength, self.__batchLength, self.__nBatches,
                self.__msgQueue.queue)
        return args

    def _callback(self, result):
        """
        Callback invoked after a replication finishes. Result is a tuple
        containing:
        - The run number of that replication
        - The path of the temporary database file created by the replication
        - An exception if the run failed, or None if it completed successfully
        - A string containing the traceback if the run failed, or None if it
          completed successfully

        By making all runs "succeed" (by not letting exceptions leak out of
        the task function executeReplication()), we can more easily get the
        run number that failed.  (An error callback would just get the exception,
        requiring either the run number to be embedded in the exception or other
        addiional code to find the corresponding run number.)

        Note that this callback occurs on the main (parent) process, though in
        a different thread.  It is possible for multiple runs complete and
        invoke this method nearly simultaneously; it is there at least
        theoretically possible for access to the master database (for the
        purpose of copying data) to become a bottleneck, and even timeout. If
        necessary, the handling of this callback could be delegated to a thread
        or process pool (with a single thread/process), thereby ensuring that
        only one callback is attempting to access the master database at a time.

        For successful runs, merge the temporary database into the master (also
        temporary) database that contains the datasetvalue data for all runs.

        The callback also creates or updates the __results dictionary value
        for the run.  (each __results value is an exception or None if the
        run completed successfully)
        """
        runNumber, dbpath, exception, tbstring = result
        self.__nRepsFinished += 1
        if exception:
            logger.error("Run %d failed: %s", runNumber, exception)
            print("Traceback:")
            print(tbstring)
        else:
            print("Replication Run", runNumber, "complete")
            try:
                self._merge_run(dbpath, runNumber)
            except Exception as e:
                print("Run", runNumber, "Data merge from ", dbpath,
                      "to", self.__masterDbPath, "failed:", e)
                result = runNumber, dbpath, e
                exception = e

        success = exception is None
        if not success:
            self.__nRepsFailed += 1
        errMsg = "" if success else str(exception)
        self.ReplicationFinished.emit(runNumber, success, errMsg)

        # The UI may access the results while the replicator is working, so
        # protect them with a lock.
        lock = threading.Lock()
        with lock:
            self.__results[runNumber] = exception

        if self.__nRepsFinished == self.__nRuns:
            if self.__masterDbConnection:
                self.__masterDbConnection.close()
                self.__masterDbConnection = None
            self.cleanup()

    def _merge_run(self, dbpath, runNumber):
        """
        Merge a passed database (created by a single replication) with a master
        database for all replications.  There are three possible scenarios here:

        1.  This is the the very first call to mergeRun() for this SimReplicator
            instance i.e., this is also the first call to executeReplications()
            for this instance.  In this case, there is not yet a master database
            file, so the passed dbpath becomes that file (and masterDbPath is
            set to it).

        2.  This is the first call to mergeRun() from a second or subsequent
            call to executeReplications() for this SimReplicator instance.
            (e.g., the user has run eight replications, and then decides to run
            eight more.)  In this case, the masterDbPath is set, but the
            connection to it needs to be re-opened.  After the re-connect, the
            data from the passed dbpath can be merged into the master database.

        3.  This is a second or subsequent call to mergeRun() for a given call
            to executeReplications().  The master database connection is
            already set, so we just merge data from the passed dbpath into the
            master database (via _copydata()).
        """
        if not self.__masterDbPath:
            self.__masterDbPath = dbpath
        else:
            if not self.__masterDbConnection:
                # It's possible for the outside world to mess with this file.
                #  We'll at least make sure it hasn't been deleted.
                if not os.path.isfile(self.__masterDbPath):
                    raise SimError(_ERROR_NAME,
                                   "Replicator Output Database has been removed")
                self.__masterDbConnection = sqlite3.connect(self.__masterDbPath)
            self._copydata(dbpath, self.__masterDbConnection, runNumber)
            os.remove(dbpath)

    def _copydata(self, srcpath, conn, runNumber):
        """
        Delete any dataset values for the passed run number from the master
        database.  (This handles the situation where the caller repeats a run
        in successive calls to executeReplications().) Then copy all rows
        from the passed srcpath database's datasetvalue table to the
        datasetvalue table in the passed master database connection (conn)
        It is assumed that the source database has datasetvalue data only for
        the passed runNumber.
        """
        startTime = time.time()
        cursor = conn.cursor()
        cursor.execute("delete from datasetvalue where run = ?", (runNumber,))
        attachsql = "attach '{0}' as srcdb".format(srcpath)
        cursor.execute(attachsql)
        sqlstr = """
                 insert into datasetvalue
                 select * from srcdb.datasetvalue
                 """
        cursor.execute(sqlstr)
        conn.commit()
        cursor.execute("detach srcdb")
        #print("copydatavalues for run", runNumber, srcpath, "time", time.time()-startTime)

    def _replication_started(self, runNumber):
        """
        Invoked when an asynchronous replication starts.
        """
        logger.info("Replication %d starting...", runNumber)
        self.__nRepsStarted += 1
        self.ReplicationStarted.emit(runNumber)


if __name__ == '__main__':
    import os, Simalytix
    import shutil
    from PySide.QtGui import *
    from simprovise.database import SimArchivedOutputDatabase, SimSummaryData

    modelPath = os.path.join(os.path.dirname(os.path.abspath(Simalytix.__file__)),
                             'Models', 'mm1_1.txt')
    outputDbPath = os.path.join(os.path.dirname(os.path.abspath(Simalytix.__file__)),
                             'Models', 'testR1.simoutput')
    warmupLength = SimTime(200)
    batchLength = SimTime(5000)
    nBatches = 2
    runNumber = 3

    def testpool():
        tp = TestPool()
        tp.run()


    class ReplicatorTester(QObject):
        Done = Signal()
        def __init__(self, fromRun, toRun):
            super().__init__(None)
            self.fromRun = fromRun
            self.toRun = toRun
            self.dbMgr = SimDatabaseManager()
            #SimAnimatableObject.setAnimating(False)
            simrandom.initialize(1)
            model = SimModel(MODEL_DEFAULTS_PATH)
            model.load(modelPath)
            self.model = model
            self.replicator = SimReplicator(model, warmupLength,
                                            batchLength, nBatches)
            self.replicator.ReplicationsComplete.connect(self.done)
            self.replicator.ReplicationsComplete.connect(self.Done)

        def run(self):
            if self.replicator.in_progress:
                self.replicator.cancel()
                return
            elif self.replicator.complete:
                self.fromRun += 3
                self.toRun += 3

            print("running tester", threading.get_ident())

            replicationParameters = SimReplicationParameters()
            replicationParameters.set_replication_range(self.fromRun, self.toRun)
            self.replicator.execute_replications(replicationParameters,
                                                asynch=True)

        def testSlot(self, s):
            print("test slot", s, threading.get_ident())

        def done(self):
            if not self.dbMgr.has_open_database():
                self.dbMgr.open_existing_database(self.model, self.replicator.output_dbpath)
            self.printOutput()


        def printOutput(self):
            print("printOutput")
            db = self.dbMgr.database
            for i in range(self.fromRun, self.toRun+1):
                summaryData = SimSummaryData(db, i, "Queue1")
                dset = db.get_dataset('Queue1', 'Time')
                sumdata = summaryData.get_data(dset)
                print(i, dset.element_id, dset.name, sumdata.mean, sumdata.count)
            #db.closeDatabase()
            #os.remove(dbPath)


    def testReplicator():
        fromRun = 9
        toRun = 12

        #SimAnimatableObject.setAnimating(False)
        simrandom.initialize(1)
        #databaseManager = SimDatabaseManager()
        model = SimModel(MODEL_DEFAULTS_PATH)
        model.load(modelPath)

        replicationParameters = SimReplicationParameters()
        replicationParameters.set_replication_range(fromRun, toRun)

        outputHandler = ReplicatorOutputHandler(fromRun, toRun)

        replicator = SimReplicator(model, warmupLength, batchLength, nBatches)
        replicator.ReplicationsComplete.connect(outputHandler.printOutput)
        replicator.execute_replications(replicationParameters)
        #outputHandler.printOutput(dbpath)

        #os.replace(dbpath, outputDbPath)

    def testReplicatorForm():
        from functools import partial
        app = QApplication(sys.argv)
        button = QPushButton("Test")
        reptester = ReplicatorTester(9,12)
        button.clicked.connect(partial(button.setText, "Cancel"))
        button.clicked.connect(reptester.run)
        reptester.Done.connect(partial(button.setText, "Execute"))
        button.show()
        app.exec_()

    testReplicatorForm()
    #testReplication()
